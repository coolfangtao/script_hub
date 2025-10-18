import streamlit as st
import difflib
from streamlit.components.v1 import html

# --- 页面基础配置 ---
st.set_page_config(
    page_title="文本对比工具 | Diff Checker",
    page_icon="🔎",
    layout="wide"  # 使用宽屏布局以更好地并排显示
)

# --- 页面标题和简介 ---
st.title("🔎 文本对比工具 (Diff Checker)")
st.write("一个简单的小工具，用于比较两段文本之间的差异。请在下方左右两个文本框中输入或粘贴内容，然后点击“开始对比”按钮。")
st.markdown("---")  # 分割线

# --- 核心功能区 ---

# 1. 创建左右两个并排的列
col1, col2 = st.columns(2)

# 2. 在左侧列创建第一个文本输入框
with col1:
    st.subheader("原始文本 (Original Text)")
    # 使用 session_state 来在页面重载时保留用户输入
    if 'text1' not in st.session_state:
        st.session_state.text1 = "这是第一行。\n这是第二行，内容相同。\n这是将被修改的第三行。"

    text1_input = st.text_area(
        label="在此处输入原始文本",
        value=st.session_state.text1,
        height=300,
        key="text1_area"
    )

# 3. 在右侧列创建第二个文本输入框
with col2:
    st.subheader("修改后文本 (Modified Text)")
    if 'text2' not in st.session_state:
        st.session_state.text2 = "这是第一行。\n这是第二行，内容相同。\n这是已经被修改过的第三行！"

    text2_input = st.text_area(
        label="在此处输入修改后的文本",
        value=st.session_state.text2,
        height=300,
        key="text2_area"
    )

# 4. 创建对比按钮和处理逻辑
st.markdown("<br>", unsafe_allow_html=True)  # 增加一点间距
if st.button("🚀 开始对比", use_container_width=True):
    # 将输入的文本按行分割成列表，这是 difflib 的标准输入格式
    text1_lines = text1_input.splitlines()
    text2_lines = text2_input.splitlines()

    # 检查是否有输入
    if not text1_input or not text2_input:
        st.warning("请输入需要对比的两段文本。")
    else:
        # 使用 difflib.HtmlDiff 创建一个能够生成HTML表格的对象
        d = difflib.HtmlDiff(wrapcolumn=80)  # wrapcolumn 控制每行最多显示多少字符

        # 生成完整的、包含差异高亮的HTML表格
        # fromdesc 和 todesc 是表格中左右两侧的标题
        diff_html = d.make_file(
            fromlines=text1_lines,
            tolines=text2_lines,
            fromdesc='原始文本',
            todesc='修改后文本'
        )

        # 使用 st.components.v1.html 来渲染HTML，并允许滚动
        st.subheader("对比结果")
        st.info("绿色背景表示新增的内容，黄色背景表示修改的内容，红色删除线表示删除的内容。")
        html(diff_html, height=400, scrolling=True)

# --- 页脚 ---
st.markdown("---")
st.markdown("由 Gemini 和 Streamlit 强力驱动")