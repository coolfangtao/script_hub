# 0_任务看板.py
import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from itertools import groupby
from datetime import datetime, timedelta, date, time
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
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
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
    content = json.dumps([task.to_dict() for task in st.session_state.tasks], indent=2, ensure_ascii=False)
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
        content = json.dumps([task.to_dict() for task in st.session_state.tasks], indent=2, ensure_ascii=False)
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
        st.toast(config.kanban.T_SUCCESS_LOCAL_SAVE, icon="💾")
    except Exception as e:
        st.error(config.kanban.T_ERROR_LOCAL_SAVE.format(e=e))


# <<< 统一的、基于模式的同步函数 >>>
def sync_state():
    """根据运行模式自动处理数据保存"""
    # 在本地模式下，进行双重保存
    if config.globals.RUN_MODE == "local":
        save_tasks_to_local()
        # 如果配置了GitHub，就同步
        if config.globals.GITHUB_TOKEN:
            save_tasks_to_github()

    # 在云端模式下，只且必须使用 session_state 中的凭证
    else:
        # 确保用户已经通过UI连接，并且凭证存在于当前会话中
        if 'github_token' in st.session_state and 'github_repo' in st.session_state:
            save_tasks_to_github(
                st.session_state.github_token,
                st.session_state.github_repo
            )
        # 如果 session_state 中没有凭证，则不执行任何操作。
        # 这可以防止未登录用户意外地同步到所有者的仓库。

def disconnect_github():
    """清空 session_state 中的 GitHub 凭证"""
    if 'github_token' in st.session_state:
        del st.session_state.github_token
    if 'github_repo' in st.session_state:
        del st.session_state.github_repo
    # 清空任务列表，因为它们属于上一个连接
    st.session_state.tasks = []
    st.toast("已断开连接", icon="🔗")

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
    return json.dumps([task.to_dict() for task in st.session_state.tasks], indent=2, ensure_ascii=False) if st.session_state.tasks else "{}"


# =========================================================================================
# <<< 升级后的“创建新任务”函数 >>>
# =========================================================================================
# =========================================================================================
# <<< 升级并修复交互逻辑后的“创建新任务”函数 >>>
# =========================================================================================
def display_main_controls():
    st.header(config.kanban.T_CONTROL_PANEL_HEADER, divider="rainbow")

    is_connected = False

    if config.globals.RUN_MODE == "local":
        st.info(config.kanban.T_LOCAL_MODE_INFO)
        is_connected = True
    else:
        is_connected = 'github_token' in st.session_state and 'github_repo' in st.session_state
        with st.container(border=True):
            st.subheader(config.kanban.T_GITHUB_CONNECT_HEADER, anchor=False)
            if not is_connected:
                st.info(config.kanban.T_CLOUD_MODE_INFO)
                if st.session_state.tasks:
                    st.warning("**注意：** 您当前页面上有未同步的任务。连接到 GitHub 将会丢弃这些任务，并从您的仓库加载数据。")
                col_token, col_repo = st.columns(2)
                g_token = col_token.text_input(config.kanban.T_GITHUB_TOKEN_INPUT, type="password")
                g_repo = col_repo.text_input(config.kanban.T_GITHUB_REPO_INPUT, placeholder="your-username/your-repo")
                if st.button(config.kanban.T_GITHUB_CONNECT_BUTTON, use_container_width=True):
                    if g_token and g_repo:
                        st.session_state.github_token, st.session_state.github_repo = g_token, g_repo
                        tasks = load_tasks_from_github(g_token, g_repo)
                        if tasks is not None:
                            st.session_state.tasks = tasks;
                            st.rerun()
                    else:
                        st.warning(config.kanban.T_ERROR_GITHUB_CREDS_MISSING)
            else:
                st.success(f"✅ 已连接到仓库: **{st.session_state.github_repo}**")
                st.button("🔌 断开连接", on_click=disconnect_github, use_container_width=True, type="secondary")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1, st.container(border=True, height=config.kanban.UI_CONTROL_PANEL_HEIGHT):
        st.subheader(config.kanban.T_CREATE_TASK_HEADER, anchor=False)

        # --- 核心修改：将交互式选择框移到 form 外部 ---

        # 1. 动态获取所有已存在的任务类型
        default_types = config.kanban.TASK_TYPES
        existing_types = sorted(list(set(t.task_type for t in st.session_state.get('tasks', []))))
        combined_types = sorted(list(set(default_types + existing_types)))

        # 2. 创建一个特殊的选项用于添加新类型
        ADD_NEW_OPTION = "➕ 添加新类型..."
        options = combined_types + [ADD_NEW_OPTION]

        selected_option = st.selectbox(
            label=config.kanban.T_TASK_TYPE_LABEL,
            options=options,
            key="task_type_selector"
        )

        new_type_name = ""
        # 3. 这个条件判断现在可以立即响应用户的选择
        if selected_option == ADD_NEW_OPTION:
            new_type_name = st.text_input(
                "请输入新的类型名称:",
                placeholder="例如：会议、调研、紧急修复"
            )

        # --- Form 现在只包含需要打包提交的部分 ---
        with st.form(key="new_task_form"):
            name = st.text_input(config.kanban.T_TASK_NAME_LABEL, placeholder=config.kanban.T_TASK_NAME_PLACEHOLDER)

            if st.form_submit_button(config.kanban.T_ADD_TASK_BUTTON, use_container_width=True):
                if name:
                    final_task_type = ""
                    # 4. 在提交时，从 form 外部的变量中获取任务类型
                    if selected_option == ADD_NEW_OPTION:
                        if new_type_name:
                            final_task_type = new_type_name
                        else:
                            st.warning("您选择了添加新类型，但未输入类型名称。")
                            st.stop()
                    else:
                        final_task_type = selected_option

                    st.session_state.tasks.append(Task(task_name=name, task_type=final_task_type))
                    st.success(config.kanban.T_SUCCESS_TASK_ADDED.format(task_name=name))
                    sync_state()
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
        if config.globals.RUN_MODE == "cloud":
            st.button("⬆️ 手动同步到 GitHub", on_click=sync_state, use_container_width=True, disabled=not is_connected)


