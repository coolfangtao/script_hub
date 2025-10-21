import streamlit as st
import difflib
from shared.sidebar import create_common_sidebar
create_common_sidebar()

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="文本对比工具 | Diff Checker",
    page_icon="🔎",
    layout="wide"
)

# --- 2. 自定义CSS样式 ---
# 注入自定义CSS来覆盖difflib的默认样式，以适应Streamlit的深色和浅色主题
# 这段CSS解决了在深色背景下对比结果看不清的问题
CUSTOM_CSS = """
<style>
    /* 为整个difflib表格增加一些样式 */
    table.diff {
        border-collapse: collapse;
        width: 100%;
        font-family: monospace;
        font-size: 0.9rem;
    }
    /* 表格头部样式 */
    table.diff th {
        background-color: #f0f2f6; /* 浅灰色背景 */
        padding: 8px;
        text-align: center;
    }
    /* 针对深色模式的头部样式 */
    [data-theme="dark"] table.diff th {
        background-color: #262730; /* 深色背景 */
    }
    /* 表格单元格样式 */
    table.diff td {
        padding: 5px;
        vertical-align: top;
        white-space: pre-wrap; /* 自动换行 */
        word-break: break-all;
    }
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
        text-decoration: line-through;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- 3. 页面标题和简介 ---
st.title("🔎 文本对比工具 (Diff Checker)")
st.markdown("一个简单的小工具，用于比较两段文本之间的差异。请在下方左右两个文本框中输入或粘贴内容，然后点击“开始对比”按钮。")

with st.expander("💡 使用小贴士"):
    st.info("""
        - **绿色背景**: 表示在“修改后文本”中新增的内容。
        - **黄色背景**: 表示被修改过的内容行。
        - **红色删除线**: 表示在“原始文本”中被删除的内容。
        - **结果区域可以滚动**: 如果差异内容很长，可以在结果框内上下滚动查看。
    """)

st.divider()

# --- 4. 核心功能区 ---

# 初始化 session_state
if 'text1' not in st.session_state:
    st.session_state.text1 = "这是第一行。\n这是第二行，内容相同。\n这是将被修改的第三行。"
if 'text2' not in st.session_state:
    st.session_state.text2 = "这是第一行。\n这是第二行，内容相同。\n这是已经被修改过的第三行！"

# 创建左右两个并排的列
col1, col2 = st.columns(2, gap="medium")

# 在左侧列创建第一个文本输入框
with col1:
    with st.container(border=True):
        st.subheader("📝 原始文本 (Original Text)")
        original_text = st.text_area(
            label="在此处输入原始文本",
            value=st.session_state.text1,
            height=350,
            key="text1_area",
            label_visibility="collapsed"  # 隐藏标签，因为subheader已经说明了
        )

# 在右侧列创建第二个文本输入框
with col2:
    with st.container(border=True):
        st.subheader("🖋️ 修改后文本 (Modified Text)")
        modified_text = st.text_area(
            label="在此处输入修改后的文本",
            value=st.session_state.text2,
            height=350,
            key="text2_area",
            label_visibility="collapsed"
        )

st.write("")  # 增加一点垂直间距

# 创建对比按钮
if st.button("🚀 开始对比", type="primary", use_container_width=True):
    # 检查是否有输入
    if not original_text or not modified_text:
        st.warning("⚠️ 请确保左右两个文本框都输入了内容。")
    else:
        # 将输入的文本按行分割成列表
        original_lines = original_text.splitlines()
        modified_lines = modified_text.splitlines()

        # 使用 difflib.HtmlDiff 创建一个能够生成HTML表格的对象
        # 注意：这里我们使用 make_table 而不是 make_file
        # make_table 只生成 <table>...</table> 部分，不包含<style>，这样我们自己的CSS才能生效
        d = difflib.HtmlDiff(wrapcolumn=80)
        diff_table_html = d.make_table(
            fromlines=original_lines,
            tolines=modified_lines,
            fromdesc='原始文本',
            todesc='修改后文本'
        )

        # --- 5. 显示对比结果 ---
        st.divider()
        st.subheader("📊 对比结果")

        # 使用 st.markdown 来渲染HTML表格，这样它就可以应用我们之前注入的CSS
        # 相比 st.components.v1.html, markdown 在这种场景下与页面主题的融合度更好
        st.markdown(diff_table_html, unsafe_allow_html=True)