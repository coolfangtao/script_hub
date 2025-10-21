import streamlit as st
import difflib
import re
from streamlit.components.v1 import html
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="文本对比工具 | Diff Checker",
    page_icon="🔎",
    layout="wide"
)

# --- 2. 自定义CSS样式 ---
# 这段CSS会覆盖 difflib 的默认颜色，以更好地适配Streamlit的浅色和深色主题
CUSTOM_CSS = """
<style>
    /* 这部分是全局样式，会影响到下面注入的 difflib 表格 */
    table.diff {
        border-collapse: collapse;
        width: 100%;
        font-family: Menlo, Monaco, 'Courier New', monospace;
        font-size: 0.9rem;
        border: 1px solid #444; 
    }
    table.diff th {
        background-color: #f0f2f6;
        color: #333;
        padding: 8px;
        text-align: center;
        font-weight: 600;
    }
    [data-theme="dark"] table.diff th {
        background-color: #262730;
        color: #FAFAFA;
        border-bottom: 1px solid #444;
    }
    /* 使用半透明的RGBA颜色，这样无论在深色还是浅色背景下都能清晰显示 */
    .diff_add {
        background-color: rgba(40, 167, 69, 0.2);
    }
    .diff_chg {
        background-color: rgba(255, 193, 7, 0.2);
    }
    .diff_sub {
        background-color: rgba(220, 53, 69, 0.2);
        text-decoration: line-through;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- 3. 页面标题和简介 ---
st.title("🔎 文本对比工具 (Diff Checker)")
st.markdown("一个简单的小工具，用于比较两段文本之间的差异。请在下方左右两个文本框中输入或粘贴内容，然后点击“开始对比”按钮。")

with st.expander("💡 使用说明"):
    st.markdown("""
        <ul>
            <li><span style="background-color: rgba(40, 167, 69, 0.2); padding: 2px 5px; border-radius: 3px;">绿色背景</span>: 表示新增的内容。</li>
            <li><span style="background-color: rgba(255, 193, 7, 0.2); padding: 2px 5px; border-radius: 3px;">黄色背景</span>: 表示被修改的内容行。</li>
            <li><span style="background-color: rgba(220, 53, 69, 0.2); padding: 2px 5px; border-radius: 3px;">红色背景</span>: 表示被删除的内容。</li>
        </ul>
    """, unsafe_allow_html=True)
st.divider()

# --- 4. 核心功能区 ---

# 初始化 session_state，使用更有说明性的默认文本
if 'text1' not in st.session_state:
    st.session_state.text1 = "Streamlit is an open-source app framework.\nIt's a faster way to build and share data apps.\nThis line will be removed.\nThis line will be modified."
if 'text2' not in st.session_state:
    st.session_state.text2 = "Streamlit is a great open-source app framework.\nIt's a faster way to build and share data apps.\nThis line is new.\nThis line has been modified."

# 使用带边框的容器来美化布局
with st.container(border=True):
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.subheader("📝 原始文本 (Original)")
        text1_input = st.text_area(
            "原始文本",
            value=st.session_state.text1,
            height=300,
            key="text1_area",
            label_visibility="collapsed"
        )
    with col2:
        st.subheader("🖋️ 修改后文本 (Modified)")
        text2_input = st.text_area(
            "修改后文本",
            value=st.session_state.text2,
            height=300,
            key="text2_area",
            label_visibility="collapsed"
        )

st.write("")  # 增加一点垂直间距

# 创建对比按钮
if st.button("🚀 开始对比", type="primary", use_container_width=True):
    if not text1_input or not text2_input:
        st.warning("⚠️ 请确保左右两个文本框都输入了内容。")
    else:
        text1_lines = text1_input.splitlines()
        text2_lines = text2_input.splitlines()

        d = difflib.HtmlDiff(wrapcolumn=80)

        # 生成包含内联样式的完整HTML文件
        full_diff_html = d.make_file(
            fromlines=text1_lines,
            tolines=text2_lines,
            fromdesc='原始文本',
            todesc='修改后文本'
        )

        # 提取 difflib 生成的 <style> 内容
        style_match = re.search(r'<style type="text/css">(.*?)</style>', full_diff_html, re.DOTALL)
        diff_style = style_match.group(1) if style_match else ""

        # 提取 <body> 内部的内容
        body_match = re.search(r'<body>(.*)</body>', full_diff_html, re.DOTALL)
        diff_body = body_match.group(1).strip() if body_match else "<p>错误：无法提取对比结果。</p>"

        # 将提取出的样式和内容组合起来，注入到页面中
        # 这样既保留了difflib的布局，又允许我们的CUSTOM_CSS覆盖颜色
        final_html = f"<style>{diff_style}</style>\n{diff_body}"

        st.divider()
        st.subheader("📊 对比结果")

        html(final_html, height=400, scrolling=True)

