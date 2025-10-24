import streamlit as st
from shared.sidebar import create_common_sidebar
create_common_sidebar()


# --- 1. 核心逻辑 (Model) ---
# 这部分保持不变，它已经是纯函数，非常棒。

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


# --- 2. 界面和状态管理 (View-Model) ---

def initialize_session_state():
    """
    初始化 Streamlit session_state 中需要的键。
    """
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""
    if "processed_text" not in st.session_state:
        st.session_state.processed_text = ""

def run_processing():
    """
    执行处理逻辑并更新 session_state。
    这个函数将作为按钮的 on_click 回调。
    """
    # 检查 session_state 中的 input_text
    if st.session_state.input_text:
        # 当按钮被点击时，调用核心逻辑函数进行处理
        st.session_state.processed_text = remove_blank_lines(st.session_state.input_text)
        st.success("所有空白行已成功去除！")
        st.balloons()
    else:
        # 如果用户没有输入任何文本就点击按钮，则发出警告
        st.session_state.processed_text = "" # 清空旧的结果
        st.warning("请输入一些文本再进行处理。")

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
    # 使用 key="input_text" 将 text_area 与 session_state.input_text 双向绑定
    # 这样用户输入会立即更新 session_state，
    # 并且从其他页面返回时，session_state 会自动填充 text_area。
    st.text_area(
        "输入文本框",
        height=300,
        placeholder="请在这里粘贴包含空白行的文本...",
        label_visibility="collapsed",
        key="input_text" # 关键改动：使用 key 绑定 session_state
    )

    # --- 处理按钮和逻辑调用 ---
    # 使用 on_click 回调函数来处理逻辑
    # 这样处理逻辑只在点击时运行一次
    st.button("去除空白行", type="primary", on_click=run_processing)

    # --- 显示结果 ---
    # 只有当 session_state.processed_text 中有内容时才显示
    if st.session_state.processed_text:
        st.subheader("2. 处理完成的文本")
        st.text_area(
            "结果文本框",
            value=st.session_state.processed_text, # 关键改动：值来源于 session_state
            height=300,
            label_visibility="collapsed",
            help="您可以从这里复制处理后的文本"
            # 注意：这里我们不使用 key，因为这是一个只读的输出。
            # 它的值在每次重绘时都会被 session_state.processed_text 覆盖。
        )


# --- 3. 主程序入口 ---
if __name__ == "__main__":
    # 在UI设置之前初始化 session_state
    initialize_session_state()
    # 运行UI渲染
    setup_ui()
