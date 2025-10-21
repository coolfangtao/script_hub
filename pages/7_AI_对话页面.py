import streamlit as st
import google.generativeai as genai
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数
from shared.config import Config


# --- 1. 配置和初始化 ---

def setup_page_and_sidebar():
    """配置页面和侧边栏"""
    st.set_page_config(
        page_title="🤖 AI 对话",
        page_icon="🤖",
        layout="wide"  # 居中布局更美观
    )
    create_common_sidebar()  # 调用函数创建侧边栏


def configure_api():
    """配置 Google Gemini API"""
    try:
        cfg = Config()
        api_key = st.secrets[cfg.GEMINI_API_KEY]
        genai.configure(api_key=api_key)
        return True
    except (KeyError, FileNotFoundError):
        st.error("Gemini API 密钥未找到。请在 Streamlit secrets 中设置好密钥。")
        return False


def initialize_chat_session(selected_model):
    """
    根据选择的模型初始化或重置聊天会话。
    如果模型被切换，则清空历史记录并开始新的会话。
    """
    # 检查 session_state 中是否已有聊天记录，或者用户是否切换了模型
    if "gemini_chat" not in st.session_state or st.session_state.get("selected_model") != selected_model:
        # 提示用户模型已切换，对话已重置
        if "gemini_chat" in st.session_state:
            st.toast(f"模型已切换为 {selected_model}，新的对话开始啦！", icon="🔄")

        st.session_state.selected_model = selected_model
        # 初始化模型
        model = genai.GenerativeModel(selected_model)
        # 开始新的聊天
        st.session_state.gemini_chat = model.start_chat(history=[])
        # 初始化消息列表用于显示
        st.session_state.messages = []


# --- 2. 主应用界面 ---

def main():
    """主应用函数"""
    setup_page_and_sidebar()

    st.title("🤖 AI 对话")
    st.caption("一个由 Google Gemini Pro 驱动的聊天机器人")

    if not configure_api():
        st.stop()  # 如果API密钥配置失败，则停止运行

    # --- 模型选择 ---
    temp = Config()
    MODEL_OPTIONS = temp.GEMINI_MODEL_OPTIONS
    selected_model = st.selectbox(
        "请选择一个 AI 模型:",
        options=MODEL_OPTIONS,
        index=0,
        help="不同模型的能力和响应速度各异。详情请访问 https://aistudio.google.com/"
    )

    initialize_chat_session(selected_model)

    # --- 显示历史聊天记录 ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 聊天输入框和响应处理 ---
    if prompt := st.chat_input("您好，有什么可以帮助您的吗？"):
        # 1. 将用户的输入添加到消息记录中并显示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. 调用 Gemini API 获取流式回复
        try:
            with st.chat_message("assistant"):
                with st.spinner("AI 正在思考中..."):
                    # 获取流式响应
                    response_stream = st.session_state.gemini_chat.send_message(prompt, stream=True)
                    # 使用 st.write_stream 直接处理流式数据，它会自动显示并返回完整响应
                    full_response = st.write_stream(response_stream)

            # 3. 将 AI 的完整回复添加到消息记录中
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"调用 API 时出错: {e}")


# --- 3. 运行主程序 ---

if __name__ == "__main__":
    main()