import streamlit as st
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数

create_common_sidebar()

import streamlit as st


# --- 1. 核心逻辑 (Model) ---
# 这个函数完全独立于 Streamlit，负责所有的数据处理。
# 它的功能是接收一个字符串，返回一个移除了所有空白行的新字符串。

def remove_blank_lines(text: str) -> str:
    """
    从给定的文本字符串中移除所有空白行。
    空白行是指完全为空或只包含空格、制表符等空白字符的行。

    Args:
        text (str): 包含潜在空白行的输入字符串。

    Returns:
        str: 已移除所有空白行的新字符串。
    """
    if not isinstance(text, str):
        return ""

    # 1. 将输入文本按行分割成列表
    lines = text.splitlines()

    # 2. 过滤掉所有只包含空白字符的行
    non_empty_lines = [line for line in lines if line.strip()]

    # 3. 将处理后的行重新用换行符连接成一个字符串
    return "\n".join(non_empty_lines)


# --- 2. 用户界面 (View) ---
# 这个函数负责定义和显示所有的 Streamlit 界面元素。

def setup_ui():
    """
    设置并显示 Streamlit 用户界面。
    """
    # --- 页面配置 ---
    st.set_page_config(
        page_title="空白行去除工具",
        page_icon="🧹"
    )

    # --- 页面标题 ---
    st.title("🧹 文本空白行去除工具")
    st.write("一键去除所有的空白行")

    # --- 输入文本框 ---
    st.subheader("1. 在下方粘贴您的文本")
    input_text = st.text_area(
        "输入文本框",
        height=300,
        placeholder="请在这里粘贴包含空白行的文本...",
        label_visibility="collapsed"
    )

    # --- 处理按钮和逻辑调用 ---
    if st.button("去除空白行", type="primary"):
        if input_text:
            # 当按钮被点击时，调用核心逻辑函数进行处理
            processed_text = remove_blank_lines(input_text)

            # --- 显示结果 ---
            st.subheader("2. 处理完成的文本")
            st.text_area(
                "结果文本框",
                value=processed_text,
                height=300,
                label_visibility="collapsed"
            )
            st.success("所有空白行已成功去除！")
            st.balloons()
        else:
            # 如果用户没有输入任何文本就点击按钮，则发出警告
            st.warning("请输入一些文本再进行处理。")


# --- 3. 主程序入口 ---
# 这是程序的起点。当运行 `streamlit run app.py` 时，这个部分会被执行。

if __name__ == "__main__":
    setup_ui()