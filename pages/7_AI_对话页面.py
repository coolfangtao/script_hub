import streamlit as st
import google.generativeai as genai
from typing import List

# 导入您自定义的共享模块
from shared.sidebar import create_common_sidebar
from shared.config import Config

# --- 页面配置 ---
st.set_page_config(
    page_title="Gemini AI 对话",
    page_icon="✨",
    layout="wide"
)

# --- 实例化配置 ---
# 严格遵循您的要求，使用 Config 类
cfg = Config()

# --- API 密钥配置 ---
# 将密钥配置放在主逻辑之外，确保在应用启动时首先检查
try:
    api_key = st.secrets[cfg.GEMINI_API_KEY]
    genai.configure(api_key=api_key)
except (KeyError, FileNotFoundError):
    st.error(f"Gemini API 密钥未找到。请在 Streamlit secrets 中设置一个名为 '{cfg.GEMINI_API_KEY}' 的密钥。")
    st.info("在本地运行时，可以创建一个 `.streamlit/secrets.toml` 文件并添加 `GEMINI_API_KEY = 'YOUR_API_KEY'`。")
    st.stop()


# --- 通用函数 ---

@st.cache_data(show_spinner="正在加载 AI 模型列表...")
def get_available_models() -> List[str]:
    """通过 API 动态获取所有可用的 Gemini 模型列表，并进行筛选"""
    try:
        return [
            m.name.split('/')[-1]
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods and 'gemini' in m.name
        ]
    except Exception as e:
        st.warning(f"无法动态获取模型列表: {e}\n\n将使用预设的备用列表。")
        # 提供一个备用列表以防 API 调用失败
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]


def initialize_chat(model_name: str) -> None:
    """初始化或重置聊天会话"""
    st.session_state.selected_model = model_name
    model = genai.GenerativeModel(model_name)
    st.session_state.gemini_chat = model.start_chat(history=[])
    st.session_state.messages = []


# --- 主应用 ---

def main():
    # --- 侧边栏 ---
    # 严格遵循您的要求，调用公共侧边栏函数
    create_common_sidebar()

    # 在公共侧边栏下方，添加此页面专属的控件
    with st.sidebar:
        st.divider()  # 添加一条分割线，区分公共部分和页面专属部分
        st.subheader("当前页面设置")
        if st.button("🗑️ 清除当前对话", use_container_width=True):
            if "selected_model" in st.session_state:
                initialize_chat(st.session_state.selected_model)
                st.rerun()

    # --- 页面标题和介绍 ---
    st.title("🤖 Gemini AI 对话")
    st.caption("一个由 Google Gemini Pro 驱动的聊天机器人")

    # --- 高级设置 (模型选择) ---
    with st.expander("⚙️ 模型选择与设置", expanded=False):
        model_options = get_available_models()
        default_model = "gemini-1.5-flash"
        default_index = model_options.index(default_model) if default_model in model_options else 0

        selected_model = st.selectbox(
            "选择一个 AI 模型:",
            options=model_options,
            index=default_index,
            help="更改模型将会自动开始一个新的对话。"
        )

    # --- 初始化会话状态 ---
    if "gemini_chat" not in st.session_state or st.session_state.get("selected_model") != selected_model:
        initialize_chat(selected_model)
        st.toast(f"模型已切换为 `{selected_model}`", icon="🧠")

    # --- 显示历史聊天记录 ---
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 聊天输入框 ---
    if prompt := st.chat_input("你好，有什么可以帮你的吗？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 调用 Gemini API 并以流式方式显示回复
        try:
            with st.chat_message("assistant"):
                with st.spinner("AI 正在思考中..."):
                    response_stream = st.session_state.gemini_chat.send_message(prompt, stream=True)
                    # 使用 st.write_stream 优雅地处理流式输出
                    full_response = st.write_stream(response_stream)

            # 将完整的 AI 回复添加到消息记录中
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"调用 API 时出错: {e}")


if __name__ == "__main__":
    main()