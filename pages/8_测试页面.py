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
from shared.config import GlobalConfig
from github import Github, UnknownObjectException, GithubException


# =========================================================================================
# 1. 配置模块 (Configuration)
# =========================================================================================

class KanbanPageConfig:
    """存储任务看板页面专属的配置和UI文本。"""

    def __init__(self):
        # 核心配置
        self.DATA_FILE_NAME = "tasks_data.json"
        self.AUTO_REFRESH_INTERVAL_MS = 1000 * 60
        # 页面基础设置
        self.PAGE_TITLE = "每日任务看板"
        self.PAGE_ICON = "📋"
        # 任务状态常量
        self.STATUS_TODO = "未开始"
        self.STATUS_DOING = "进行中"
        self.STATUS_DONE = "已完成"
        # 任务标签/类型
        self.TASK_TYPES = ["主线任务", "副线任务"]
        # 评论区配置
        self.COMMENT_TYPES = ["备注", "问题", "心得"]
        self.COMMENT_ICON_MAP = {"心得": "💡", "问题": "❓", "备注": "📌"}
        self.COMMENT_COLOR_MAP = {"心得": "green", "问题": "red", "备注": "blue"}
        # UI 文本
        self.T_MAIN_TITLE = f"{self.PAGE_ICON} {self.PAGE_TITLE}"
        self.T_CONTROL_PANEL_HEADER = "控制面板"
        self.UI_CONTROL_PANEL_HEIGHT = 360
        self.T_CREATE_TASK_HEADER = "🚀 创建新任务"
        self.T_TASK_NAME_LABEL = "任务名称"
        self.T_TASK_NAME_PLACEHOLDER = "例如：完成项目报告"
        self.T_TASK_TYPE_LABEL = "任务标签"
        self.T_ADD_TASK_BUTTON = "添加任务"
        self.T_WARN_EMPTY_TASK_NAME = "任务名称不能为空！"
        self.T_SUCCESS_TASK_ADDED = "任务 '{task_name}' 已添加！"
        self.T_LOCAL_IO_HEADER = "📥 本地导入/导出"
        self.T_UPLOAD_LABEL = "选择一个 .json 任务文件"
        self.T_UPLOAD_HELP = "从本地文件恢复任务。"
        self.T_DOWNLOAD_BUTTON = "📥 下载任务到本地"
        self.T_DOWNLOAD_HELP = "将当前看板上的所有任务保存为一个 JSON 文件。"
        self.T_EXPORT_FILE_PREFIX = "tasks_export_"
        self.T_GITHUB_SYNC_HEADER = "☁️ GitHub 云同步"
        self.T_GITHUB_SYNC_CAPTION = "数据在每次更改后会自动同步。这里提供手动操作以备不时之需。"
        self.T_GITHUB_PUSH_BUTTON = "⬆️ 推送到 GitHub"
        self.T_GITHUB_PUSH_HELP = "将当前看板数据保存到云端。"
        self.T_GITHUB_PULL_BUTTON = "⬇️ 从 GitHub 拉取"
        self.T_GITHUB_PULL_HELP = "从云端获取最新数据，会覆盖当前看板！"
        self.T_GITHUB_SYNC_INFO = "数据同步基于你的 `secrets.toml` 配置文件。"
        self.T_COLUMN_TODO_HEADER = f"📥 {self.STATUS_TODO}/挂起"
        self.T_COLUMN_DOING_HEADER = f"💻 {self.STATUS_DOING}"
        self.T_COLUMN_DONE_HEADER = f"✅ {self.STATUS_DONE}"
        self.T_CARD_METRIC_ACTIVE_TIME = "⏱️ 任务总耗时 (有效工作)"
        self.T_CARD_METRIC_ACTIVE_TIME_HELP = "这是任务在“进行中”状态下所花费的实际时间总和。每分钟刷新。"
        self.T_CARD_METRIC_LIFESPAN = "🗓️ 任务生命周期 (自创建)"
        self.T_CARD_METRIC_LIFESPAN_HELP = "这是从任务创建开始的总时长。如果任务已完成，则为创建到完成的总时长。每分钟刷新。"
        self.T_CARD_PROGRESS_SLIDER_LABEL = "当前进度（0-100%）"
        self.T_CARD_PROGRESS_SLIDER_HELP = "拖动滑块来更新任务进度。拖到100%会自动完成，拖离100%会自动重新打开。"
        self.T_CARD_COMMENTS_HEADER = "任务评论"
        self.T_CARD_TIME_LOGS_HEADER = "工时记录"
        self.T_CARD_MANAGE_POPOVER = "⚙️ 管理"
        self.T_CARD_EDIT_HEADER = "编辑任务"
        self.T_CARD_SAVE_BUTTON = "💾 保存更改"
        self.T_CARD_DELETE_BUTTON = "🗑️ 删除任务"
        self.T_CARD_DELETE_HELP = "此操作不可撤销！"
        self.T_BUTTON_START = "▶️ 开始"
        self.T_BUTTON_PAUSE = "⏸️ 挂起"
        self.T_BUTTON_PAUSE_HELP = "将任务移回“未开始”并暂停计时，不改变当前进度。"
        self.T_BUTTON_DONE = "✅ 完成"
        self.T_BUTTON_REOPEN = "🔄 重新打开"
        self.T_POPOVER_CREATE_COMMENT = "💬 创建评论"
        self.T_COMMENT_TYPE_LABEL = "评论类型"
        self.T_COMMENT_CONTENT_LABEL = "评论内容..."
        self.T_COMMENT_SUBMIT_BUTTON = "提交"
        self.T_WARN_EMPTY_COMMENT = "评论内容不能为空"
        self.T_TOAST_TIMER_STARTED = "计时开始 ⏱️"
        self.T_TOAST_TIMER_STOPPED = "本段计时结束..."
        self.T_TOAST_COMMENT_ADDED = "任务 '{task_name}' 添加了新评论！"
        self.T_INFO_NO_TIME_LOGS = "暂无完整的工时记录。"
        self.T_ERROR_GITHUB_CONNECTION = "连接到 GitHub 仓库失败: {e}。请检查你的 secrets.toml 文件配置。"
        self.T_SUCCESS_GITHUB_LOAD = "✅ 已从 GitHub 成功加载任务！"
        self.T_INFO_GITHUB_FILE_NOT_FOUND = "在仓库中未找到任务文件。当你第一次推送时，将自动创建。"
        self.T_INFO_GITHUB_REPO_EMPTY = "检测到 GitHub 数据仓库为空。当你第一次推送任务时，将自动创建数据文件。"
        self.T_ERROR_GITHUB_LOAD_UNKNOWN = "从 GitHub 加载任务时发生未知错误: {e}"
        self.T_ERROR_GITHUB_SAVE_FAILED = "无法保存，因为未能连接到 GitHub 仓库。"
        self.T_SUCCESS_GITHUB_UPDATED = "✅ 任务已成功同步到 GitHub！"
        self.T_SUCCESS_GITHUB_CREATED = "✅ 在 GitHub 上创建了新的任务文件并已同步！"
        self.T_ERROR_GITHUB_SYNC_FAILED = "同步到 GitHub 失败: {e}"
        self.T_SUCCESS_IMPORT = "成功导入 {count} 个新任务！"
        self.T_INFO_NO_NEW_TASKS_IMPORTED = "文件中没有发现新任务。"
        self.T_ERROR_JSON_DECODE = "导入失败：文件格式不是有效的 JSON。"
        self.T_ERROR_IMPORT_UNKNOWN = "导入时发生未知错误: {e}"
        self.T_SUCCESS_TASK_UPDATED = "任务 '{task_name}' 已更新!"
        self.T_SUCCESS_TASK_DELETED = "任务 '{task_name}' 已删除。"
        self.T_LOCAL_MODE_INFO = "🚀 **本地开发模式**: 数据已自动从本地文件加载，所有更改将实时保存到本地并同步至 GitHub。"
        self.T_CLOUD_MODE_INFO = "☁️ **云端模式**: 请连接到你的 GitHub 仓库以加载或保存任务。"
        self.T_GITHUB_PRECONFIGURED_INFO = "✅ 已连接到预设的 GitHub 仓库: `{repo}`"
        self.T_GITHUB_CONNECT_HEADER = "🔗 连接到 GitHub"
        self.T_GITHUB_TOKEN_INPUT = "GitHub 个人访问令牌"
        self.T_GITHUB_REPO_INPUT = "GitHub 仓库地址 (例如: 'user/repo')"
        self.T_GITHUB_CONNECT_BUTTON = "连接并加载数据"
        self.T_ERROR_GITHUB_CREDS_MISSING = "请输入完整的 GitHub 令牌和仓库地址。"
        self.T_SUCCESS_LOCAL_SAVE = "✅ 任务已成功保存到本地文件！"
        self.T_ERROR_LOCAL_SAVE = "保存到本地文件失败: {e}"
        self.T_SUCCESS_LOCAL_LOAD = "✅ 已从本地文件成功加载任务！"
        self.T_ERROR_LOCAL_LOAD = "从本地文件加载任务失败: {e}"