def get_task_by_id(task_id):
    return next((task for task in st.session_state.tasks if task.task_id == task_id), None)


def handle_progress_change(task_id):
    task = get_task_by_id(task_id)
    if task: task.update_progress(st.session_state[f"progress_{task_id}"]); sync_state()


def handle_status_change(task, new_status):
    task.set_status(new_status)
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

        # 这里的 with st.form(...) 是关键
        with st.form(key=f"edit_form_{task.task_id}"):
            st.subheader(config.kanban.T_CARD_EDIT_HEADER, anchor=False)
            edited_name = st.text_input(config.kanban.T_TASK_NAME_LABEL, value=task.task_name)

            # --- 这是上一个bug的修复：动态生成类型列表 ---
            default_types = config.kanban.TASK_TYPES
            existing_types = sorted(list(set(t.task_type for t in st.session_state.get('tasks', []))))
            combined_types = sorted(list(set(default_types + existing_types)))
            if task.task_type not in combined_types:
                combined_types.append(task.task_type)
                combined_types.sort()
            index = combined_types.index(task.task_type) if task.task_type in combined_types else 0
            edited_type = st.selectbox(
                config.kanban.T_TASK_TYPE_LABEL,
                options=combined_types,
                index=index,
                key=f"task_type_{task.task_id}"
            )

            # --- 核心修复：确保 st.form_submit_button 在 form 的缩进内部 ---
            if st.form_submit_button(config.kanban.T_CARD_SAVE_BUTTON, use_container_width=True):
                task.task_name, task.task_type = edited_name, edited_type
                st.toast(config.kanban.T_SUCCESS_TASK_UPDATED.format(task_name=task.task_name), icon="✅")
                sync_state()
                st.rerun()  # 在这种交互后立即刷新是合理的

        # --- 分割线和删除按钮应该在 form 的外部 ---
        st.divider()
        if st.button(config.kanban.T_CARD_DELETE_BUTTON, type="primary", use_container_width=True,
                     help=config.kanban.T_CARD_DELETE_HELP, key=f"delete_btn_{task.task_id}"):
            st.session_state.tasks = [t for t in st.session_state.tasks if t.task_id != task.task_id]
            st.toast(config.kanban.T_SUCCESS_TASK_DELETED.format(task_name=task.task_name), icon="🗑️")
            sync_state()
            st.rerun()  # 删除后也需要刷新


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


