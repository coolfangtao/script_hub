# 文件路径: shared/usage_tracker.py

import streamlit as st
import datetime
from shared.config import GlobalConfig
from shared.github_handler import get_private_data_handler  # <-- 导入新的处理函数


# --- 公共接口函数 ---

@st.cache_data(ttl=600)  # 缓存10分钟
def get_usage_stats():
    """
    (公共)
    获取用于在主页上显示的脚本使用统计数据。
    """
    # 1. 获取缓存的 handler 实例
    handler = get_private_data_handler()
    if not handler or not handler.is_ready():
        st.warning("GitHub私有仓库连接失败，无法获取统计数据。")
        return {}

    # 2. 从 GlobalConfig 获取文件名
    config = GlobalConfig()

    # 3. 使用 handler 读取文件
    data, _ = handler.read_json_file(config.USAGE_DATA_FILE)

    return data if data else {}


def track_page_visit(script_label):
    """
    (公共)
    跟踪一次页面访问。
    使用session_state防止在同一会话的单个页面刷新时重复计数。
    """
    session_key = f"page_tracked_{script_label}"

    # 1. 检查是否在当前会话中已经跟踪过此页面
    if st.session_state.get(session_key, False):
        return  # 已经跟踪过，直接返回

    # 2. 获取 handler 和 config
    handler = get_private_data_handler()
    if not handler or not handler.is_ready():
        # 不显示错误，以免打扰用户，但在需要时可以取消注释
        # st.error("GitHub handler not ready. Cannot track visit.")
        return

    config = GlobalConfig()
    file_path = config.USAGE_DATA_FILE

    # 3. 获取最新数据（不使用缓存，因为我们需要最新的SHA）
    data, sha = handler.read_json_file(file_path)
    if data is None:
        data = {}  # 文件不存在，初始化为空字典

    # 4. 更新数据
    timestamp = datetime.datetime.now(config.APP_TIMEZONE).isoformat()

    if script_label not in data:
        data[script_label] = {"count": 0}

    data[script_label]["count"] = data[script_label].get("count", 0) + 1
    data[script_label]["last_visited"] = timestamp

    # 5. 写回GitHub
    commit_prefix = f"[UsageTrack] 访问: {script_label}"
    success = handler.write_json_file(file_path, data, commit_prefix, sha)

    if success:
        # 6. 在会话中标记此页面为已跟踪
        st.session_state[session_key] = True
        # 7. 清除 get_usage_stats 的缓存，以便主页能立即显示最新数据
        st.cache_data.clear()