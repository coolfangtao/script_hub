import streamlit as st
import google.generativeai as genai
from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar
from shared.config import GlobalConfig


cfg = GlobalConfig()


# --- 1. 配置和初始化 ---

def setup_page_and_sidebar():
    """配置页面和侧边栏"""
    st.set_page_config(
        page_title="AI 对话",
        page_icon="🤖",
        layout="wide"
    )
    # 注意：侧边栏仍然会创建，但API输入框不会出现在那里
    # track_script_usage("💬 AI对话")
    create_common_sidebar()


# --- 核心优化部分：API配置 ---
def configure_api(run_mode):
    """
    根据运行模式 (local/cloud) 配置 Google Gemini API.
    - local: 从 st.secrets 读取密钥.
    - cloud: 在主页上要求用户输入密钥.
    """
    if st.session_state.get("api_key_configured", False):
        return True

    api_key = None
    if run_mode == 'local':
        st.sidebar.info("🚀 运行模式: 本地")
        try:
            api_key = st.secrets[cfg.GEMINI_API_KEY]
            st.sidebar.success("✅ API 密钥已从本地配置加载。")
        except KeyError:
            st.error("本地模式下未找到 API 密钥。请在 Streamlit Cloud 的 Secrets 中设置 `GEMINI_API_KEY`。")
            return False

    elif run_mode == 'cloud':
        # --- UI修改的核心：将输入框放在主页上 ---
        with st.container(border=True):
            st.subheader("欢迎使用 AI 对话 ☁️")
            st.info("这是一个云端部署版本，请输入您的 Google Gemini API 密钥以继续。")
            api_key = st.text_input(
                "Google Gemini API 密钥",
                type="password",
                key="api_key_input",  # 使用独立的key
                placeholder="在此输入您的 API 密钥..."
            )
            st.markdown("[如何获取 API 密钥？](https://aistudio.google.com/app/apikey)", unsafe_allow_html=True)

        if not api_key:
            return False  # 如果没有输入，则阻塞后续UI加载

    else:
        st.error(f"❌ 未知的运行模式: '{run_mode}'")
        return False

    # --- 通用的配置逻辑 ---
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.session_state.api_key_configured = True
            # 当云端模式首次配置成功后，立即重新运行以隐藏输入框
            if run_mode == 'cloud':
                st.rerun()
            return True
        except Exception as e:
            # 如果配置失败，在输入框下方显示错误
            st.error(f"API 密钥配置失败: {e}", icon="🚨")
            st.session_state.api_key_configured = False
            return False

    return False


def initialize_session_state():
    """初始化或检查会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None
    if "api_key_configured" not in st.session_state:
        st.session_state.api_key_configured = False


def clear_chat_history():
    """清除所有聊天记录"""
    st.session_state.messages = []


# --- 2. 核心逻辑处理器 ---

def stream_handler(stream):
    """处理API返回的流式数据，仅提取文本部分"""
    for chunk in stream:
        if hasattr(chunk, 'text'):
            yield chunk.text


# --- 3. 主应用界面 ---

def main():
    """主应用函数"""
    setup_page_and_sidebar()
    initialize_session_state()

    st.title("🤖 AI 对话")

    # --- API 配置检查 ---
    # 如果配置未完成 (例如，在云端模式下等待用户输入)，
    # configure_api 会显示输入框并返回 False, st.stop()会阻止下面的代码运行。
    if not configure_api(cfg.RUN_MODE):
        st.stop()

    # --- 只有在API配置成功后，才会显示以下内容 ---
    st.caption("一个由 Google Gemini 驱动的聊天机器人")

    MODEL_OPTIONS = cfg.GEMINI_MODEL_OPTIONS

    col1, col_spacer, col2 = st.columns([2, 5, 2])
    with col1:
        def on_model_change():
            if st.session_state.selected_model != st.session_state.model_selector:
                clear_chat_history()
                st.toast("模型已切换，新的对话开始啦！", icon="🔄")

        selected_model = st.selectbox(
            "选择 AI 模型:",
            options=MODEL_OPTIONS,
            key="model_selector",
            on_change=on_model_change,
            help="切换模型会自动开始新的对话。"
        )
        st.session_state.selected_model = selected_model
    with col2:
        st.write("")
        if st.button("清除当前对话", use_container_width=True):
            clear_chat_history()
            st.toast("对话已清除！", icon="🧹")
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("您好，有什么可以帮助您的吗？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            with st.chat_message("assistant"):
                with st.spinner("AI 正在思考中..."):
                    model = genai.GenerativeModel(selected_model)
                    gemini_history = [
                        {"role": "model" if msg["role"] == "assistant" else "user", "parts": [msg["content"]]}
                        for msg in st.session_state.messages[:-1]
                    ]
                    chat = model.start_chat(history=gemini_history)
                    response_stream = chat.send_message(prompt, stream=True)
                    full_response = st.write_stream(stream_handler(response_stream))
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"调用 API 时出错: {e}")
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()


# --- 4. 运行主程序 ---
if __name__ == "__main__":
    main()