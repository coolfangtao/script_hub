import streamlit as st
import difflib
import re
from streamlit.components.v1 import html

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="文本对比工具 | Diff Checker",
    page_icon="🔎",
    layout="wide"
)

# --- 2. 自定义CSS样式 ---
# 这段CSS是解决你截图中显示问题的关键。
# 它覆盖了difflib的默认样式，并使用 [data-theme="dark"] 选择器来专门为Streamlit的深色主题优化颜色。
CUSTOM_CSS = """
<style>
    table.diff {
        border-collapse: collapse;
        width: 100%;
        font-family: Menlo, Monaco, 'Courier New', monospace;
        font-size: 0.9rem;
        border: 1px solid #444; /* 为表格增加一个细边框 */
    }
    /* 表格头部 (图例) */
    table.diff th {
        background-color: #f0f2f6; /* 浅色模式下的背景 */
        color: #333;
        padding: 8px;
        text-align: center;
        font-weight: 600;
    }
    /* 专门为深色模式优化的头部样式 */
    [data-theme="dark"] table.diff th {
        background-color: #262730; /* 深色模式下的背景 */
        color: #FAFAFA;
        border-bottom: 1px solid #444;
    }
    /* 表格单元格 */
    table.diff td {
        padding: 4px 6px;
        vertical-align: top;
        white-space: pre-wrap;
        word-break: break-all;
    }
    /* 行号单元格 */
    .diff_next, .diff_header {
        text-align: right;
        color: #888;
        padding-right: 10px;
    }
    /* 使用半透明的RGBA颜色，这样无论在深色还是浅色背景下都能清晰显示 */
    /* 新增行的背景色 (绿色) */
    .diff_add {
        background-color: rgba(40, 167, 69, 0.2);
    }
    /* 修改行的背景色 (黄色) */
    .diff_chg {
        background-color: rgba(255, 193, 7, 0.2);
    }
    /* 删除行的背景色 (红色) */
    .diff_sub {
        background-color: rgba(220, 53, 69, 0.2);
        text-decoration: line-through; /* 保留删除线 */
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- 3. 页面标题和简介 ---
st.title("🔎 文本对比工具 (Diff Checker)")
st.markdown("一个简单的小工具，用于比较两段文本之间的差异。请在下方左右两个文本框中输入或粘贴内容，然后点击“开始对比”按钮。")

with st.expander("💡 使用说明"):
    # FIX 1: 使用st.markdown并设置unsafe_allow_html=True来正确渲染HTML标签
    st.markdown("""
        <ul>
            <li><span style="background-color: rgba(40, 167, 69, 0.2); padding: 2px 5px; border-radius: 3px;">绿色背景</span>: 表示新增的内容。</li>
            <li><span style="background-color: rgba(255, 193, 7, 0.2); padding: 2px 5px; border-radius: 3px;">黄色背景</span>: 表示被修改的内容行。</li>
            <li><span style="background-color: rgba(220, 53, 69, 0.2); padding: 2px 5px; border-radius: 3px;">红色背景</span>: 表示被删除的内容。</li>
        </ul>
    """, unsafe_allow_html=True)
st.divider()

# --- 4. 核心功能区 ---

# 初始化 session_state
if 'text1' not in st.session_state:
    st.session_state.text1 = "这是第一行。\n这是第二行，内容相同。\n这是将被修改的第三行。"
if 'text2' not in st.session_state:
    st.session_state.text2 = "这是第1行。\n这是第二行，内容不相同。\n这是被修改过的第三行。"

# 使用带边框的容器来美化布局
with st.container(border=True):
    col1, col2 = st.columns(2, gap="medium")
    # 在左侧列创建第一个文本输入框
    with col1:
        st.subheader("📝 原始文本 (Original)")
        text1_input = st.text_area(
            "原始文本",
            value=st.session_state.text1,
            height=300,
            key="text1_area",
            label_visibility="collapsed"
        )
    # 在右侧列创建第二个文本输入框
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

        # 使用 difflib.HtmlDiff
        d = difflib.HtmlDiff(wrapcolumn=80)

        # FIX 2: 使用 make_file() 生成包含高亮信息的完整HTML，然后提取其<body>部分
        # 这样既能获得带CSS类的表格，又能避免与Streamlit的样式冲突。
        full_diff_html = d.make_file(
            fromlines=text1_lines,
            tolines=text2_lines,
            fromdesc='原始文本',
            todesc='修改后文本'
        )

        # 使用正则表达式提取<body>标签内的所有内容
        body_content_match = re.search(r'<body>(.*)</body>', full_diff_html, re.DOTALL)
        if body_content_match:
            diff_body = body_content_match.group(1).strip()
        else:
            diff_body = "<p>错误：无法提取对比结果。</p>"

        st.divider()
        st.subheader("📊 对比结果")

        # 使用 st.components.v1.html 来渲染提取出的HTML，并允许滚动
        # 你的自定义CSS现在可以正确应用到这个带有高亮类的表格上了
        html(diff_body, height=400, scrolling=True)
