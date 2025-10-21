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


def initialize_chat_session(selected_model):
    """
    根据选择的模型初始化或重置聊天会话。
    如果模型被切换，则清空历史记录并开始新的会话。
    """
    model_switched = "selected_model" in st.session_state and st.session_state.get("selected_model") != selected_model

    if "gemini_chat" not in st.session_state or model_switched:
        if model_switched:
            st.toast(f"模型已切换为 {selected_model}，新的对话开始啦！", icon="🔄")

        st.session_state.selected_model = selected_model
        model = genai.GenerativeModel(selected_model)
        st.session_state.gemini_chat = model.start_chat(history=[])
        st.session_state.messages = []


# --- 2. 核心修复：流式数据处理器 ---

def stream_handler(stream):
    """
    这是一个生成器函数，用于处理 Gemini API 返回的流。
    它会迭代流中的每一个响应块（chunk），并仅提取出文本部分（.text）。
    这样，st.write_stream 接收到的就是一个纯文本流。
    """
    for chunk in stream:
        if hasattr(chunk, 'text'):
            yield chunk.text


# --- 3. 主应用界面 ---

def main():
    """主应用函数"""
    setup_page_and_sidebar()

    st.title("🤖 AI 对话")
    st.caption("一个由 Google Gemini 驱动的聊天机器人")

    if not configure_api():
        st.stop()

    cfg = Config()
    MODEL_OPTIONS = cfg.GEMINI_MODEL_OPTIONS

    # --- 顶部布局：左侧模型选择，右侧清除按钮 ---
    col1, col_spacer, col2 = st.columns([2, 5, 2])

    with col1:
        selected_model = st.selectbox(
            "请选择一个 AI 模型:",
            options=MODEL_OPTIONS,
            index=0,
            key="model_selector",
            label_visibility="collapsed",
            help="不同模型的能力和响应速度各异。"
        )

    with col2:
        st.write("")
        if st.button("清除当前对话", use_container_width=True):
            initialize_chat_session(selected_model)
            st.toast("对话已清除！", icon="🧹")
            st.rerun()

    initialize_chat_session(selected_model)

    # --- 显示历史聊天记录 ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- MODIFICATION REVERTED: 将聊天输入框恢复为始终在底部 ---
    # 移除了根据是否有对话历史来改变输入框位置的复杂逻辑。
    # 现在输入框将始终固定在页面底部，这是最稳定可靠的方式。
    if prompt := st.chat_input("您好，有什么可以帮助您的吗？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                with st.spinner("AI 正在思考中..."):
                    response_stream = st.session_state.gemini_chat.send_message(prompt, stream=True)
                    full_response = st.write_stream(stream_handler(response_stream))
            st.session_state.messages.append({"role": "assistant", "content": full_response})

            # 同样移除了之前用于切换输入框位置的 st.rerun() 调用

        except Exception as e:
            st.error(f"调用 API 时出错: {e}")


# --- 4. 运行主程序 ---

if __name__ == "__main__":
    main()