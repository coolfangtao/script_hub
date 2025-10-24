import streamlit as st
import google.generativeai as genai
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
    create_common_sidebar()


# --- 新增：核心优化部分 ---
def configure_api(run_mode):
    """
    根据运行模式 (local/cloud) 配置 Google Gemini API.
    - local: 从 st.secrets 读取密钥.
    - cloud: 要求用户在侧边栏输入密钥.
    """
    # 如果已配置成功，则直接返回 True，避免重复配置
    if st.session_state.get("api_key_configured", False):
        return True

    api_key = None
    if run_mode == 'local':
        st.sidebar.info("🚀 运行模式: 本地")
        try:
            api_key = st.secrets[cfg.GEMINI_API_KEY]
            st.sidebar.success("✅ API 密钥已从本地配置加载。")
        except Exception as e:
            st.error(f"本地模式下无法加载 API 密钥: {e}")
            return False
    elif run_mode == 'cloud':
        st.sidebar.info("☁️ 运行模式: 云端")
        api_key = st.sidebar.text_input(
            "请输入您的 Google Gemini API 密钥",
            type="password",
            help="您可以从 Google AI Studio 获取您的密钥。"
        )
        if not api_key:
            st.info("请输入您的 API 密钥以启动聊天机器人。")
            return False
    else:
        st.error(f"❌ 未知的运行模式: '{run_mode}'")
        return False

    # 使用获取到的密钥进行配置
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.session_state.api_key_configured = True  # 标记为配置成功
            if run_mode == 'cloud':
                st.sidebar.success("✅ API 密钥配置成功！")
            return True
        except Exception as e:
            st.error(f"API 密钥配置失败: {e}")
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
    st.caption("一个由 Google Gemini 驱动的聊天机器人")

    # --- 修改点：根据 cfg.RUN_MODE 调用配置函数 ---
    if not configure_api(cfg.RUN_MODE):
        st.stop()

    MODEL_OPTIONS = cfg.GEMINI_MODEL_OPTIONS

    # --- 顶部布局：左侧模型选择，右侧清除按钮 ---
    col1, col_spacer, col2 = st.columns([2, 5, 2])

    with col1:
        def on_model_change():
            if st.session_state.selected_model != st.session_state.model_selector:
                clear_chat_history()
                st.toast(f"模型已切换，新的对话开始啦！", icon="🔄")

        selected_model = st.selectbox(
            "选择 AI 模型:",
            options=MODEL_OPTIONS,
            key="model_selector",
            on_change=on_model_change,
            help="切换模型会自动开始新的对话。"
        )
        st.session_state.selected_model = selected_model

    with col2:
        st.write("") # 用于垂直对齐
        if st.button("清除当前对话", use_container_width=True):
            clear_chat_history()
            st.toast("对话已清除！", icon="🧹")
            st.rerun()

    # --- 显示历史聊天记录 ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 聊天输入框和响应处理 ---
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