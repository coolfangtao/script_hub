# apps/ai_01_chat_robot/app.py

import streamlit as st
import google.generativeai as genai

# 从当前应用的模块导入
from config import AppConfig
from state import ChatState
from ui import ChatUI
# 从共享模块导入
from shared.sidebar import create_common_sidebar


def stream_handler(stream):
    """处理 API 返回的流式数据，仅提取文本部分。"""
    for chunk in stream:
        if hasattr(chunk, 'text'):
            yield chunk.text


def main():
    """主应用函数"""
    # 1. 初始化
    cfg = AppConfig()
    state = ChatState()
    ui = ChatUI(cfg, state)

    # 2. 页面和侧边栏设置
    ui.setup_page()
    create_common_sidebar()  # 渲染共享侧边栏
    api_key = ui.render_api_key_sidebar()  # 渲染 API Key 输入

    # 3. API 配置与检查
    if api_key:
        # 仅在 API key 首次被提供或更改时进行配置
        if not state.is_api_key_configured:
            try:
                genai.configure(api_key=api_key)
                state.is_api_key_configured = True
                st.sidebar.success(cfg.API_CONFIG_SUCCESS)
            except Exception as e:
                st.sidebar.error(f"{cfg.API_CONFIG_FAILURE}{e}")
                state.is_api_key_configured = False

    # 如果 API 未配置，则停止应用执行
    if not state.is_api_key_configured:
        st.info("请输入您的 API Key 以开始聊天。")
        st.stop()

    # 4. 渲染主界面
    ui.render_header()
    ui.render_controls()
    ui.render_chat_history()

    # 5. 处理用户输入和模型响应
    if prompt := ui.get_user_prompt():
        state.add_message("user", prompt)

        # 立即在UI上显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                with st.spinner(cfg.SPINNER_TEXT):
                    model = genai.GenerativeModel(state.selected_model)

                    # 将我们的消息格式转换为 Gemini API 需要的格式
                    # Gemini API 使用 'model' 代表 'assistant'
                    gemini_history = [
                        {"role": "model" if msg["role"] == "assistant" else "user", "parts": [msg["content"]]}
                        for msg in state.messages[:-1]  # 发送除最新用户消息外的所有历史
                    ]

                    chat = model.start_chat(history=gemini_history)
                    response_stream = chat.send_message(prompt, stream=True)

                    full_response = st.write_stream(stream_handler(response_stream))

            # 将完整的助理回复添加到历史记录中
            state.add_message("assistant", full_response)

        except Exception as e:
            st.error(f"{cfg.API_CALL_ERROR}{e}")
            # 如果出错，移除刚刚添加的用户消息，以保持同步
            state.pop_message()

        # 在处理完一次交互后，建议执行 st.rerun()
        # 这可以确保 UI 组件（如 on_change 回调）的行为一致性
        # 虽然在这个简单应用中不是必须的，但对于复杂应用是个好习惯
        # st.rerun()


# 运行主程序
if __name__ == "__main__":
    main()