# 0_任务看板.py
import streamlit as st
import json
import os
from itertools import groupby
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from shared.sidebar import create_common_sidebar
from shared.config import AppConfig  # <<< 导入全局配置实例
from github import Github, UnknownObjectException

config = AppConfig()

# --- 初始化和页面设置 ---
st_autorefresh(interval=config.kanban.AUTO_REFRESH_INTERVAL_MS, key="clock_refresher")
create_common_sidebar()
beijing_tz = config.globals.APP_TIMEZONE


# 1. 任务类定义 (Task Class Definition)
class Task:
    def __init__(self, task_name, task_type):
        self.task_name = task_name
        self.task_type = task_type
        self.creation_time = datetime.now(beijing_tz)
        self.task_id = f"task_{self.creation_time.timestamp()}"
        self.task_progress = 0
        self.status = config.kanban.STATUS_TODO  # 使用配置
        self.completion_time = None
        self.task_duration = None
        self.task_comments = []
        self.total_active_time = timedelta(0)
        self.last_start_active_time = None
        self.active_time_segments = []

    def to_dict(self):
        return {
            "task_name": self.task_name,
            "task_type": self.task_type,
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "task_id": self.task_id,
            "task_progress": self.task_progress,
            "status": self.status,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "task_duration_seconds": self.task_duration.total_seconds() if self.task_duration else None,
            "task_comments": [{"content": c["content"], "type": c["type"], "time": c["time"].isoformat()} for c in
                              self.task_comments],
            "total_active_time_seconds": self.total_active_time.total_seconds(),
            "last_start_active_time": self.last_start_active_time.isoformat() if self.last_start_active_time else None,
            "active_time_segments": [{"start_time": s["start_time"].isoformat(), "end_time": s["end_time"].isoformat(),
                                      "duration_seconds": s["duration"].total_seconds(), "stopped_as": s["stopped_as"]}
                                     for s in self.active_time_segments]
        }

    @classmethod
    def from_dict(cls, data):
        task = cls(data["task_name"], data["task_type"])
        task.creation_time = datetime.fromisoformat(data["creation_time"]) if data.get("creation_time") else None
        task.task_id = data.get("task_id", f"task_{task.creation_time.timestamp()}")
        task.task_progress = data["task_progress"]
        task.status = data["status"]
        task.completion_time = datetime.fromisoformat(data["completion_time"]) if data.get("completion_time") else None
        if data.get("task_duration_seconds") is not None:
            task.task_duration = timedelta(seconds=data["task_duration_seconds"])
        task.task_comments = [{"content": c["content"], "type": c["type"], "time": datetime.fromisoformat(c["time"])}
                              for c in data.get("task_comments", [])]
        task.total_active_time = timedelta(seconds=data.get("total_active_time_seconds", 0))
        if data.get("last_start_active_time"):
            task.last_start_active_time = datetime.fromisoformat(data["last_start_active_time"])
        task.active_time_segments = [
            {"start_time": datetime.fromisoformat(s["start_time"]), "end_time": datetime.fromisoformat(s["end_time"]),
             "duration": timedelta(seconds=s["duration_seconds"]), "stopped_as": s["stopped_as"]} for s in
            data.get("active_time_segments", [])]
        return task

    def add_comment(self, content, comment_type):
        comment = {"content": content, "type": comment_type, "time": datetime.now(beijing_tz)}
        self.task_comments.append(comment)
        st.toast(config.kanban.T_TOAST_COMMENT_ADDED.format(task_name=self.task_name), icon="💬")

    def set_status(self, new_status):
        if self.status == new_status: return
        old_status, self.status, now = self.status, new_status, datetime.now(beijing_tz)

        if new_status == config.kanban.STATUS_DOING and old_status != config.kanban.STATUS_DOING:
            self.last_start_active_time = now
            st.toast(config.kanban.T_TOAST_TIMER_STARTED)
        elif new_status != config.kanban.STATUS_DOING and old_status == config.kanban.STATUS_DOING:
            if self.last_start_active_time:
                duration = now - self.last_start_active_time
                self.total_active_time += duration
                self.active_time_segments.append(
                    {"start_time": self.last_start_active_time, "end_time": now, "duration": duration,
                     "stopped_as": new_status})
                self.last_start_active_time = None
                st.toast(config.kanban.T_TOAST_TIMER_STOPPED)

        if new_status == config.kanban.STATUS_DONE:
            if old_status != config.kanban.STATUS_DONE:
                self.completion_time = now
                self.task_duration = self.completion_time - self.creation_time
                if self.task_progress != 100: self.task_progress = 100
                st.balloons()
        elif old_status == config.kanban.STATUS_DONE and new_status != config.kanban.STATUS_DONE:
            self.completion_time, self.task_duration = None, None
            if self.task_progress == 100: self.task_progress = 90
        elif new_status == config.kanban.STATUS_TODO:
            self.completion_time, self.task_duration = None, None

    def update_progress(self, new_progress):
        if self.task_progress == new_progress: return
        self.task_progress = new_progress
        if new_progress == 100 and self.status != config.kanban.STATUS_DONE:
            self.set_status(config.kanban.STATUS_DONE)
        elif new_progress < 100 and self.status == config.kanban.STATUS_DONE:
            self.set_status(config.kanban.STATUS_DOING)
        elif new_progress > 0 and self.status == config.kanban.STATUS_TODO:
            self.set_status(config.kanban.STATUS_DOING)
        elif new_progress == 0 and self.status != config.kanban.STATUS_TODO:
            self.set_status(config.kanban.STATUS_TODO)

    def get_total_lifespan_duration(self):
        return self.task_duration if self.completion_time else datetime.now(beijing_tz) - self.creation_time

    def get_total_active_duration(self):
        current_active = datetime.now(
            beijing_tz) - self.last_start_active_time if self.status == config.kanban.STATUS_DOING and self.last_start_active_time else timedelta(
            0)
        return self.total_active_time + current_active


