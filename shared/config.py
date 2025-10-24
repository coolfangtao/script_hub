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
        # 添加数据文件路径
        self.USAGE_DATA_FILE = "script_usage_data.json"


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