# =========================================================================================
# <<< 统计分析标签页函数 >>>
# =========================================================================================
def display_statistics_tab():
    st.header("任务统计分析 📊", divider="rainbow")

    tasks = st.session_state.get('tasks', [])
    if not tasks:
        st.info("看板上还没有任务，快去创建一个吧！")
        return

    # 1. <<< 直接从Task对象构建DataFrame，避免不必要的类型转换 >>>
    df = pd.DataFrame(
        [
            {
                "creation_time": t.creation_time,  # 直接使用datetime对象
                "completion_time": t.completion_time,  # 直接使用datetime对象或None
                "status": t.status,
                "task_type": t.task_type,
                "total_active_time_seconds": t.total_active_time.total_seconds(),
                "task_duration_seconds": t.task_duration.total_seconds() if t.task_duration else None,
            }
            for t in tasks
        ]
    )

    # 转换数据类型以便分析
    df['total_active_time_hours'] = df['total_active_time_seconds'] / 3600
    df['task_duration_hours'] = df['task_duration_seconds'] / 3600

    # --- 后续的统计和绘图代码 ---

    # 2. 显示关键指标 (KPIs)
    st.subheader("核心指标", anchor=False)
    total_tasks = len(df)
    completed_tasks = df[df['status'] == config.kanban.STATUS_DONE].shape[0]
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    avg_active_time_sec = df[df['status'] == config.kanban.STATUS_DONE]['total_active_time_seconds'].mean()
    avg_lifespan_sec = df[df['status'] == config.kanban.STATUS_DONE]['task_duration_seconds'].mean()

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("总任务数", f"{total_tasks} 个")
    kpi_cols[1].metric("完成率", f"{completion_rate:.1f}%")
    kpi_cols[2].metric("平均活跃时长", format_timedelta_to_str(timedelta(seconds=avg_active_time_sec)) if pd.notna(
        avg_active_time_sec) else "N/A")
    kpi_cols[3].metric("平均生命周期", format_timedelta_to_str(timedelta(seconds=avg_lifespan_sec)) if pd.notna(
        avg_lifespan_sec) else "N/A")

    st.markdown("---")

    # 3. 任务分布图表
    st.subheader("任务分布", anchor=False)
    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['status'].value_counts()
        fig_status = px.pie(status_counts, values=status_counts.values, names=status_counts.index,
                            title="任务状态分布", hole=0.3)
        st.plotly_chart(fig_status, use_container_width=True)
    with col2:
        type_counts = df['task_type'].value_counts()
        fig_type = px.pie(type_counts, values=type_counts.values, names=type_counts.index,
                          title="任务类型分布", hole=0.3)
        st.plotly_chart(fig_type, use_container_width=True)

    st.markdown("---")

    # 4. 任务时间趋势
    st.subheader("任务时间趋势", anchor=False)
    # 确保creation_time有时区信息，以便正确处理
    if df['creation_time'].dt.tz is None:
        df['creation_time'] = df['creation_time'].dt.tz_localize('UTC').dt.tz_convert(beijing_tz)

    df['creation_date'] = df['creation_time'].dt.date
    tasks_per_day = df.groupby('creation_date').size().reset_index(name='count')
    fig_trend = px.bar(tasks_per_day, x='creation_date', y='count', title="每日创建任务数",
                       labels={'creation_date': '日期', 'count': '任务数量'})
    fig_trend.update_layout(xaxis_title="创建日期", yaxis_title="任务数")
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # 5. 任务耗时分析
    st.subheader("任务耗时分析 (仅限已完成任务)", anchor=False)
    completed_df = df[df['status'] == config.kanban.STATUS_DONE].copy()
    if not completed_df.empty:
        # 按类型分析平均耗时
        avg_time_by_type = completed_df.groupby('task_type')[
            ['total_active_time_hours', 'task_duration_hours']].mean().reset_index()
        avg_time_by_type = avg_time_by_type.rename(columns={
            'total_active_time_hours': '平均活跃时长 (小时)',
            'task_duration_hours': '平均生命周期 (小时)'
        })

        fig_avg_time = px.bar(avg_time_by_type, x='task_type', y=['平均活跃时长 (小时)', '平均生命周期 (小时)'],
                              barmode='group', title='各类型任务平均耗时对比')
        fig_avg_time.update_layout(xaxis_title="任务类型", yaxis_title="平均小时数")
        st.plotly_chart(fig_avg_time, use_container_width=True)
    else:
        st.info("暂无已完成的任务可供分析耗时。")