def format_timedelta_to_str(duration):
    if not isinstance(duration, timedelta) or duration.total_seconds() <= 0: return "0秒"
    total_seconds = int(duration.total_seconds())
    days, rem = divmod(total_seconds, 86400);
    hours, rem = divmod(rem, 3600);
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days > 0: parts.append(f"{days}天")
    if hours > 0: parts.append(f"{hours}小时")
    if minutes > 0: parts.append(f"{minutes}分钟")
    if seconds > 0 and total_seconds < 60: parts.append(f"{seconds}秒")
    return "".join(parts) if parts else "0秒"


@st.cache_resource
def get_github_repo(token=None, repo_name=None):
    # 优先使用传入的凭证，其次是全局配置
    g_token = token or config.globals.GITHUB_TOKEN
    g_repo = repo_name or config.globals.GITHUB_REPO
    if not g_token or not g_repo: return None
    try:
        return Github(g_token).get_repo(g_repo)
    except Exception as e:
        st.error(config.kanban.T_ERROR_GITHUB_CONNECTION.format(e=e)); return None


def load_tasks_from_github(token=None, repo_name=None):
    repo = get_github_repo(token, repo_name)
    if repo is None: return None
    try:
        content = repo.get_contents(config.kanban.DATA_FILE_NAME).decoded_content.decode("utf-8")
        st.toast(config.kanban.T_SUCCESS_GITHUB_LOAD, icon="🎉")
        return [Task.from_dict(task_data) for task_data in json.loads(content)]
    except UnknownObjectException:
        st.info(config.kanban.T_INFO_GITHUB_FILE_NOT_FOUND); return []
    except Exception as e:
        st.error(config.kanban.T_ERROR_GITHUB_LOAD_UNKNOWN.format(e=e)); return []


