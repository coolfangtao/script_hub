# 0_任务看板.py
import streamlit as st
import json
import os
import tempfile
import pandas as pd
import plotly.express as px
from itertools import groupby
from datetime import datetime, timedelta
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
        """将任务对象序列化为字典（已修复：现在会保存评论的id和status）。"""
        return {
            "task_name": self.task_name,
            "task_type": self.task_type,
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "task_id": self.task_id,
            "task_progress": self.task_progress,
            "status": self.status,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "task_duration_seconds": self.task_duration.total_seconds() if self.task_duration else None,
            # --- 核心修复点：序列化所有评论字段 ---
            "task_comments": [
                {
                    "id": c.get("id"),
                    "content": c.get("content"),
                    "type": c.get("type"),
                    "time": c.get("time").isoformat(),
                    "status": c.get("status")
                } for c in self.task_comments
            ],
            "total_active_time_seconds": self.total_active_time.total_seconds(),
            "last_start_active_time": self.last_start_active_time.isoformat() if self.last_start_active_time else None,
            "active_time_segments": [
                {
                    "start_time": s["start_time"].isoformat(),
                    "end_time": s["end_time"].isoformat(),
                    "duration_seconds": s["duration"].total_seconds(),
                    "stopped_as": s["stopped_as"]
                } for s in self.active_time_segments
            ]
        }

    @classmethod
    def from_dict(cls, data):
        """从字典反序列化创建任务对象（已精简，不再需要复杂的兼容性逻辑）。"""
        task = cls(data.get("task_name", "无标题任务"), data.get("task_type", "未分类"))

        # 加载任务属性（保持稳健的.get）
        task.creation_time = datetime.fromisoformat(data["creation_time"])
        task.task_id = data.get("task_id", f"task_{task.creation_time.timestamp()}")
        task.task_progress = data.get("task_progress", 0)
        task.status = data.get("status", config.kanban.STATUS_TODO)
        task.completion_time = datetime.fromisoformat(data["completion_time"]) if data.get("completion_time") else None
        if data.get("task_duration_seconds") is not None:
            task.task_duration = timedelta(seconds=data["task_duration_seconds"])
        task.total_active_time = timedelta(seconds=data.get("total_active_time_seconds", 0))
        if data.get("last_start_active_time"):
            task.last_start_active_time = datetime.fromisoformat(data["last_start_active_time"])

        # --- 精简点：评论加载逻辑变得非常简单 ---
        # 因为我们假定所有评论数据都是结构完整的
        task.task_comments = [
            {
                "id": c.get("id"),
                "content": c.get("content"),
                "type": c.get("type"),
                "time": datetime.fromisoformat(c.get("time")),
                "status": c.get("status")
            } for c in data.get("task_comments", [])
        ]

        task.active_time_segments = [
            {
                "start_time": datetime.fromisoformat(s["start_time"]),
                "end_time": datetime.fromisoformat(s["end_time"]),
                "duration": timedelta(seconds=s["duration_seconds"]),
                "stopped_as": s["stopped_as"]
            } for s in data.get("active_time_segments", [])
        ]
        return task

    def add_comment(self, content, comment_type):
        """为任务添加一条评论（已升级，增加ID和状态）。"""
        now = datetime.now(beijing_tz)
        comment = {
            "id": f"comment_{now.timestamp()}",  # 新增：唯一ID
            "content": content,
            "type": comment_type,
            "time": now,
            "status": "未解决" if comment_type == "问题" else None  # 新增：为“问题”类型自动设置状态
        }
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

    # --- 新增：以下是用于计算效率的核心方法 ---
    def get_first_start_time(self):
        """
        从工时记录中动态计算并返回首次开始任务的时间。
        如果没有任何工时记录，则返回 None。
        """
        if not self.active_time_segments:
            return None
        # 找到所有工时记录中，start_time 最早的那一个
        earliest_segment = min(self.active_time_segments, key=lambda segment: segment['start_time'])
        return earliest_segment['start_time']

    def get_doing_efficiency(self):
        """
        计算任务的执行效率。
        效率 = 总活跃时长 / (完成时间 - 首次开始时间)
        """
        first_start = self.get_first_start_time()

        # 必须是已完成、且能计算出首次开始时间的任务才能计算
        if self.status != config.kanban.STATUS_DONE or not first_start or not self.completion_time:
            return None

        total_active_duration = self.get_total_active_duration()
        total_work_span = self.completion_time - first_start

        # 避免除以零或负数时间的错误
        if total_work_span.total_seconds() <= 0:
            return 1.0

        efficiency = total_active_duration.total_seconds() / total_work_span.total_seconds()
        # 效率可能因为计时误差略大于1，将其限制在1以内
        return min(efficiency, 1.0)


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
        """保存任务列表到本地文件（使用原子写入）。"""
        path = self.g_config.LOCAL_DATA_FILE_PATH
        try:
            content = json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False)
            # 1. 创建一个与目标文件在同一目录下的临时文件
            temp_dir = os.path.dirname(path)
            # 使用 tempfile 确保文件名唯一且安全
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=temp_dir, delete=False) as tmp_file:
                tmp_file.write(content)
                temp_path = tmp_file.name  # 获取临时文件名

            # 2. 只有在成功写入临时文件后，才将其重命名为目标文件
            # 在大多数操作系统上，重命名是原子操作
            os.replace(temp_path, path)
            st.toast(self.k_config.T_SUCCESS_LOCAL_SAVE, icon="💾")
        except Exception as e:
            st.error(self.k_config.T_ERROR_LOCAL_SAVE.format(e=e))
            # 如果出错，尝试清理临时文件
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

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

    # --- 新增：这是一个全新的辅助函数，用于计算每日时间利用率 ---
    def _calculate_daily_utilization(self, tasks, window_start_hour, window_end_hour, crosses_midnight=False):
        """
        （跨天增强版）计算指定时间窗口的利用率。
        - crosses_midnight: 标记时间窗口是否跨过午夜。
        """
        daily_stats = {}

        # 1. 遍历所有工时记录
        for task in tasks:
            for segment in task.active_time_segments:
                # 确定工时记录的“归属日”
                day = segment['start_time'].date()

                # 2. 定义当天的分析窗口 (可能是跨天的)
                window_start_dt = datetime.combine(day, datetime.min.time(), tzinfo=beijing_tz).replace(
                    hour=window_start_hour)

                # 如果跨天，结束时间就是第二天的相应小时
                if crosses_midnight:
                    window_end_dt = datetime.combine(day + timedelta(days=1), datetime.min.time(),
                                                     tzinfo=beijing_tz).replace(hour=window_end_hour)
                else:
                    window_end_dt = datetime.combine(day, datetime.min.time(), tzinfo=beijing_tz).replace(
                        hour=window_end_hour)

                # 3. 计算工时记录与分析窗口的交集
                overlap_start = max(segment['start_time'], window_start_dt)
                overlap_end = min(segment['end_time'], window_end_dt)

                if overlap_end > overlap_start:
                    if day not in daily_stats:
                        daily_stats[day] = {"window_seconds": 0}
                    daily_stats[day]["window_seconds"] += (overlap_end - overlap_start).total_seconds()

        if not daily_stats:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(daily_stats, orient='index')
        df.index = pd.to_datetime(df.index)

        # 4. 计算总可用时长
        if crosses_midnight:
            # (24 - start) + end
            available_hours = (24 - window_start_hour) + window_end_hour
        else:
            available_hours = window_end_hour - window_start_hour

        available_seconds = available_hours * 3600
        df['window_utilization_pct'] = (df['window_seconds'] / available_seconds * 100) if available_seconds > 0 else 0
        return df.sort_index(ascending=False)

    def _display_utilization_kpis(self, df, prefix=""):
        """
        计算并展示利用率的关键指标。（已更新为动态均值计算）
        """
        today = datetime.now(beijing_tz).date()

        # 提取今日数据
        today_series = df[df.index.date == today]
        today_util = today_series['window_utilization_pct'].iloc[0] if not today_series.empty else 0

        # 提取所有有活动记录的历史数据
        historical_df = df[df.index.date < today]

        # 指标1: 上一个活动日的利用率
        last_day_util = historical_df['window_utilization_pct'].iloc[0] if not historical_df.empty else 0
        delta = today_util - last_day_util if last_day_util > 0 else None

        # --- 修改点：动态计算最近N日的平均值 ---

        # 1. 获取用于计算平均值的数据（最多5天）
        # pandas的.head(5)方法很智能，如果数据不足5行，它会返回所有行
        df_for_avg = historical_df.head(5)

        # 2. 计算实际天数和平均值
        num_days_for_avg = len(df_for_avg)
        last_n_days_avg = df_for_avg['window_utilization_pct'].mean() if not df_for_avg.empty else 0

        # 3. 创建动态标签
        avg_label = f"近{num_days_for_avg}日{prefix}平均" if num_days_for_avg > 0 else f"历史{prefix}平均"

        # --- 修改结束 ---

        kpi_cols = st.columns(3)
        kpi_cols[0].metric(
            label=f"今日{prefix}利用率",
            value=f"{today_util:.1f}%",
            delta=f"{delta:.1f}%" if delta is not None else "—",
            help="与上一个有记录的工作日相比的变化。"
        )
        kpi_cols[1].metric(
            label=f"上一活动日{prefix}利用率",
            value=f"{last_day_util:.1f}%"
        )
        # 使用新的动态标签和计算值
        kpi_cols[2].metric(
            label=avg_label,
            value=f"{last_n_days_avg:.1f}%"
        )


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
        """渲染任务评论区（最终布局优化版，确保文本完整显示）。"""

        # --- 布局优化 1：将标题和“创建评论”按钮放在同一行 ---
        header_cols = st.columns([2, 1])
        with header_cols[0]:
            st.subheader(self.k_config.T_CARD_COMMENTS_HEADER, divider='rainbow')
        with header_cols[1]:
            # 正确使用配置类中的文本变量，而不是硬编码
            with st.popover(f"{self.k_config.T_POPOVER_CREATE_COMMENT}", use_container_width=True):
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

        # 数据分组
        problems = [c for c in task.task_comments if c['type'] == '问题']
        other_comments = [c for c in task.task_comments if c['type'] != '问题']

        # 定义回调函数
        def on_status_change(t, c_id, key):
            comment = next((c for c in t.task_comments if c.get('id') == c_id), None)
            if comment:
                comment['status'] = st.session_state[key]
                self.data_manager.sync_state()

        # 渲染“待解决问题”模块
        if problems:
            unsolved_count = len([p for p in problems if p.get('status', '未解决') == '未解决'])
            st.markdown(f"**待解决问题 ({unsolved_count})**")

            for p in sorted(problems, key=lambda c: c['time']):
                with st.container(border=True):
                    comment_id = p.get('id', str(p['time'].timestamp()))

                    # --- 布局优化 2：采用新的垂直+水平混合布局，确保空间 ---

                    # 1. 评论内容单独占一行，获得最大空间
                    st.markdown(p['content'])

                    # 2. 在下方创建新的一行来放置控件
                    footer_cols = st.columns([3, 2])

                    with footer_cols[0]:
                        # 时间戳放在左下角
                        st.caption(f"记录于: {p['time'].strftime('%Y-%m-%d %H:%M')}")

                    with footer_cols[1]:
                        # Selectbox放在右下角，获得充足的横向空间
                        options = ["未解决", "已解决"]
                        current_status = p.get('status', '未解决')

                        try:
                            current_index = options.index(current_status)
                        except ValueError:
                            current_index = 0

                        st.selectbox(
                            "状态", options=options, index=current_index,
                            key=f"status_select_{comment_id}_card",
                            on_change=on_status_change,
                            args=(task, comment_id, f"status_select_{comment_id}_card"),
                            label_visibility="collapsed"
                        )
                    # --- 布局优化结束 ---
            st.markdown("---")

        # 渲染“其他评论”模块
        if other_comments:
            st.markdown("**其他评论记录 (备注/心得)**")
            container_height = 150 if problems else 250
            with st.container(height=container_height):
                for c in reversed(other_comments):
                    icon = self.k_config.COMMENT_ICON_MAP.get(c['type'], "💬")
                    color = self.k_config.COMMENT_COLOR_MAP.get(c['type'], "gray")
                    with st.chat_message(name=c['type'], avatar=icon):
                        st.markdown(f":{color}[{c['content']}]")
                        st.caption(f"_{c['time'].strftime('%Y-%m-%d %H:%M')}_")

    def _render_task_management_popover(self, task, existing_types):
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
            if st.button(
                    self.k_config.T_CARD_DELETE_BUTTON,
                    key=f"delete_button_{task.task_id}",  # <--- 关键修复！
                    type="primary",
                    use_container_width=True,
                    help=self.k_config.T_CARD_DELETE_HELP
            ):
                st.session_state.tasks = [t for t in st.session_state.tasks if t.task_id != task.task_id]
                st.toast(self.k_config.T_SUCCESS_TASK_DELETED.format(task_name=task.task_name), icon="🗑️")
                self.data_manager.sync_state()
                st.rerun()

    def _render_daily_utilization_section(self, tasks):
        """渲染每日时间利用率分析模块（已增加KPI指标显示）。"""
        with st.container(border=True):
            st.subheader("📊 每日时间利用率分析", anchor=False)
            st.caption("通过自定义工作与非工作时间，分析你在不同时间段的专注度和产出效率。")

            time_options = [f"{h:02d}:00" for h in range(24)] + [f"{h:02d}:00 (次日)" for h in range(6)]
            col1, col2 = st.columns(2, gap="large")

            # --- 左侧：工作时间利用率 ---
            with col1:
                st.markdown("##### 🏢 工作时间")
                with st.expander("⚙️ 设置工作时间 (支持跨天)", expanded=False):
                    work_start_str, work_end_str = st.select_slider(
                        "选择工作时间范围",
                        options=time_options, value=("09:00", "17:00"), key="work_time_range"
                    )

                work_start = int(work_start_str.split(':')[0])
                work_end = int(work_end_str.split(':')[0])
                work_crosses_midnight = "(次日)" in work_end_str

                if not work_crosses_midnight and work_start >= work_end:
                    st.warning("工作开始时间必须早于结束时间。")
                else:
                    work_df = self._calculate_daily_utilization(tasks, work_start, work_end,
                                                                crosses_midnight=work_crosses_midnight)

                    # --- 新增：调用KPI显示函数 ---
                    self._display_utilization_kpis(work_df, prefix="工作")

                    if not work_df.empty:
                        fig = px.line(
                            work_df.head(30), x=work_df.head(30).index, y='window_utilization_pct',
                            title=f"工作时间利用率 ({work_start_str} - {work_end_str})",
                            labels={'x': '日期', 'window_utilization_pct': '利用率 (%)'}, markers=True
                        )
                        fig.update_layout(yaxis=dict(range=[0, 105]))
                        fig.update_xaxes(tickformat="%m月%d日", dtick="D1")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("在定义的工作时间内暂无工时记录。")

            # --- 右侧：非工作时间利用率 ---
            with col2:
                st.markdown("##### 🏡 非工作时间")
                with st.expander("⚙️ 设置非工作/学习时间 (支持跨天)", expanded=False):
                    free_start_str, free_end_str = st.select_slider(
                        "选择时间范围",
                        options=time_options, value=("18:00", "23:00"), key="free_time_range"
                    )

                free_start = int(free_start_str.split(':')[0])
                free_end = int(free_end_str.split(':')[0])
                free_crosses_midnight = "(次日)" in free_end_str

                if not free_crosses_midnight and free_start >= free_end:
                    st.warning("非工作开始时间必须早于结束时间。")
                else:
                    free_df = self._calculate_daily_utilization(tasks, free_start, free_end,
                                                                crosses_midnight=free_crosses_midnight)

                    # --- 新增：调用KPI显示函数 ---
                    self._display_utilization_kpis(free_df, prefix="非工作")

                    if not free_df.empty:
                        fig = px.line(
                            free_df.head(30), x=free_df.head(30).index, y='window_utilization_pct',
                            title=f"非工作时间利用率 ({free_start_str} - {free_end_str})",
                            labels={'x': '日期', 'window_utilization_pct': '利用率 (%)'},
                            markers=True, color_discrete_sequence=['#EF553B']
                        )
                        fig.update_layout(yaxis=dict(range=[0, 105]))
                        fig.update_xaxes(tickformat="%m月%d日", dtick="D1")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("在定义的非工作时间内暂无工时记录。")

    def _render_task_efficiency_section(self, df):
        """渲染单任务执行效率模块（已更新为多彩柱状图）。"""
        with st.container(border=True):
            st.subheader("🎯 单任务执行效率分析 (仅限已完成)", anchor=False)
            st.caption("效率越高，表示任务完成过程中的拖延时间越少。100% 表示任务从开始到结束一直在进行中。")

            efficiency_df = df.dropna(subset=['efficiency']).copy()
            if not efficiency_df.empty:
                efficiency_df['efficiency_pct'] = efficiency_df['efficiency'] * 100

                # 文字指标 (保持不变)
                avg_eff = efficiency_df['efficiency_pct'].mean()
                max_eff_row = efficiency_df.loc[efficiency_df['efficiency_pct'].idxmax()]
                min_eff_row = efficiency_df.loc[efficiency_df['efficiency_pct'].idxmin()]

                kpi_cols = st.columns(3)
                kpi_cols[0].metric("平均执行效率", f"{avg_eff:.1f}%")
                kpi_cols[1].metric("最高效率任务", f"{max_eff_row['efficiency_pct']:.1f}%",
                                   help=f"任务: {max_eff_row['task_name']}")
                kpi_cols[2].metric("最低效率任务", f"{min_eff_row['efficiency_pct']:.1f}%",
                                   help=f"任务: {min_eff_row['task_name']}")

                st.markdown("---")

                # --- 修改点：在 px.bar 中添加 color='task_name' ---
                fig_efficiency = px.bar(
                    efficiency_df.sort_values('efficiency', ascending=True),
                    x='efficiency_pct',
                    y='task_name',
                    orientation='h',
                    title='各任务执行效率对比',
                    labels={'task_name': '任务名称', 'efficiency_pct': '效率 (%)'},
                    text=efficiency_df['efficiency_pct'].apply(lambda x: f'{x:.1f}%'),
                    color='task_name'  # <-- 核心修改：根据任务名称分配不同颜色
                )

                # --- 优化点：隐藏多余的颜色图例 ---
                # 因为Y轴已经标注了任务名，所以颜色图例是多余的
                fig_efficiency.update_layout(showlegend=False)

                fig_efficiency.update_layout(xaxis=dict(range=[0, 105]))
                st.plotly_chart(fig_efficiency, use_container_width=True)
            else:
                st.info("暂无已完成且有计时记录的任务可供分析效率。")

    def _render_tasks_overview_section(self, df):
        """渲染整合后的任务总览模块。"""
        with st.container(border=True):
            st.subheader("🗂️ 任务总览", anchor=False)

            # 1. 核心指标
            total_tasks = len(df)
            completed_tasks = df[df['status'] == self.k_config.STATUS_DONE].shape[0]
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            avg_active_time_sec = df[df['status'] == self.k_config.STATUS_DONE]['total_active_time_seconds'].mean()
            avg_lifespan_sec = df[df['status'] == self.k_config.STATUS_DONE]['task_duration_seconds'].mean()

            kpi_cols = st.columns(4)
            kpi_cols[0].metric("总任务数", f"{total_tasks} 个")
            kpi_cols[1].metric("完成率", f"{completion_rate:.1f}%")
            kpi_cols[2].metric("平均活跃时长", format_timedelta_to_str(timedelta(seconds=avg_active_time_sec)) if pd.notna(
                avg_active_time_sec) else "N/A", help="仅计算已完成任务")
            kpi_cols[3].metric("平均生命周期", format_timedelta_to_str(timedelta(seconds=avg_lifespan_sec)) if pd.notna(
                avg_lifespan_sec) else "N/A", help="仅计算已完成任务")

            st.markdown("---")

            # 2. 任务分布
            dist_col1, dist_col2 = st.columns(2)
            with dist_col1:
                status_counts = df['status'].value_counts()
                fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="按状态分布",
                             hole=0.3)
                st.plotly_chart(fig, use_container_width=True)
            with dist_col2:
                type_counts = df['task_type'].value_counts()
                fig = px.pie(type_counts, values=type_counts.values, names=type_counts.index, title="按类型分布", hole=0.3)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # 3. 任务趋势与耗时（左右布局）
            trend_col1, trend_col2 = st.columns(2)
            with trend_col1:
                st.markdown("##### 任务创建趋势")
                df_creation = df.copy()
                if df_creation['creation_time'].dt.tz is None:
                    df_creation['creation_time'] = df_creation['creation_time'].dt.tz_localize('UTC').dt.tz_convert(
                        beijing_tz)
                df_creation['creation_date'] = df_creation['creation_time'].dt.date
                tasks_per_day = df_creation.groupby('creation_date').size().reset_index(name='count')

                fig_trend = px.bar(
                    tasks_per_day, x='creation_date', y='count',
                    labels={'creation_date': '日期', 'count': '任务数量'},
                    color='creation_date',  # 按日期赋予不同颜色
                    color_continuous_scale=px.colors.sequential.Viridis  # 使用一个好看的连续色阶
                )
                fig_trend.update_layout(coloraxis_showscale=False)  # 隐藏颜色图例
                fig_trend.update_xaxes(tickformat="%m月%d日", dtick="D1")
                st.plotly_chart(fig_trend, use_container_width=True)

            with trend_col2:
                st.markdown("##### 任务耗时分析 (仅限已完成)")
                df_timing = df.copy()
                df_timing['total_active_time_hours'] = df_timing['total_active_time_seconds'] / 3600
                df_timing['task_duration_hours'] = df_timing['task_duration_seconds'] / 3600
                completed_df = df_timing[df_timing['status'] == self.k_config.STATUS_DONE].copy()

                if not completed_df.empty:
                    avg_time_by_type = completed_df.groupby('task_type')[
                        ['total_active_time_hours', 'task_duration_hours']].mean().reset_index()
                    avg_time_by_type = avg_time_by_type.rename(
                        columns={'total_active_time_hours': '平均活跃时长 (小时)', 'task_duration_hours': '平均生命周期 (小时)'})

                    fig_avg_time = px.bar(
                        avg_time_by_type, x='task_type', y=['平均活跃时长 (小时)', '平均生命周期 (小时)'],
                        barmode='group',
                        color_discrete_map={  # 自定义颜色
                            '平均活跃时长 (小时)': '#636EFA',
                            '平均生命周期 (小时)': '#FFA15A'
                        },
                        labels={'task_type': '任务类型', 'value': '平均小时数', 'variable': '指标'}
                    )
                    st.plotly_chart(fig_avg_time, use_container_width=True)
                else:
                    st.info("暂无已完成的任务可供分析。")

    # --- 公共渲染函数 ---

    def render_task_card(self, task, existing_types):
        """渲染单个任务卡片的所有内容。"""
        with st.expander(f"`{task.task_type}` {task.task_name}", expanded=False):
            st.subheader(task.task_name, divider="rainbow")
            self._render_task_metrics(task)
            self._render_task_controls(task)
            self._render_task_progress_slider(task)
            self._render_task_time_logs(task)
            self._render_task_comments_section(task)
            self._render_task_management_popover(task, existing_types)

    def render_kanban_layout(self, existing_types):
        """渲染看板的三列布局（未开始、进行中、已完成）。"""
        tasks = st.session_state.get('tasks', [])
        sorted_tasks = sorted(tasks, key=lambda x: x.creation_time, reverse=True)
        tasks_todo = [t for t in sorted_tasks if t.status == self.k_config.STATUS_TODO]
        tasks_doing = [t for t in sorted_tasks if t.status == self.k_config.STATUS_DOING]
        tasks_done = [t for t in sorted_tasks if t.status == self.k_config.STATUS_DONE]

        col1, col2, col3 = st.columns(3, gap="large")
        with col1:
            st.header(f"{self.k_config.T_COLUMN_TODO_HEADER} ({len(tasks_todo)})", divider="rainbow")
            for task in tasks_todo: self.render_task_card(task, existing_types)
        with col2:
            st.header(f"{self.k_config.T_COLUMN_DOING_HEADER} ({len(tasks_doing)})", divider="rainbow")
            for task in tasks_doing: self.render_task_card(task, existing_types)
        with col3:
            st.header(f"{self.k_config.T_COLUMN_DONE_HEADER} ({len(tasks_done)})", divider="rainbow")
            for task in tasks_done: self.render_task_card(task, existing_types)

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

    def render_main_controls(self, existing_types):
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

    def render_statistics_tab(self):
        """
        渲染统计分析标签页。（主函数，负责调度各个渲染模块）
        """
        st.header("任务统计分析", divider="rainbow")
        tasks = st.session_state.get('tasks', [])
        if not tasks:
            st.info("看板上还没有任务，快去创建一个吧！")
            return

        # 1. 统一准备数据
        main_df = pd.DataFrame([
            {
                "task_name": t.task_name, "creation_time": t.creation_time,
                "completion_time": t.completion_time, "status": t.status,
                "task_type": t.task_type,
                "total_active_time_seconds": t.get_total_active_duration().total_seconds(),
                "task_duration_seconds": t.task_duration.total_seconds() if t.task_duration else None,
                "efficiency": t.get_doing_efficiency()
            }
            for t in tasks
        ])

        # 2. 按新的布局顺序渲染各个分析模块
        self._render_daily_utilization_section(tasks)
        self._render_task_efficiency_section(main_df)
        self._render_tasks_overview_section(main_df)  # 调用新的整合模块

    def render_timeline_tab(self):
        """渲染日历/时间线视图标签页（已升级为多日期范围选择）。"""
        st.header("任务时间线视图 📅", divider="rainbow")

        # 1. 升级为日期范围选择器
        today = datetime.now(beijing_tz).date()
        selected_range = st.date_input(
            "请选择要查看的日期范围",
            value=(today, today),  # 传入一个元组来创建范围选择器
            help="选择一个开始和结束日期来查看该时间段内的任务活动。"
        )

        # 处理用户可能只选择一个日期的情况
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_date, end_date = selected_range
        elif isinstance(selected_range, list) and len(selected_range) == 2:
            start_date, end_date = selected_range
        else:  # 如果只选择了一天，streamlit有时会返回一个元素的列表
            start_date = end_date = selected_range[0] if isinstance(selected_range, list) else today

        if start_date > end_date:
            st.warning("开始日期不能晚于结束日期。")
            return

        st.markdown("---")

        tasks = st.session_state.get('tasks', [])
        timeline_data = []
        for task in tasks:
            for segment in task.active_time_segments:
                timeline_data.append({
                    "Task": task.task_name,
                    "Start": segment['start_time'],
                    "Finish": segment['end_time'],
                    "Type": task.task_type
                })
            if task.status == self.k_config.STATUS_DOING and task.last_start_active_time:
                timeline_data.append({
                    "Task": task.task_name,
                    "Start": task.last_start_active_time,
                    "Finish": datetime.now(beijing_tz),
                    "Type": "进行中"
                })

        if not timeline_data:
            st.info("没有任务活动记录，请先开始并完成一些任务以生成时间线。")
            return

        df = pd.DataFrame(timeline_data)
        df['Start'] = pd.to_datetime(df['Start']).dt.tz_convert(beijing_tz)
        df['Finish'] = pd.to_datetime(df['Finish']).dt.tz_convert(beijing_tz)

        # 2. 根据新的日期范围来定义过滤边界
        range_start = datetime.combine(start_date, datetime.min.time(), tzinfo=beijing_tz)
        # 结束边界应该是结束日期的最后一刻，即下一天的开始
        range_end = datetime.combine(end_date, datetime.min.time(), tzinfo=beijing_tz) + timedelta(days=1)

        filtered_df = df[(df['Start'] < range_end) & (df['Finish'] > range_start)].copy()

        # 裁剪任务条，使其不超过视图范围
        filtered_df['Clipped_Start'] = filtered_df['Start'].clip(lower=range_start)
        filtered_df['Clipped_Finish'] = filtered_df['Finish'].clip(upper=range_end)

        if filtered_df.empty:
            st.info(f"在 **{start_date}** 到 **{end_date}** 期间没有找到任何任务活动记录。")
            return

        # 3. 创建甘特图
        title = f"任务活动甘特图 ({start_date.strftime('%Y年%m月%d日')})"
        if start_date != end_date:
            title += f" 至 ({end_date.strftime('%Y年%m月%d日')})"

        fig = px.timeline(
            filtered_df,
            x_start="Clipped_Start",
            x_end="Clipped_Finish",
            y="Task",
            color="Type",
            title=title
        )
        fig.update_yaxes(categoryorder='total ascending')

        # 4. 循环为范围内的每一天添加标记线
        current_date = start_date
        while current_date <= end_date:
            day_marker = datetime.combine(current_date, datetime.min.time(), tzinfo=beijing_tz)

            # 添加每日的分割线（第一天的0点线除外，因为它就是图表起点）
            if current_date != start_date:
                fig.add_vline(x=day_marker, line_width=1.5, line_color="black")

            # 添加每日的中午12点虚线
            noon_marker = day_marker.replace(hour=12)
            fig.add_vline(x=noon_marker, line_width=1, line_dash="dash", line_color="grey")

            current_date += timedelta(days=1)

        # 5. 强制设定X轴的范围为所选的完整日期范围
        fig.update_layout(xaxis_range=[range_start, range_end])
        fig.update_xaxes(tickformat="%m月%d日<br>%H:%M")

        st.plotly_chart(fig, use_container_width=True)

    def render_comments_tab(self):
        """渲染评论知识库标签页（显示逻辑已加固）。"""
        st.header("💬 问题跟踪与知识库", divider="rainbow")
        tasks_with_comments = [task for task in st.session_state.get('tasks', []) if task.task_comments]

        if not tasks_with_comments:
            st.info("目前还没有任何任务有评论记录。")
            return

        all_comments = [cmt for task in tasks_with_comments for cmt in task.task_comments]

        st.subheader("关键指标", anchor=False)
        total_problems = len([c for c in all_comments if c['type'] == '问题'])
        unsolved_problems = len([c for c in all_comments if c.get('status') == '未解决'])
        total_insights = len([c for c in all_comments if c['type'] == '心得'])
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("待解决问题", f"{unsolved_problems} 个")
        kpi_cols[1].metric("问题总数", f"{total_problems} 个")
        kpi_cols[2].metric("心得总数", f"{total_insights} 条")
        st.markdown("---")

        st.subheader("筛选与搜索", anchor=False)
        all_comment_types = sorted(list(set(c['type'] for c in all_comments)))
        task_names = sorted(list(set(t.task_name for t in tasks_with_comments)))
        filter_cols = st.columns([2, 2, 1, 1])
        search_query = filter_cols[0].text_input("全文搜索评论内容", placeholder="输入关键词...")
        selected_tasks = filter_cols[1].multiselect("按任务筛选", options=task_names)
        selected_types = filter_cols[2].multiselect("按类型筛选", options=all_comment_types)
        selected_status = filter_cols[3].selectbox("按问题状态筛选", options=["全部", "未解决", "已解决"], index=1)
        st.markdown("---")

        filtered_tasks = []
        for task in tasks_with_comments:
            comments_to_display = list(task.task_comments)
            if selected_tasks and task.task_name not in selected_tasks: continue
            if search_query: comments_to_display = [c for c in comments_to_display if
                                                    search_query.lower() in c['content'].lower()]
            if selected_types: comments_to_display = [c for c in comments_to_display if c['type'] in selected_types]
            # 替换后的代码
            if selected_status != "全部":
                # 核心修正：只保留那些类型是“问题”并且状态匹配的评论
                comments_to_display = [c for c in comments_to_display if
                                       c['type'] == '问题' and c.get('status') == selected_status]
            if comments_to_display: filtered_tasks.append({'task': task, 'comments': comments_to_display})

        if not filtered_tasks:
            st.warning("根据您的筛选条件，没有找到匹配的评论。")
            return

        st.subheader(f"找到 {len(filtered_tasks)} 个相关任务", anchor=False)
        for item in filtered_tasks:
            task = item['task']
            comments = sorted(item['comments'], key=lambda c: c['time'])
            with st.expander(f"**{task.task_name}** (`{task.task_type}`) - 包含 {len(comments)} 条相关评论"):
                for c in comments:
                    icon = self.k_config.COMMENT_ICON_MAP.get(c['type'], "💬")
                    with st.container(border=True):
                        header_cols = st.columns([1, 6])
                        header_cols[0].markdown(f"##### {icon} {c['type']}")
                        if c['type'] == '问题':
                            # --- 核心修复点：确保 status 永远不会是 None ---
                            # 如果 c.get('status') 返回 None 或任何非 "已解决" 的值，都视为 "未解决"
                            status = "已解决" if c.get('status') == "已解决" else "未解决"

                            color = "red" if status == "未解决" else "green"
                            header_cols[1].markdown(f"状态: :{color}[**{status}**]")

                        st.markdown(c['content'])
                        footer_cols = st.columns([3, 1])
                        footer_cols[0].caption(f"记录于: {c['time'].strftime('%Y-%m-%d %H:%M')}")

                        if c['type'] == '问题':
                            comment_id = c.get('id', str(c['time'].timestamp()))
                            if c.get('status') == '未解决':
                                if footer_cols[1].button("✅ 标记为已解决", key=f"solve_{comment_id}",
                                                         use_container_width=True):
                                    c['status'] = '已解决'
                                    self.data_manager.sync_state()
                                    st.rerun()
                            elif c.get('status') == '已解决':
                                if footer_cols[1].button("🔄 重新打开", key=f"reopen_{comment_id}", type="secondary",
                                                         use_container_width=True):
                                    c['status'] = '未解决'
                                    self.data_manager.sync_state()
                                    st.rerun()


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

    # --- 优化点：在这里一次性计算好所有已存在的任务类型 ---
    tasks_for_types_calc = st.session_state.get('tasks', [])
    existing_task_types = sorted(list(set(t.task_type for t in tasks_for_types_calc)))
    # --- 优化结束 ---

    # 4. 创建并渲染标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📌 任务看板",  "📅 日历视图", "📊 统计分析","💬 评论知识库"])

    with tab1:
        ui.render_main_controls(existing_task_types)
        ui.render_kanban_layout(existing_task_types)
    with tab2:
        ui.render_timeline_tab()
    with tab3:
        ui.render_statistics_tab()
    with tab4:
        ui.render_comments_tab()


if __name__ == "__main__":
    main()