# =========================================================================================
# <<< 日历视图函数 >>>
# =========================================================================================
# =========================================================================================
# <<< 功能升级后的日历视图函数 >>>
# =========================================================================================
# =========================================================================================
# <<< 修复并升级后的日历视图函数 >>>
# =========================================================================================
# =========================================================================================
# <<< 修复并升级后的日历视图函数 >>>
# =========================================================================================
def display_timeline_tab():
    st.header("任务时间线视图 📅", divider="rainbow")

    tasks = st.session_state.get('tasks', [])

    timeline_data = []
    for task in tasks:
        base_task_name = task.task_name
        for segment in task.active_time_segments:
            timeline_data.append({
                "Task": base_task_name,
                "Start": segment['start_time'],
                "Finish": segment['end_time'],
                "Type": task.task_type
            })
        if task.status == config.kanban.STATUS_DOING and task.last_start_active_time:
            timeline_data.append({
                "Task": base_task_name,
                "Start": task.last_start_active_time,
                "Finish": datetime.now(beijing_tz),
                "Type": "进行中"
            })

    if not timeline_data:
        st.info("没有任务活动记录，请先开始并完成一些任务以生成时间线。")
        return

    df = pd.DataFrame(timeline_data)

    st.subheader("选择查看范围", anchor=False)
    min_date = df['Start'].min().date()
    max_date = df['Finish'].max().date()
    today = date.today()

    default_start = today if min_date <= today <= max_date else min_date

    date_selection = st.date_input(
        "选择日期或范围",
        value=(default_start, today),
        min_value=min_date,
        max_value=max_date,
        help="选择一个日期来查看当天，或选择一个范围来查看多天。"
    )

    if not (isinstance(date_selection, tuple) and len(date_selection) == 2):
        st.stop()

    start_date, end_date = date_selection

    start_date_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=beijing_tz)
    end_date_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=beijing_tz)

    filtered_df = df[
        (df['Start'] <= end_date_dt) & (df['Finish'] >= start_date_dt)
        ].copy()

    if filtered_df.empty:
        st.warning(f"在 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 期间没有找到任务活动记录。")
        return

    def get_display_name(row):
        if row['Type'] == '进行中':
            return f"{row['Task']} (⚡️进行中)"
        return row['Task']

    filtered_df['Display Name'] = filtered_df.apply(get_display_name, axis=1)
    filtered_df['Display Name'] = filtered_df['Display Name'].astype(str)
    filtered_df['Task'] = filtered_df['Task'].astype(str)

    filtered_df['Clipped_Start'] = filtered_df['Start'].clip(lower=start_date_dt)
    filtered_df['Clipped_Finish'] = filtered_df['Finish'].clip(upper=end_date_dt)

    def create_bar_label(row):
        duration = row['Clipped_Finish'] - row['Clipped_Start']
        duration_str = format_timedelta_to_str(duration)
        if duration.total_seconds() < 1800:
            return f"<b>{duration_str}</b>"
        start_str = row['Clipped_Start'].strftime('%H:%M')
        end_str = row['Clipped_Finish'].strftime('%H:%M')
        return f"<b>{start_str} → {end_str} ({duration_str})</b>"

    filtered_df['bar_text'] = filtered_df.apply(create_bar_label, axis=1)

    st.subheader("任务活动时间线", anchor=False)

    fig = px.timeline(
        filtered_df,
        x_start="Clipped_Start",
        x_end="Clipped_Finish",
        y="Display Name",
        color="Task",
        title=f"任务时间线 ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
        labels={"Task": "任务名称"},
        hover_name="Display Name",
        hover_data={"Start": "|%Y-%m-%d %H:%M:%S", "Finish": "|%Y-%m-%d %H:%M:%S", "Task": False},
        text="bar_text",
        height=600
    )
    fig.update_traces(
        width=0.7, textposition='inside', textfont_color='white', insidetextanchor='middle'
    )

    all_dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    for day in all_dates:
        midnight_ts = datetime.combine(day, datetime.min.time()).replace(tzinfo=beijing_tz)

        # <<< 核心修复：直接使用 time()，而不是 datetime.time() >>>
        noon_ts = datetime.combine(day, time(12, 0)).replace(tzinfo=beijing_tz)

        fig.add_vline(x=midnight_ts, line_dash="solid", line_color="grey")
        fig.add_vline(x=noon_ts, line_dash="dash", line_color="lightgrey")

        fig.add_annotation(
            x=midnight_ts,
            y=1.01,
            yref="paper",
            text=day.strftime("%b %d"),
            showarrow=False,
            xanchor="left",
            font=dict(color="grey", size=10)
        )

    fig.update_layout(
        xaxis_title="时间",
        yaxis_title="任务",
        showlegend=True,
        xaxis=dict(type="date", tickformat="%H:%M\n%m-%d")
    )
    fig.update_yaxes(categoryorder='total ascending')

    st.plotly_chart(fig, use_container_width=True)


