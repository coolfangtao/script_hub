import streamlit as st
import google.generativeai as genai
from shared.sidebar import create_common_sidebar
from shared.config import Config


# --- 1. 配置和初始化 ---

def setup_page_and_sidebar():
    """配置页面和侧边栏"""
    st.set_page_config(
        page_title="AI 对话",
        page_icon="🤖",
        layout="wide"
    )
    create_common_sidebar()


def configure_api():
    """配置 Google Gemini API"""
    try:
        cfg = Config()
        api_key = st.secrets[cfg.GEMINI_API_KEY]
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"API 配置失败: {e}")
        return False


def initialize_session_state():
    """初始化或检查会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None


# --- BUG 1 FIX: 创建一个专门的清除历史记录的函数 ---
def clear_chat_history():
    """清除所有聊天记录和相关的会话状态"""
    st.session_state.messages = []
    # 移除了对旧的 gemini_chat 对象的依赖


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

    if not configure_api():
        st.stop()

    cfg = Config()
    MODEL_OPTIONS = cfg.GEMINI_MODEL_OPTIONS

    # --- 顶部布局：左侧模型选择，右侧清除按钮 ---
    col1, col_spacer, col2 = st.columns([2, 5, 2])

    with col1:
        # 当模型选择变化时，自动清除历史记录
        def on_model_change():
            if st.session_state.selected_model != st.session_state.model_selector:
                clear_chat_history()
                st.toast(f"模型已切换，新的对话开始啦！", icon="🔄")

        selected_model = st.selectbox(
            "请选择一个 AI 模型:",
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

                    # --- BUG 2 FIX: 使用 st.session_state.messages 作为唯一可信的历史来源 ---
                    # 转换我们的消息格式为 Gemini API 需要的格式
                    # Gemini API 使用 'model' 代表 'assistant'
                    gemini_history = [
                        {"role": "model" if msg["role"] == "assistant" else "user", "parts": [msg["content"]]}
                        for msg in st.session_state.messages[:-1]  # 发送除最新用户消息外的所有历史
                    ]

                    chat = model.start_chat(history=gemini_history)
                    response_stream = chat.send_message(prompt, stream=True)

                    full_response = st.write_stream(stream_handler(response_stream))

            # 将完整的助理回复添加到历史记录中
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"调用 API 时出错: {e}")
            # 如果出错，移除刚刚添加的用户消息，以保持同步
            st.session_state.messages.pop()


# --- 4. 运行主程序 ---
if __name__ == "__main__":
    main()