def save_tasks_to_github(token=None, repo_name=None):
    repo = get_github_repo(token, repo_name)
    if repo is None: st.error(config.kanban.T_ERROR_GITHUB_SAVE_FAILED); return
    content = json.dumps([task.to_dict() for task in st.session_state.tasks], indent=2)
    commit_message = f"Tasks updated at {datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        try:
            file = repo.get_contents(config.kanban.DATA_FILE_NAME)
            repo.update_file(file.path, commit_message, content, file.sha)
            st.toast(config.kanban.T_SUCCESS_GITHUB_UPDATED, icon="⬆️")
        except UnknownObjectException:
            repo.create_file(config.kanban.DATA_FILE_NAME, commit_message, content)
            st.toast(config.kanban.T_SUCCESS_GITHUB_CREATED, icon="☁️")
    except Exception as e:
        st.error(config.kanban.T_ERROR_GITHUB_SYNC_FAILED.format(e=e))


def load_tasks_from_local():
    path = config.globals.LOCAL_DATA_FILE_PATH
    if not os.path.exists(path): return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content: return []
            st.toast(config.kanban.T_SUCCESS_LOCAL_LOAD, icon="🏠")
            return [Task.from_dict(td) for td in json.loads(content)]
    except Exception as e:
        st.error(config.kanban.T_ERROR_LOCAL_LOAD.format(e=e)); return []


def save_tasks_to_local():
    path = config.globals.LOCAL_DATA_FILE_PATH
    try:
        content = json.dumps([task.to_dict() for task in st.session_state.tasks], indent=2)
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
        st.toast(config.kanban.T_SUCCESS_LOCAL_SAVE, icon="💾")
    except Exception as e:
        st.error(config.kanban.T_ERROR_LOCAL_SAVE.format(e=e))


# <<< 统一的、基于模式的同步函数 >>>
def sync_state():
    """根据运行模式自动处理数据保存"""
    # 在本地模式下，双重保存
    if config.globals.RUN_MODE == "local":
        save_tasks_to_local()
        if config.globals.GITHUB_TOKEN: # 如果配置了GitHub，就同步
            save_tasks_to_github()
    # 在云端模式下，只同步到用户连接的GitHub
    else:
        g_token = st.session_state.get("github_token") or config.globals.GITHUB_TOKEN
        g_repo = st.session_state.get("github_repo") or config.globals.GITHUB_REPO
        if g_token and g_repo:
            save_tasks_to_github(g_token, g_repo)


# <<< 修改：更清晰的初始化逻辑 >>>
def initialize_app():
    st.set_page_config(page_title=config.kanban.PAGE_TITLE, page_icon=config.kanban.PAGE_ICON, layout="wide")
    st.title(config.kanban.T_MAIN_TITLE); st.markdown("---")
    if 'tasks' not in st.session_state:
        if config.globals.RUN_MODE == "local":
            # 本地模式：先从本地加载，如果本地没有，再尝试从GitHub加载
            tasks = load_tasks_from_local()
            if not tasks and config.globals.GITHUB_TOKEN:
                tasks = load_tasks_from_github()
            st.session_state.tasks = tasks
        else:
            # 云端模式：默认是空的，等待用户连接GitHub
            st.session_state.tasks = []


def handle_tasks_import(uploaded_file):
    if uploaded_file is None: return
    try:
        tasks_data = json.load(uploaded_file)
        existing_ids = {task.task_id for task in st.session_state.tasks}
        new_tasks = [Task.from_dict(td) for td in tasks_data if td.get("task_id") not in existing_ids]
        if new_tasks:
            st.session_state.tasks.extend(new_tasks)
            st.success(config.kanban.T_SUCCESS_IMPORT.format(count=len(new_tasks)));
            st.rerun()
        else:
            st.info(config.kanban.T_INFO_NO_NEW_TASKS_IMPORTED)
    except json.JSONDecodeError:
        st.error(config.kanban.T_ERROR_JSON_DECODE)
    except Exception as e:
        st.error(config.kanban.T_ERROR_IMPORT_UNKNOWN.format(e=e))


def get_export_data():
    return json.dumps([task.to_dict() for task in st.session_state.tasks], indent=2) if st.session_state.tasks else "{}"