class AppConfig:
    """全局唯一的配置实例，整合所有配置类。"""

    def __init__(self):
        self.globals = GlobalConfig()
        self.kanban = KanbanPageConfig()


config = AppConfig()  # 全局配置实例
beijing_tz = config.globals.APP_TIMEZONE  # 时区


# =========================================================================================
# 2. 数据模型 (Data Model)
# =========================================================================================

class Task:
    """
    任务类，定义了一个任务的所有属性和核心业务逻辑。
    包括状态变更、进度更新、评论添加、时间计算等。
    """

    def __init__(self, task_name, task_type):
        self.task_name = task_name
        self.task_type = task_type
        self.creation_time = datetime.now(beijing_tz)
        self.task_id = f"task_{self.creation_time.timestamp()}"
        self.task_progress = 0
        self.status = config.kanban.STATUS_TODO
        self.completion_time = None
        self.task_duration = None
        self.task_comments = []
        self.total_active_time = timedelta(0)
        self.last_start_active_time = None
        self.active_time_segments = []

    def to_dict(self):
        """将任务对象序列化为字典，以便保存为JSON。"""
        return {
            "task_name": self.task_name, "task_type": self.task_type,
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "task_id": self.task_id, "task_progress": self.task_progress, "status": self.status,
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
        """从字典反序列化创建任务对象。"""
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
        """为任务添加一条评论。"""
        comment = {"content": content, "type": comment_type, "time": datetime.now(beijing_tz)}
        self.task_comments.append(comment)
        st.toast(config.kanban.T_TOAST_COMMENT_ADDED.format(task_name=self.task_name), icon="💬")

    def set_status(self, new_status):
        """
        设置任务的新状态，并处理相关的计时逻辑。
        """
        if self.status == new_status: return
        old_status, self.status, now = self.status, new_status, datetime.now(beijing_tz)

        is_starting = new_status == config.kanban.STATUS_DOING and old_status != config.kanban.STATUS_DOING
        is_stopping = new_status != config.kanban.STATUS_DOING and old_status == config.kanban.STATUS_DOING

        if is_starting:
            self.last_start_active_time = now
            st.toast(config.kanban.T_TOAST_TIMER_STARTED)
        elif is_stopping and self.last_start_active_time:
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
        elif new_status != config.kanban.STATUS_DONE:
            self.completion_time, self.task_duration = None, None
            if old_status == config.kanban.STATUS_DONE and self.task_progress == 100: self.task_progress = 90

    def update_progress(self, new_progress):
        """根据新的进度值更新任务状态。"""
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
        """计算任务的总生命周期（从创建到现在的总时长）。"""
        return self.task_duration if self.completion_time else datetime.now(beijing_tz) - self.creation_time

    def get_total_active_duration(self):
        """计算任务的总活跃时长（所有“进行中”状态的时间总和）。"""
        current_active = datetime.now(
            beijing_tz) - self.last_start_active_time if self.status == config.kanban.STATUS_DOING and self.last_start_active_time else timedelta(
            0)
        return self.total_active_time + current_active


# =========================================================================================
# 3. 数据管理模块 (Data Management)
# =========================================================================================

class DataManager:
    """
    数据同步类，集中处理所有数据的导入、导出和云同步操作。
    """

    def __init__(self, app_config):
        self.config = app_config
        self.g_config = app_config.globals
        self.k_config = app_config.kanban

    @st.cache_resource
    def _get_github_repo(_self, token=None, repo_name=None):
        """
        获取并缓存GitHub仓库对象。
        使用 _self 是因为 st.cache_resource 会改变 'self' 的行为。
        """
        g_token = token or _self.g_config.GITHUB_TOKEN
        g_repo = repo_name or _self.g_config.GITHUB_PRIVATE_REPO
        if not g_token or not g_repo:
            return None
        try:
            return Github(g_token).get_repo(g_repo)
        except GithubException as e:
            st.error(_self.k_config.T_ERROR_GITHUB_CONNECTION.format(e=e))
            return None

    def _load_from_github(self, token=None, repo_name=None):
        """从GitHub加载任务列表。"""
        repo = self._get_github_repo(token, repo_name)
        if repo is None: return None
        try:
            content_file = repo.get_contents(self.k_config.DATA_FILE_NAME)
            content = content_file.decoded_content.decode("utf-8")
            st.toast(self.k_config.T_SUCCESS_GITHUB_LOAD, icon="🎉")
            return [Task.from_dict(task_data) for task_data in json.loads(content)]
        except UnknownObjectException:
            st.info(self.k_config.T_INFO_GITHUB_FILE_NOT_FOUND)
            return []
        except Exception as e:
            st.error(self.k_config.T_ERROR_GITHUB_LOAD_UNKNOWN.format(e=e))
            return []

    def _save_to_github(self, tasks, token=None, repo_name=None):
        """保存任务列表到GitHub。"""
        repo = self._get_github_repo(token, repo_name)
        if repo is None:
            st.error(self.k_config.T_ERROR_GITHUB_SAVE_FAILED)
            return
        content = json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False)
        commit_message = f"Tasks updated at {datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            file = repo.get_contents(self.k_config.DATA_FILE_NAME)
            repo.update_file(file.path, commit_message, content, file.sha)
            st.toast(self.k_config.T_SUCCESS_GITHUB_UPDATED, icon="⬆️")
        except UnknownObjectException:
            repo.create_file(self.k_config.DATA_FILE_NAME, commit_message, content)
            st.toast(self.k_config.T_SUCCESS_GITHUB_CREATED, icon="☁️")
        except Exception as e:
            st.error(self.k_config.T_ERROR_GITHUB_SYNC_FAILED.format(e=e))

    def _load_from_local(self):
        """从本地文件加载任务列表。"""
        path = self.g_config.LOCAL_DATA_FILE_PATH
        if not os.path.exists(path): return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content: return []
            st.toast(self.k_config.T_SUCCESS_LOCAL_LOAD, icon="🏠")
            return [Task.from_dict(td) for td in json.loads(content)]
        except Exception as e:
            st.error(self.k_config.T_ERROR_LOCAL_LOAD.format(e=e))
            return []

    def _save_to_local(self, tasks):
        """保存任务列表到本地文件。"""
        path = self.g_config.LOCAL_DATA_FILE_PATH
        try:
            content = json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            st.toast(self.k_config.T_SUCCESS_LOCAL_SAVE, icon="💾")
        except Exception as e:
            st.error(self.k_config.T_ERROR_LOCAL_SAVE.format(e=e))

    def initial_load(self):
        """
        应用初始化时加载数据。
        本地模式：优先本地，若本地为空则尝试GitHub。
        云端模式：默认为空，等待用户连接。
        """
        if self.g_config.RUN_MODE == "local":
            tasks = self._load_from_local()
            if not tasks and self.g_config.GITHUB_TOKEN:
                tasks = self._load_from_github()
            return tasks
        else:  # cloud mode
            return []

    def sync_state(self):
        """
        根据运行模式，将当前st.session_state.tasks同步到持久化存储。
        """
        tasks = st.session_state.get('tasks', [])
        if self.g_config.RUN_MODE == "local":
            self._save_to_local(tasks)
            if self.g_config.GITHUB_TOKEN:
                self._save_to_github(tasks)
        else:  # cloud mode
            if 'github_token' in st.session_state and 'github_repo' in st.session_state:
                self._save_to_github(tasks, st.session_state.github_token, st.session_state.github_repo)

    def import_from_file(self, uploaded_file):
        """从上传的JSON文件导入新任务。"""
        if uploaded_file is None: return
        try:
            tasks_data = json.load(uploaded_file)
            existing_ids = {task.task_id for task in st.session_state.tasks}
            new_tasks = [Task.from_dict(td) for td in tasks_data if td.get("task_id") not in existing_ids]
            if new_tasks:
                st.session_state.tasks.extend(new_tasks)
                st.success(self.k_config.T_SUCCESS_IMPORT.format(count=len(new_tasks)))
                self.sync_state()
                st.rerun()
            else:
                st.info(self.k_config.T_INFO_NO_NEW_TASKS_IMPORTED)
        except json.JSONDecodeError:
            st.error(self.k_config.T_ERROR_JSON_DECODE)
        except Exception as e:
            st.error(self.k_config.T_ERROR_IMPORT_UNKNOWN.format(e=e))

    def get_export_data(self):
        """生成用于导出的JSON字符串。"""
        tasks = st.session_state.get('tasks', [])
        return json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False) if tasks else "{}"

    def connect_and_load_from_github(self, g_token, g_repo):
        """云端模式下，连接并从GitHub加载数据。"""
        tasks = self._load_from_github(g_token, g_repo)
        if tasks is not None:
            st.session_state.github_token = g_token
            st.session_state.github_repo = g_repo
            st.session_state.tasks = tasks
            st.rerun()


