# 文件路径: pages/7_AI_对话页面.py

import streamlit as st
import google.generativeai as genai
from shared.sidebar import create_common_sidebar # 导入公共侧边栏函数
from shared.ai_model_config import MODEL_NAME

# --- 页面配置和侧边栏 ---
st.set_page_config(
    page_title="AI 对话",
    page_icon="🤖"
)
create_common_sidebar() # 调用函数创建侧边栏

# --- API 密钥配置 ---
# 从 Streamlit secrets 中获取 API 密钥
try:
    api_key = st.secrets["API_KEY"]
    genai.configure(api_key=api_key)
except (KeyError, FileNotFoundError):
    st.error("Gemini API 密钥未找到。请在 Streamlit secrets 中设置名为 'API_KEY' 的密钥。")
    st.stop()


# --- 初始化模型和会话状态 ---
# 使用 session_state 来持久化聊天记录
if "gemini_chat" not in st.session_state:
    # 初始化模型
    model = genai.GenerativeModel(MODEL_NAME)
    # 开始聊天，并将会话对象存储在 session_state 中
    st.session_state.gemini_chat = model.start_chat(history=[])
    # 初始化一个列表来单独存储和显示消息
    st.session_state.messages = []

# --- 页面标题和介绍 ---
st.title("🤖 AI 对话")
st.caption("一个由 Google Gemini Pro 驱动的聊天机器人")

# --- 显示历史聊天记录 ---
# 遍历 session_state 中存储的所有消息并显示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 聊天输入框 ---
# Streamlit 的 st.chat_input 组件用于接收用户输入
if prompt := st.chat_input("您好，有什么可以帮助您的吗？"):
    # 1. 将用户的输入添加到消息记录中并显示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用 Gemini API 获取回复
    try:
        # 显示一个加载指示器，提升用户体验
        with st.spinner("AI 正在思考中..."):
            # 使用存储在 session_state 中的聊天会话对象发送消息
            response = st.session_state.gemini_chat.send_message(prompt, stream=True)
            response.resolve() # 等待所有流式数据块接收完毕

        # 3. 将 AI 的回复添加到消息记录中并显示
        ai_response = response.text
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant"):
            st.markdown(ai_response)

    except Exception as e:
        st.error(f"调用 API 时出错: {e}")