def display_main_controls():
    st.header(config.kanban.T_CONTROL_PANEL_HEADER, divider="rainbow")

    # <<< 根据运行模式显示不同的UI >>>
    if config.globals.RUN_MODE == "local":
        st.info(config.kanban.T_LOCAL_MODE_INFO)
    else:  # 云端模式
        # --- 修改开始 ---
        # 为所有云端用户提供统一、安全的 GitHub 连接界面
        with st.container(border=True):
            st.subheader(config.kanban.T_GITHUB_CONNECT_HEADER, anchor=False)
            st.info(config.kanban.T_CLOUD_MODE_INFO)  # 提示用户需要连接GitHub

            # 为所有公共用户提供输入框
            col_token, col_repo = st.columns(2)
            g_token = col_token.text_input(
                config.kanban.T_GITHUB_TOKEN_INPUT,
                type="password",
                key="github_token_input"  # 使用固定的key
            )
            g_repo = col_repo.text_input(
                config.kanban.T_GITHUB_REPO_INPUT,
                placeholder="your-username/your-repo",
                key="github_repo_input"  # 使用固定的key
            )

            if st.button(config.kanban.T_GITHUB_CONNECT_BUTTON, use_container_width=True):
                if g_token and g_repo:
                    # 将用户输入的值存入 session_state
                    st.session_state.github_token = g_token
                    st.session_state.github_repo = g_repo
                    # 使用用户输入的值加载任务
                    tasks = load_tasks_from_github(g_token, g_repo)
                    if tasks is not None:
                        st.session_state.tasks = tasks
                        st.rerun()
                else:
                    st.warning(config.kanban.T_ERROR_GITHUB_CREDS_MISSING)

    # 创建任务 和 本地导入/导出 功能区
    col1, col2 = st.columns(2)
    with col1, st.container(border=True, height=config.kanban.UI_CONTROL_PANEL_HEIGHT):
        st.subheader(config.kanban.T_CREATE_TASK_HEADER, anchor=False)
        with st.form(key="new_task_form", clear_on_submit=True):
            name = st.text_input(config.kanban.T_TASK_NAME_LABEL, placeholder=config.kanban.T_TASK_NAME_PLACEHOLDER)
            type = st.selectbox(config.kanban.T_TASK_TYPE_LABEL, config.kanban.TASK_TYPES)
            if st.form_submit_button(config.kanban.T_ADD_TASK_BUTTON, use_container_width=True):
                if name:
                    st.session_state.tasks.append(Task(task_name=name, task_type=type))
                    st.success(config.kanban.T_SUCCESS_TASK_ADDED.format(task_name=name))
                    sync_state()  # <<< 统一调用
                    st.rerun()
                else:
                    st.warning(config.kanban.T_WARN_EMPTY_TASK_NAME)

    with col2, st.container(border=True, height=config.kanban.UI_CONTROL_PANEL_HEIGHT):
        st.subheader(config.kanban.T_LOCAL_IO_HEADER, anchor=False)
        uploaded = st.file_uploader(config.kanban.T_UPLOAD_LABEL, type=["json"], help=config.kanban.T_UPLOAD_HELP)
        if uploaded: handle_tasks_import(uploaded)
        fname = f"{config.kanban.T_EXPORT_FILE_PREFIX}{datetime.now(beijing_tz).strftime('%Y%m%d_%H%M%S')}.json"
        st.download_button(config.kanban.T_DOWNLOAD_BUTTON, get_export_data(), fname, "application/json",
                           help=config.kanban.T_DOWNLOAD_HELP, use_container_width=True,
                           disabled=not st.session_state.tasks)
        # 手动同步按钮（主要用于云端模式）
        if config.globals.RUN_MODE == "cloud":
            st.button("⬆️ 手动同步到 GitHub", on_click=sync_state, use_container_width=True)


def get_task_by_id(task_id):
    return next((task for task in st.session_state.tasks if task.task_id == task_id), None)


def handle_progress_change(task_id):
    task = get_task_by_id(task_id)
    if task: task.update_progress(st.session_state[f"progress_{task_id}"]); sync_state()


def handle_status_change(task, new_status):
    task.set_status(new_status);
    sync_state()