# =========================================================================================
# 4. UI 渲染模块 (UI Rendering)
# =========================================================================================

class KanbanUI:
    """
    UI类，将所有Streamlit组件的渲染操作集中在此，使主逻辑更清晰。
    """

    def __init__(self, app_config, data_manager):
        self.config = app_config
        self.k_config = app_config.kanban
        self.g_config = app_config.globals
        self.data_manager = data_manager

    # --- 私有辅助渲染函数 ---
    def _render_task_metrics(self, task):
        """渲染任务卡片中的核心指标（耗时、生命周期）。"""
        col_time1, col_time2 = st.columns(2)
        col_time1.metric(self.k_config.T_CARD_METRIC_ACTIVE_TIME,
                         format_timedelta_to_str(task.get_total_active_duration()),
                         help=self.k_config.T_CARD_METRIC_ACTIVE_TIME_HELP)
        col_time2.metric(self.k_config.T_CARD_METRIC_LIFESPAN,
                         format_timedelta_to_str(task.get_total_lifespan_duration()),
                         help=self.k_config.T_CARD_METRIC_LIFESPAN_HELP)

    def _render_task_controls(self, task):
        """渲染任务卡片中的状态控制按钮（开始、暂停等）。"""

        # 定义回调函数
        def handle_status_change(t, new_status):
            t.set_status(new_status)
            self.data_manager.sync_state()

        cols = st.columns(4)
        if task.status == self.k_config.STATUS_TODO:
            cols[0].button(self.k_config.T_BUTTON_START, key=f"start_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.k_config.STATUS_DOING), use_container_width=True)
        if task.status == self.k_config.STATUS_DOING:
            cols[1].button(self.k_config.T_BUTTON_PAUSE, key=f"pause_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.k_config.STATUS_TODO), help=self.k_config.T_BUTTON_PAUSE_HELP,
                           use_container_width=True)
            cols[2].button(self.k_config.T_BUTTON_DONE, key=f"done_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.k_config.STATUS_DONE), use_container_width=True)
        if task.status == self.k_config.STATUS_DONE:
            cols[3].button(self.k_config.T_BUTTON_REOPEN, key=f"reopen_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.k_config.STATUS_DOING), use_container_width=True)
        st.write("")

    def _render_task_progress_slider(self, task):
        """渲染任务进度滑块。"""

        def handle_progress_change(task_id):
            task_to_update = next((t for t in st.session_state.tasks if t.task_id == task_id), None)
            if task_to_update:
                new_progress = st.session_state[f"progress_{task_id}"]
                task_to_update.update_progress(new_progress)
                self.data_manager.sync_state()

        st.slider(self.k_config.T_CARD_PROGRESS_SLIDER_LABEL, 0, 100, task.task_progress, 10, "%d%%",
                  key=f"progress_{task.task_id}", help=self.k_config.T_CARD_PROGRESS_SLIDER_HELP,
                  on_change=handle_progress_change, args=(task.task_id,))

    def _render_task_time_logs(self, task):
        """渲染任务工时记录。"""
        st.subheader(self.k_config.T_CARD_TIME_LOGS_HEADER, divider='rainbow')
        if task.status == self.k_config.STATUS_DOING and task.last_start_active_time:
            start_str = task.last_start_active_time.strftime('%Y-%m-%d %H:%M:%S')
            duration_str = format_timedelta_to_str(datetime.now(beijing_tz) - task.last_start_active_time)
            st.success(f"**当前:** 正在计时... ({duration_str})\n开始于: {start_str}")

        if not task.active_time_segments and task.status != self.k_config.STATUS_DOING:
            st.caption(self.k_config.T_INFO_NO_TIME_LOGS)
        else:
            sorted_segments = sorted(task.active_time_segments, key=lambda s: s['start_time'], reverse=True)
            for date_val, group in groupby(sorted_segments, key=lambda s: s['start_time'].date()):
                group_list = list(group)
                total_duration_str = format_timedelta_to_str(sum((s['duration'] for s in group_list), timedelta()))
                with st.expander(f"**{date_val.strftime('%Y-%m-%d')}** - 总计: **{total_duration_str}**"):
                    for s in group_list:
                        duration, start, end = format_timedelta_to_str(s['duration']), s['start_time'].strftime(
                            '%H:%M:%S'), s['end_time'].strftime('%H:%M:%S')
                        icon = "⏸️" if s['stopped_as'] == self.k_config.STATUS_TODO else "✅"
                        st.info(f"**{duration}** (从 {start} 到 {end}) {icon}")

    def _render_task_comments_section(self, task):
        """渲染任务评论区（包括添加评论的表单和评论列表）。"""
        st.subheader(self.k_config.T_CARD_COMMENTS_HEADER, divider='rainbow')
        with st.popover(self.k_config.T_POPOVER_CREATE_COMMENT):
            with st.form(key=f"comment_form_{task.task_id}", clear_on_submit=True):
                ctype = st.selectbox(self.k_config.T_COMMENT_TYPE_LABEL, self.k_config.COMMENT_TYPES)
                content = st.text_area(self.k_config.T_COMMENT_CONTENT_LABEL, height=100)
                if st.form_submit_button(self.k_config.T_COMMENT_SUBMIT_BUTTON):
                    if content:
                        task.add_comment(content, ctype)
                        self.data_manager.sync_state()
                        st.rerun()
                    else:
                        st.warning(self.k_config.T_WARN_EMPTY_COMMENT)

        if task.task_comments:
            with st.container(height=250):
                for c in reversed(task.task_comments):
                    icon = self.k_config.COMMENT_ICON_MAP.get(c['type'], "💬")
                    color = self.k_config.COMMENT_COLOR_MAP.get(c['type'], "gray")
                    with st.chat_message(name=c['type'], avatar=icon):
                        st.markdown(f":{color}[{c['content']}]")
                        st.caption(f"_{c['time'].strftime('%Y-%m-%d %H:%M')}_")

    def _render_task_management_popover(self, task):
        """渲染任务管理弹窗（编辑和删除）。"""
        st.divider()
        col_info, col_manage = st.columns([3, 1])
        with col_info:
            st.caption(f"ID: {task.task_id}")
            st.caption(f"创建于: {task.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")

        with col_manage, st.popover(self.k_config.T_CARD_MANAGE_POPOVER):
            with st.form(key=f"edit_form_{task.task_id}"):
                st.subheader(self.k_config.T_CARD_EDIT_HEADER, anchor=False)
                edited_name = st.text_input(self.k_config.T_TASK_NAME_LABEL, value=task.task_name)

                existing_types = sorted(list(set(t.task_type for t in st.session_state.get('tasks', []))))
                combined_types = sorted(list(set(self.k_config.TASK_TYPES + existing_types)))
                if task.task_type not in combined_types: combined_types.append(task.task_type)

                index = combined_types.index(task.task_type) if task.task_type in combined_types else 0
                edited_type = st.selectbox(self.k_config.T_TASK_TYPE_LABEL, options=combined_types, index=index)

                if st.form_submit_button(self.k_config.T_CARD_SAVE_BUTTON, use_container_width=True):
                    task.task_name, task.task_type = edited_name, edited_type
                    st.toast(self.k_config.T_SUCCESS_TASK_UPDATED.format(task_name=task.task_name), icon="✅")
                    self.data_manager.sync_state()
                    st.rerun()

            st.divider()
            if st.button(self.k_config.T_CARD_DELETE_BUTTON, type="primary", use_container_width=True,
                         help=self.k_config.T_CARD_DELETE_HELP):
                st.session_state.tasks = [t for t in st.session_state.tasks if t.task_id != task.task_id]
                st.toast(self.k_config.T_SUCCESS_TASK_DELETED.format(task_name=task.task_name), icon="🗑️")
                self.data_manager.sync_state()
                st.rerun()

    # --- 公共渲染函数 ---

    def render_task_card(self, task):
        """渲染单个任务卡片的所有内容。"""
        with st.expander(f"`{task.task_type}` {task.task_name}", expanded=True):
            st.subheader(task.task_name, divider="rainbow")
            self._render_task_metrics(task)
            self._render_task_controls(task)
            self._render_task_progress_slider(task)
            self._render_task_time_logs(task)
            self._render_task_comments_section(task)
            self._render_task_management_popover(task)

    def render_kanban_layout(self):
        """渲染看板的三列布局（未开始、进行中、已完成）。"""
        tasks = st.session_state.get('tasks', [])
        sorted_tasks = sorted(tasks, key=lambda x: x.creation_time, reverse=True)
        tasks_todo = [t for t in sorted_tasks if t.status == self.k_config.STATUS_TODO]
        tasks_doing = [t for t in sorted_tasks if t.status == self.k_config.STATUS_DOING]
        tasks_done = [t for t in sorted_tasks if t.status == self.k_config.STATUS_DONE]

        col1, col2, col3 = st.columns(3, gap="large")
        with col1:
            st.header(f"{self.k_config.T_COLUMN_TODO_HEADER} ({len(tasks_todo)})", divider="rainbow")
            for task in tasks_todo: self.render_task_card(task)
        with col2:
            st.header(f"{self.k_config.T_COLUMN_DOING_HEADER} ({len(tasks_doing)})", divider="rainbow")
            for task in tasks_doing: self.render_task_card(task)
        with col3:
            st.header(f"{self.k_config.T_COLUMN_DONE_HEADER} ({len(tasks_done)})", divider="rainbow")
            for task in tasks_done: self.render_task_card(task)

    def _render_github_connection_panel(self):
        """渲染云端模式下的GitHub连接面板。"""
        with st.container(border=True):
            st.subheader(self.k_config.T_GITHUB_CONNECT_HEADER, anchor=False)
            is_connected = 'github_token' in st.session_state and 'github_repo' in st.session_state

            if not is_connected:
                st.info(self.k_config.T_CLOUD_MODE_INFO)
                col_token, col_repo = st.columns(2)
                g_token = col_token.text_input(self.k_config.T_GITHUB_TOKEN_INPUT, type="password")
                g_repo = col_repo.text_input(self.k_config.T_GITHUB_REPO_INPUT, placeholder="your-username/your-repo")
                if st.button(self.k_config.T_GITHUB_CONNECT_BUTTON, use_container_width=True):
                    if g_token and g_repo:
                        self.data_manager.connect_and_load_from_github(g_token, g_repo)
                    else:
                        st.warning(self.k_config.T_ERROR_GITHUB_CREDS_MISSING)
            else:
                st.success(f"✅ 已连接到仓库: **{st.session_state.github_repo}**")

                def disconnect():
                    keys_to_del = ['github_token', 'github_repo']
                    for key in keys_to_del:
                        if key in st.session_state: del st.session_state[key]
                    st.session_state.tasks = []
                    st.toast("已断开连接", icon="🔗")

                st.button("🔌 断开连接", on_click=disconnect, use_container_width=True, type="secondary")

    def render_main_controls(self):
        """渲染主控制面板，包括创建任务、导入导出和云同步。"""
        st.header(self.k_config.T_CONTROL_PANEL_HEADER, divider="rainbow")

        if self.g_config.RUN_MODE == "local":
            st.info(self.k_config.T_LOCAL_MODE_INFO)
        else:
            self._render_github_connection_panel()
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1, st.container(border=True, height=self.k_config.UI_CONTROL_PANEL_HEIGHT):
            st.subheader(self.k_config.T_CREATE_TASK_HEADER, anchor=False)
            existing_types = sorted(list(set(t.task_type for t in st.session_state.get('tasks', []))))
            combined_types = sorted(list(set(self.k_config.TASK_TYPES + existing_types)))
            ADD_NEW_OPTION = "➕ 添加新类型..."
            options = combined_types + [ADD_NEW_OPTION]
            selected_option = st.selectbox(label=self.k_config.T_TASK_TYPE_LABEL, options=options)
            new_type_name = st.text_input("请输入新的类型名称:",
                                          key="new_type_name") if selected_option == ADD_NEW_OPTION else ""

            with st.form(key="new_task_form"):
                name = st.text_input(self.k_config.T_TASK_NAME_LABEL, placeholder=self.k_config.T_TASK_NAME_PLACEHOLDER)
                if st.form_submit_button(self.k_config.T_ADD_TASK_BUTTON, use_container_width=True):
                    if name:
                        final_task_type = new_type_name if selected_option == ADD_NEW_OPTION and new_type_name else selected_option if selected_option != ADD_NEW_OPTION else None
                        if final_task_type:
                            st.session_state.tasks.append(Task(task_name=name, task_type=final_task_type))
                            st.success(self.k_config.T_SUCCESS_TASK_ADDED.format(task_name=name))
                            self.data_manager.sync_state()
                            st.rerun()
                        else:
                            st.warning("您选择了添加新类型，但未输入类型名称。")
                    else:
                        st.warning(self.k_config.T_WARN_EMPTY_TASK_NAME)

        with col2, st.container(border=True, height=self.k_config.UI_CONTROL_PANEL_HEIGHT):
            st.subheader(self.k_config.T_LOCAL_IO_HEADER, anchor=False)
            uploaded = st.file_uploader(self.k_config.T_UPLOAD_LABEL, type=["json"], help=self.k_config.T_UPLOAD_HELP)
            if uploaded: self.data_manager.import_from_file(uploaded)

            fname = f"{self.k_config.T_EXPORT_FILE_PREFIX}{datetime.now(beijing_tz).strftime('%Y%m%d_%H%M%S')}.json"
            st.download_button(self.k_config.T_DOWNLOAD_BUTTON, self.data_manager.get_export_data(), fname,
                               "application/json", help=self.k_config.T_DOWNLOAD_HELP, use_container_width=True,
                               disabled=not st.session_state.tasks)

            if self.g_config.RUN_MODE == "cloud":
                st.button("⬆️ 手动同步到 GitHub", on_click=self.data_manager.sync_state, use_container_width=True,
                          disabled='github_token' not in st.session_state)

    # ... 渲染其他标签页的函数 ...
    def render_statistics_tab(self):
        """渲染统计分析标签页。"""
        # (这部分代码耦合度不高，保持原样，仅放入类方法中)
        st.header("任务统计分析 📊", divider="rainbow")
        tasks = st.session_state.get('tasks', [])
        if not tasks:
            st.info("看板上还没有任务，快去创建一个吧！")
            return

        df = pd.DataFrame([{"creation_time": t.creation_time, "completion_time": t.completion_time, "status": t.status,
                            "task_type": t.task_type, "total_active_time_seconds": t.total_active_time.total_seconds(),
                            "task_duration_seconds": t.task_duration.total_seconds() if t.task_duration else None} for t
                           in tasks])
        df['total_active_time_hours'] = df['total_active_time_seconds'] / 3600
        df['task_duration_hours'] = df['task_duration_seconds'] / 3600

        st.subheader("核心指标", anchor=False)
        total_tasks, completed_tasks = len(df), df[df['status'] == self.k_config.STATUS_DONE].shape[0]
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        avg_active_time_sec = df[df['status'] == self.k_config.STATUS_DONE]['total_active_time_seconds'].mean()
        avg_lifespan_sec = df[df['status'] == self.k_config.STATUS_DONE]['task_duration_seconds'].mean()

        kpi_cols = st.columns(4)
        kpi_cols[0].metric("总任务数", f"{total_tasks} 个")
        kpi_cols[1].metric("完成率", f"{completion_rate:.1f}%")
        kpi_cols[2].metric("平均活跃时长", format_timedelta_to_str(timedelta(seconds=avg_active_time_sec)) if pd.notna(
            avg_active_time_sec) else "N/A")
        kpi_cols[3].metric("平均生命周期", format_timedelta_to_str(timedelta(seconds=avg_lifespan_sec)) if pd.notna(
            avg_lifespan_sec) else "N/A")

        st.markdown("---")
        st.subheader("任务分布", anchor=False)
        col1, col2 = st.columns(2)
        with col1:
            status_counts = df['status'].value_counts()
            fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="任务状态分布",
                         hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            type_counts = df['task_type'].value_counts()
            fig = px.pie(type_counts, values=type_counts.values, names=type_counts.index, title="任务类型分布", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

    def render_timeline_tab(self):
        """渲染日历/时间线视图标签页。"""
        # (这部分代码耦合度不高，保持原样，仅放入类方法中)
        st.header("任务时间线视图 📅", divider="rainbow")
        tasks = st.session_state.get('tasks', [])
        timeline_data = []
        for task in tasks:
            for segment in task.active_time_segments:
                timeline_data.append(
                    {"Task": task.task_name, "Start": segment['start_time'], "Finish": segment['end_time'],
                     "Type": task.task_type})
            if task.status == self.k_config.STATUS_DOING and task.last_start_active_time:
                timeline_data.append(
                    {"Task": task.task_name, "Start": task.last_start_active_time, "Finish": datetime.now(beijing_tz),
                     "Type": "进行中"})

        if not timeline_data:
            st.info("没有任务活动记录，请先开始并完成一些任务以生成时间线。")
            return

        df = pd.DataFrame(timeline_data)
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Type", title="任务活动甘特图")
        fig.update_yaxes(categoryorder='total ascending')
        st.plotly_chart(fig, use_container_width=True)

    def render_comments_tab(self):
        """渲染评论知识库标签页。"""
        # (这部分代码耦合度不高，保持原样，仅放入类方法中)
        st.header("💬 评论知识库", divider="rainbow")
        tasks_with_comments = [task for task in st.session_state.get('tasks', []) if task.task_comments]
        if not tasks_with_comments:
            st.info("目前还没有任何任务有评论记录。")
            return

        all_comment_types = sorted(
            list(set(comment['type'] for task in tasks_with_comments for comment in task.task_comments)))
        task_names_with_comments = sorted(list(set(task.task_name for task in tasks_with_comments)))
        col1, col2 = st.columns(2)
        selected_types = col1.multiselect("按评论类型筛选", options=all_comment_types)
        selected_tasks = col2.multiselect("按任务名称筛选", options=task_names_with_comments)
        st.markdown("---")

        all_comments = []
        for task in tasks_with_comments:
            if selected_tasks and task.task_name not in selected_tasks: continue
            for comment in task.task_comments:
                if selected_types and comment['type'] not in selected_types: continue
                all_comments.append(
                    {"task_name": task.task_name, "task_type": task.task_type, "content": comment['content'],
                     "type": comment['type'], "time": comment['time']})

        if not all_comments:
            st.warning("根据您的筛选条件，没有找到匹配的评论。")
            return

        sorted_comments = sorted(all_comments, key=lambda c: c['time'], reverse=True)
        st.subheader(f"找到 {len(sorted_comments)} 条相关评论", anchor=False)
        for comment in sorted_comments:
            icon = self.k_config.COMMENT_ICON_MAP.get(comment['type'], "💬")
            with st.container(border=True):
                st.markdown(f"##### {icon} {comment['type']} (来自任务: **{comment['task_name']}**)")
                st.markdown(comment['content'])
                st.caption(f"记录于: {comment['time'].strftime('%Y-%m-%d %H:%M:%S')}")


# =========================================================================================
# 5. 辅助函数和主程序 (Helpers & Main App)
# =========================================================================================

def format_timedelta_to_str(duration):
    """将 timedelta 对象格式化为易读的字符串，例如 '1天2小时3分钟'。"""
    if not isinstance(duration, timedelta) or duration.total_seconds() <= 0: return "0秒"
    total_seconds = int(duration.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days > 0: parts.append(f"{days}天")
    if hours > 0: parts.append(f"{hours}小时")
    if minutes > 0: parts.append(f"{minutes}分钟")
    if not parts and seconds > 0: parts.append(f"{seconds}秒")
    return "".join(parts) if parts else "0秒"


def initialize_app(data_manager):
    """
    初始化应用页面配置和会话状态。
    """
    st.set_page_config(page_title=config.kanban.PAGE_TITLE, page_icon=config.kanban.PAGE_ICON, layout="wide")
    st.title(config.kanban.T_MAIN_TITLE)
    st.markdown("---")

    # 自动刷新
    st_autorefresh(interval=config.kanban.AUTO_REFRESH_INTERVAL_MS, key="clock_refresher")

    # 侧边栏
    create_common_sidebar()

    # 初始化任务列表
    if 'tasks' not in st.session_state:
        st.session_state.tasks = data_manager.initial_load()


def main():
    """
    主函数，应用的入口点。
    负责初始化、创建实例和渲染标签页。
    """
    # 1. 创建核心类的实例
    data_manager = DataManager(config)

    # 2. 初始化页面和 session_state
    initialize_app(data_manager)

    # 3. 创建UI实例 (在初始化之后，因为它可能需要 session_state)
    ui = KanbanUI(config, data_manager)

    # 4. 创建并渲染标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📌 任务看板", "📊 统计分析", "📅 日历视图", "💬 评论知识库"])

    with tab1:
        ui.render_main_controls()
        ui.render_kanban_layout()
    with tab2:
        ui.render_statistics_tab()
    with tab3:
        ui.render_timeline_tab()
    with tab4:
        ui.render_comments_tab()


if __name__ == "__main__":
    main()