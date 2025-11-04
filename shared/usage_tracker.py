# 文件路径: shared/usage_tracker.py

import streamlit as st
import datetime
from shared.config import GlobalConfig
from shared.github_handler import get_private_data_handler
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx


def _get_client_ip() -> str:
    """
    (已修复 v2)
    使用Streamlit的内部API获取客户端IP地址。

    优先检查 X-Forwarded-For Header，这对于部署在
    Streamlit Cloud 或其他反向代理后面的应用至关重要。
    """
    try:
        ctx = get_script_run_ctx()
        if ctx is None:
            return "Unknown (ctx is None)"

        session_info = runtime.get_instance().get_client(ctx.session_id)
        if session_info is None:
            return "Unknown (session_info is None)"

        if session_info.request is None:
            return "Unknown (request is None)"

        # --- 关键修复 ---
        # 1. 检查 X-Forwarded-For (用于部署环境)
        headers = session_info.request.headers
        forwarded_for = headers.get("X-Forwarded-For")
        if forwarded_for:
            # "X-Forwarded-For" 可能是 "client_ip, proxy1_ip, proxy2_ip"
            # 我们只取第一个 (真正的客户端)
            return forwarded_for.split(",")[0].strip()

        # 2. 回退到 remote_ip (用于本地开发)
        return session_info.request.remote_ip or "Unknown"

    except Exception as e:
        return f"Error: {e}"


# --- (get_usage_stats 保持不变) ---
@st.cache_data(ttl=600)
def get_usage_stats():
    """
    (公共)
    获取用于在主页上显示的脚本使用统计数据。
    """
    handler = get_private_data_handler()
    if not handler or not handler.is_ready():
        st.warning("GitHub私有仓库连接失败，无法获取统计数据。")
        return {}

    config = GlobalConfig()
    data, _ = handler.read_json_file(config.USAGE_DATA_FILE)

    return data if data else {}


# --- 新的内部辅助函数 ---
def _record_visit_to_github(script_label):
    """
    (内部函数)
    负责实际的GitHub读写操作，记录一次访问。
    返回 True/False 表示成功或失败。
    """

    # 1. 检查会话锁，防止重复记录 (例如, 主页和子页面在1秒内同时触发)
    session_key = f"page_tracked_{script_label}"
    if st.session_state.get(session_key, False):
        return True  # 已经记录过了

    ip_address = _get_client_ip()

    # 2. 获取 handler 和 config
    handler = get_private_data_handler()
    if not handler or not handler.is_ready():
        return False

    config = GlobalConfig()
    file_path = config.USAGE_DATA_FILE

    # 3. 获取最新数据
    data, sha = handler.read_json_file(file_path)
    if data is None:
        data = {}

        # 4. 更新数据
    timestamp = datetime.datetime.now(config.APP_TIMEZONE).isoformat()

    if script_label not in data:
        data[script_label] = {"count": 0, "visits": []}
    if "visits" not in data[script_label]:
        data[script_label]["visits"] = []

    visit_data = {
        "time": timestamp
        # "ip": ip_address
    }
    data[script_label]["visits"].append(visit_data)
    data[script_label]["count"] = data[script_label].get("count", 0) + 1
    data[script_label]["visits"].append(timestamp)
    data[script_label]["last_visited"] = timestamp

    # 5. 写回GitHub
    commit_prefix = f"[UsageTrack] 访问: {script_label}"
    success = handler.write_json_file(file_path, data, commit_prefix, sha)

    if success:
        # 6. 在会话中标记此页面为已跟踪
        st.session_state[session_key] = True
        # 7. 清除 get_usage_stats 的缓存
        st.cache_data.clear()

    return success


# --- 更新后的 track_page_visit (新逻辑) ---

def track_page_visit(script_label):
    """
    (已更新 v3 - 延迟跟踪)
    跟踪一次子页面访问，并智能处理待办的主页访问。
    """

    # 1. (新) 处理待办的主页访问
    if st.session_state.get("pending_home_visit", False):
        # 这是一个真实用户！我们补录一次主页访问
        home_success = _record_visit_to_github("🏠 主页")

        if home_success:
            # 清除标记，防止重复补录
            st.session_state["pending_home_visit"] = False
            # st.toast("'🏠 主页' (真实访问) 记录成功!", icon="🏠")

    # 2. (旧) 记录当前子页面的访问
    page_success = _record_visit_to_github(script_label)

    if page_success:
        # st.toast(f"'{script_label}' 记录成功!", icon="✅")
        pass
    else:
        st.toast(f"记录 '{script_label}' 失败。", icon="❌")