def display_task_controls(task):
    cols = st.columns(4)
    if task.status == config.kanban.STATUS_TODO:
        cols[0].button(config.kanban.T_BUTTON_START, key=f"start_{task.task_id}", on_click=handle_status_change,
                       args=(task, config.kanban.STATUS_DOING), use_container_width=True)
    if task.status == config.kanban.STATUS_DOING:
        cols[1].button(config.kanban.T_BUTTON_PAUSE, key=f"pause_{task.task_id}", on_click=handle_status_change,
                       args=(task, config.kanban.STATUS_TODO), help=config.kanban.T_BUTTON_PAUSE_HELP,
                       use_container_width=True)
        cols[2].button(config.kanban.T_BUTTON_DONE, key=f"done_{task.task_id}", on_click=handle_status_change,
                       args=(task, config.kanban.STATUS_DONE), use_container_width=True)
    if task.status == config.kanban.STATUS_DONE:
        cols[3].button(config.kanban.T_BUTTON_REOPEN, key=f"reopen_{task.task_id}", on_click=handle_status_change,
                       args=(task, config.kanban.STATUS_DOING), use_container_width=True)
    st.write("")


def display_task_comments(task):
    st.subheader(config.kanban.T_CARD_COMMENTS_HEADER, divider='rainbow')
    with st.popover(config.kanban.T_POPOVER_CREATE_COMMENT):
        with st.form(key=f"comment_form_{task.task_id}", clear_on_submit=True):
            ctype = st.selectbox(config.kanban.T_COMMENT_TYPE_LABEL, config.kanban.COMMENT_TYPES,
                                 key=f"ctype_{task.task_id}")
            content = st.text_area(config.kanban.T_COMMENT_CONTENT_LABEL, key=f"ctext_{task.task_id}", height=100)
            if st.form_submit_button(config.kanban.T_COMMENT_SUBMIT_BUTTON):
                if content:
                    task.add_comment(content, ctype); sync_state(); st.rerun()
                else:
                    st.warning(config.kanban.T_WARN_EMPTY_COMMENT)
    if task.task_comments:
        with st.container(height=250):
            for c in reversed(task.task_comments):
                icon = config.kanban.COMMENT_ICON_MAP.get(c['type'], "💬")
                color = config.kanban.COMMENT_COLOR_MAP.get(c['type'], "gray")
                with st.chat_message(name=c['type'], avatar=icon):
                    st.markdown(f":{color}[{c['content']}]");
                    st.caption(f"_{c['time'].strftime('%Y-%m-%d %H:%M')}_")


def display_task_time_logs(task):
    st.subheader(config.kanban.T_CARD_TIME_LOGS_HEADER, divider='rainbow')
    if task.status == config.kanban.STATUS_DOING and task.last_start_active_time:
        start_str = task.last_start_active_time.strftime('%Y-%m-%d %H:%M:%S')
        duration_str = format_timedelta_to_str(datetime.now(beijing_tz) - task.last_start_active_time)
        st.success(f"**当前:** 正在计时... ({duration_str})\n开始于: {start_str}")
    if not task.active_time_segments and task.status != config.kanban.STATUS_DOING:
        st.caption(config.kanban.T_INFO_NO_TIME_LOGS)
    else:
        sorted_segments = sorted(task.active_time_segments, key=lambda s: s['start_time'], reverse=True)
        for date, group in groupby(sorted_segments, key=lambda s: s['start_time'].date()):
            group_list = list(group)
            total_duration_str = format_timedelta_to_str(sum((s['duration'] for s in group_list), timedelta()))
            date_str = date.strftime('%Y-%m-%d')
            with st.expander(f"**{date_str}** - 总计: **{total_duration_str}** ({len(group_list)} 条记录)"):
                for s in group_list:
                    duration, start, end = format_timedelta_to_str(s['duration']), s['start_time'].strftime('%H:%M:%S'), \
                                           s['end_time'].strftime('%H:%M:%S')
                    icon = "⏸️" if s['stopped_as'] == config.kanban.STATUS_TODO else "✅"
                    st.info(f"**{duration}** (从 {start} 到 {end}) {icon}")


