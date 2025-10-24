# shared/config.py
import streamlit as st
from datetime import timezone, timedelta
import yaml
from pathlib import Path
import os

# <<< 运行模式检测函数 >>>
def get_run_mode():
    """
    直接从 secrets 读取运行环境配置。
    默认为 'cloud'，以保证部署到云端时的安全性（不会尝试写本地文件）。
    """
    return st.secrets.get("RUN_ENVIRONMENT", "cloud")


class GlobalConfig:
    """存储所有页面共享的全局配置，例如密钥、API等。"""

    def __init__(self):
        # --- 运行模式 ---
        self.RUN_MODE = get_run_mode()  # "local" or "cloud"

        # --- 本地文件路径配置 (仅在 local 模式下有意义) ---
        self.LOCAL_DATA_FILE_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'local_tasks_data.json')
        )

        self.IMAGE_PATH_IN_REPO = st.secrets.get("IMAGE_PATH_IN_REPO", "images")


        # 从 Streamlit secrets 加载密钥
        self.GITHUB_TOKEN = st.secrets.get("github_data_token")
        self.GITHUB_PRIVATE_REPO = st.secrets.get("github_data_repo")
        self.GITHUB_PUBLIC_REPO = st.secrets.get("github_data_public_repo")

        self.GEMINI_API_KEY = "gemini_api_key"

        # 可用的AI模型
        self.GEMINI_MODEL_OPTIONS = [
            "gemini-2.5-flash-lite",  # 默认模型，可用，2.15秒
            "gemini-2.0-flash",  # 可用，5.11秒
            "gemini-2.5-pro",   # 可用，14.93秒
            "gemini-2.0-flash-exp",  # 可用，4.28秒
            "gemini-2.0-flash-lite",  # 可用，9.62秒
            "gemini-2.5-flash",  # 可用，6.74秒
            "gemini-robotics-er-1.5-preview",  # 可用，8.73秒
        ]

        # 定义时区
        self.APP_TIMEZONE = timezone(timedelta(hours=8))  # 北京时间 (UTC+8)


class KanbanPageConfig:
    """存储任务看板页面专属的配置和UI文本。"""

    def __init__(self):
        # --- 核心配置 ---
        self.DATA_FILE_NAME = "tasks_data.json"
        self.AUTO_REFRESH_INTERVAL_MS = 1000 * 60  # 自动刷新间隔（毫秒）

        # --- 页面基础设置 ---
        self.PAGE_TITLE = "每日任务看板"
        self.PAGE_ICON = "📋"

        # --- 任务状态常量 ---
        self.STATUS_TODO = "未开始"
        self.STATUS_DOING = "进行中"
        self.STATUS_DONE = "已完成"

        # --- 任务标签/类型 ---
        self.TASK_TYPES = ["主线任务", "副线任务"]

        # --- 评论区配置 ---
        self.COMMENT_TYPES = ["备注", "问题", "心得"]
        self.COMMENT_ICON_MAP = {"心得": "💡", "问题": "❓", "备注": "📌"}
        self.COMMENT_COLOR_MAP = {"心得": "green", "问题": "red", "备注": "blue"}

        # --- UI 文本 (可用于未来国际化) ---
        self.T_MAIN_TITLE = f"{self.PAGE_ICON} {self.PAGE_TITLE}"
        self.T_CONTROL_PANEL_HEADER = "控制面板"

        self.UI_CONTROL_PANEL_HEIGHT = 360  # 控制面板容器的固定高度（像素）

        # 控制区：创建任务
        self.T_CREATE_TASK_HEADER = "🚀 创建新任务"
        self.T_TASK_NAME_LABEL = "任务名称"
        self.T_TASK_NAME_PLACEHOLDER = "例如：完成项目报告"
        self.T_TASK_TYPE_LABEL = "任务标签"
        self.T_ADD_TASK_BUTTON = "添加任务"
        self.T_WARN_EMPTY_TASK_NAME = "任务名称不能为空！"
        self.T_SUCCESS_TASK_ADDED = "任务 '{task_name}' 已添加！"

        # 控制区：导入导出
        self.T_LOCAL_IO_HEADER = "📥 本地导入/导出"
        self.T_UPLOAD_LABEL = "选择一个 .json 任务文件"
        self.T_UPLOAD_HELP = "从本地文件恢复任务。"
        self.T_DOWNLOAD_BUTTON = "📥 下载任务到本地"
        self.T_DOWNLOAD_HELP = "将当前看板上的所有任务保存为一个 JSON 文件。"
        self.T_EXPORT_FILE_PREFIX = "tasks_export_"

        # 控制区：GitHub同步
        self.T_GITHUB_SYNC_HEADER = "☁️ GitHub 云同步"
        self.T_GITHUB_SYNC_CAPTION = "数据在每次更改后会自动同步。这里提供手动操作以备不时之需。"
        self.T_GITHUB_PUSH_BUTTON = "⬆️ 推送到 GitHub"
        self.T_GITHUB_PUSH_HELP = "将当前看板数据保存到云端。"
        self.T_GITHUB_PULL_BUTTON = "⬇️ 从 GitHub 拉取"
        self.T_GITHUB_PULL_HELP = "从云端获取最新数据，会覆盖当前看板！"
        self.T_GITHUB_SYNC_INFO = "数据同步基于你的 `secrets.toml` 配置文件。"

        # 看板列标题
        self.T_COLUMN_TODO_HEADER = f"📥 {self.STATUS_TODO}/挂起"
        self.T_COLUMN_DOING_HEADER = f"💻 {self.STATUS_DOING}"
        self.T_COLUMN_DONE_HEADER = f"✅ {self.STATUS_DONE}"

        # 任务卡片UI文本
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

        # 任务控制按钮
        self.T_BUTTON_START = "▶️ 开始"
        self.T_BUTTON_PAUSE = "⏸️ 挂起"
        self.T_BUTTON_PAUSE_HELP = "将任务移回“未开始”并暂停计时，不改变当前进度。"
        self.T_BUTTON_DONE = "✅ 完成"
        self.T_BUTTON_REOPEN = "🔄 重新打开"

        # 评论区
        self.T_POPOVER_CREATE_COMMENT = "💬 创建评论"
        self.T_COMMENT_TYPE_LABEL = "评论类型"
        self.T_COMMENT_CONTENT_LABEL = "评论内容..."
        self.T_COMMENT_SUBMIT_BUTTON = "提交"
        self.T_WARN_EMPTY_COMMENT = "评论内容不能为空"

        # 系统消息与提示
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
    """
    创建一个全局唯一的配置实例，整合所有配置类。
    """
    def __init__(self):
        self.globals = GlobalConfig()
        self.kanban = KanbanPageConfig()