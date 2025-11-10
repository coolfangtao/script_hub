# shared/config.py
import streamlit as st
from datetime import timezone, timedelta


class GlobalConfig:
    """存储所有页面共享的全局配置，例如密钥、API等。"""

    def __init__(self):
        # --- 运行模式 ---
        self.RUN_MODE = st.secrets.get("RUN_ENVIRONMENT", "cloud")  # "local" or "cloud"
        # 云端模式下用于验证身份的密码
        self.APP_PASSWORD = st.secrets.get("app_password")

        self.GITHUB_TOKEN = st.secrets.get("github_data_token")  # github token
        self.GITHUB_PRIVATE_REPO = st.secrets.get("github_data_repo")  # 私人数据库路径
        self.GITHUB_PUBLIC_REPO = st.secrets.get("github_data_public_repo")  # 公共数据库路径

        self.USAGE_DATA_FILE = "script_usage_data.json"  # 用户使用次数统计，存放在私人数据库（已决定废弃）
        self.IMAGE_PATH_IN_REPO = st.secrets.get("IMAGE_PATH_IN_REPO", "images")  # 公共图床服务专用

        # Turso数据库配置(用于存放绝大部分streamlit的数据)
        self.STREAMLIT_TURSO_DB = st.secrets.get("streamlit_turso_db")
        self.STREAMLIT_TURSO_TOKEN = st.secrets.get("streamlit_turso_token")

        # AI秘钥
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
            # "gemini-2.0-flash-preview-image-generation",
            # "gemini-2.5-flash-image"
        ]

        # 定义时区 北京时间 (UTC+8)
        self.APP_TIMEZONE = timezone(timedelta(hours=8))

# 创建全局配置实例
@st.cache_resource
def get_global_config():
    """获取全局配置的缓存实例"""
    return GlobalConfig()