def display_task_management(task):
    st.divider()
    col_info, col_manage = st.columns([3, 1])
    with col_info:
        st.caption(f"ID: {task.task_id}");
        st.caption(f"创建于: {task.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")
    with col_manage, st.popover(config.kanban.T_CARD_MANAGE_POPOVER):
        with st.form(key=f"edit_form_{task.task_id}"):
            st.subheader(config.kanban.T_CARD_EDIT_HEADER, anchor=False)
            edited_name = st.text_input(config.kanban.T_TASK_NAME_LABEL, value=task.task_name)
            type_options = config.kanban.TASK_TYPES
            index = type_options.index(task.task_type) if task.task_type in type_options else 0
            edited_type = st.selectbox(config.kanban.T_TASK_TYPE_LABEL, options=type_options, index=index,
                                       key=f"task_type_{task.task_id}")
            if st.form_submit_button(config.kanban.T_CARD_SAVE_BUTTON, use_container_width=True):
                task.task_name, task.task_type = edited_name, edited_type
                st.toast(config.kanban.T_SUCCESS_TASK_UPDATED.format(task_name=task.task_name), icon="✅");
                sync_state();
                st.rerun()
        st.divider()
        if st.button(config.kanban.T_CARD_DELETE_BUTTON, type="primary", use_container_width=True,
                     help=config.kanban.T_CARD_DELETE_HELP, key=f"delete_btn_{task.task_id}"):
            st.session_state.tasks = [t for t in st.session_state.tasks if t.task_id != task.task_id]
            st.toast(config.kanban.T_SUCCESS_TASK_DELETED.format(task_name=task.task_name), icon="🗑️");
            sync_state();
            st.rerun()


def display_task_card(task):
    with st.expander(f"{task.task_name}", expanded=True):
        st.subheader(task.task_name, divider="rainbow")
        col_time1, col_time2 = st.columns(2)
        col_time1.metric(config.kanban.T_CARD_METRIC_ACTIVE_TIME,
                         format_timedelta_to_str(task.get_total_active_duration()),
                         help=config.kanban.T_CARD_METRIC_ACTIVE_TIME_HELP)
        col_time2.metric(config.kanban.T_CARD_METRIC_LIFESPAN,
                         format_timedelta_to_str(task.get_total_lifespan_duration()),
                         help=config.kanban.T_CARD_METRIC_LIFESPAN_HELP)
        display_task_controls(task)
        st.slider(config.kanban.T_CARD_PROGRESS_SLIDER_LABEL, 0, 100, task.task_progress, 10, "%d%%",
                  key=f"progress_{task.task_id}", help=config.kanban.T_CARD_PROGRESS_SLIDER_HELP,
                  on_change=handle_progress_change, args=(task.task_id,))
        display_task_time_logs(task)
        display_task_comments(task)
        display_task_management(task)


def display_kanban_layout():
    sorted_tasks = sorted(st.session_state.tasks, key=lambda x: x.creation_time, reverse=True)
    tasks_todo = [t for t in sorted_tasks if t.status == config.kanban.STATUS_TODO]
    tasks_doing = [t for t in sorted_tasks if t.status == config.kanban.STATUS_DOING]
    tasks_done = [t for t in sorted_tasks if t.status == config.kanban.STATUS_DONE]

    # 将页面分为三列
    col1, col2, col3 = st.columns(3, gap="large")

    with col1:  # 使用存储的第一个列对象
        st.header(f"{config.kanban.T_COLUMN_TODO_HEADER} ({len(tasks_todo)})", divider="rainbow")
        for task in tasks_todo: display_task_card(task)

    with col2:  # 使用存储的第二个列对象
        st.header(f"{config.kanban.T_COLUMN_DOING_HEADER} ({len(tasks_doing)})", divider="rainbow")
        for task in tasks_doing: display_task_card(task)

    with col3:  # 使用存储的第三个列对象
        st.header(f"{config.kanban.T_COLUMN_DONE_HEADER} ({len(tasks_done)})", divider="rainbow")
        for task in tasks_done: display_task_card(task)


def main():
    initialize_app()
    display_main_controls()
    display_kanban_layout()


if __name__ == "__main__":
    main()