# =========================================================================================
# <<< 新增：评论知识库标签页函数 >>>
# =========================================================================================
def display_comments_tab():
    st.header("💬 评论知识库", divider="rainbow")

    tasks_with_comments = [task for task in st.session_state.get('tasks', []) if task.task_comments]

    if not tasks_with_comments:
        st.info("目前还没有任何任务有评论记录。")
        return

    # --- 1. 创建筛选器 ---
    st.subheader("筛选评论", anchor=False)

    # 获取所有出现过的评论类型用于筛选
    all_comment_types = sorted(
        list(set(comment['type'] for task in tasks_with_comments for comment in task.task_comments)))

    # 获取所有有评论的任务名用于筛选
    task_names_with_comments = sorted(list(set(task.task_name for task in tasks_with_comments)))

    col1, col2 = st.columns(2)
    with col1:
        selected_types = st.multiselect(
            "按评论类型筛选",
            options=all_comment_types,
            default=[],
            help="只看特定类型的评论，如只看“问题记录”。"
        )
    with col2:
        selected_tasks = st.multiselect(
            "按任务名称筛选",
            options=task_names_with_comments,
            default=[],
            help="只看特定任务下的评论。"
        )

    st.markdown("---")

    # --- 2. 准备并过滤数据 ---
    all_comments = []
    for task in tasks_with_comments:
        for comment in task.task_comments:
            # 应用筛选逻辑
            if selected_types and comment['type'] not in selected_types:
                continue
            if selected_tasks and task.task_name not in selected_tasks:
                continue

            all_comments.append({
                "task_name": task.task_name,
                "task_type": task.task_type,
                "content": comment['content'],
                "type": comment['type'],
                "time": comment['time']
            })

    if not all_comments:
        st.warning("根据您的筛选条件，没有找到匹配的评论。")
        return

    # 按评论时间倒序排列，最新的在最前面
    sorted_comments = sorted(all_comments, key=lambda c: c['time'], reverse=True)

    # --- 3. 显示评论列表 ---
    st.subheader(f"找到 {len(sorted_comments)} 条相关评论", anchor=False)

    for comment in sorted_comments:
        icon = config.kanban.COMMENT_ICON_MAP.get(comment['type'], "💬")

        with st.container(border=True):
            header_cols = st.columns([1, 4])
            with header_cols[0]:
                st.markdown(f"##### {icon} {comment['type']}")
            with header_cols[1]:
                st.caption(f"关联任务：**{comment['task_name']}** ({comment['task_type']})")

            st.markdown(comment['content'])
            st.caption(f"记录于: {comment['time'].strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    initialize_app()

    # 创建四个标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📌 任务看板", "📊 统计分析", "📅 日历视图", "💬 评论知识库"])

    with tab1:
        display_main_controls()
        display_kanban_layout()

    with tab2:
        display_statistics_tab()

    with tab3:
        display_timeline_tab()

    with tab4:
        display_comments_tab()


if __name__ == "__main__":
    main()