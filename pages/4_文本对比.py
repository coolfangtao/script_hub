import streamlit as st
import difflib
import html as html_converter

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="文本对比工具 | Diff Checker",
    page_icon="🔎",
    layout="wide"
)

# --- 2. 自定义CSS样式 ---
# 适配新的左右分栏对比视图
CUSTOM_CSS = """
<style>
    /* 对比结果容器的样式，模仿st.text_area */
    .diff-container {
        border-radius: 0.5rem;
        padding: 10px;
        height: 400px;
        overflow-y: scroll;
        font-family: Menlo, Monaco, 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.4;
        background-color: #ffffff;
        border: 1px solid #d1d5db; 
    }

    /* 深色主题下的容器样式 */
    [data-theme="dark"] .diff-container {
        background-color: #0E1117; 
        border: 1px solid #30363d;
        color: #fafafa;
    }

    /* 容器内每一行文本的样式 */
    .diff-container span {
        display: block;
        white-space: pre-wrap;
        word-wrap: break-word;
    }

    /* 新增行的背景高亮 */
    .diff-add {
        background-color: rgba(40, 167, 69, 0.2);
    }
    /* 删除行的背景高亮 */
    .diff-sub {
        background-color: rgba(220, 53, 69, 0.2);
        text-decoration: line-through;
    }

    /* 确保深色主题下，高亮区域的文字依然清晰 */
    [data-theme="dark"] .diff-add,
    [data-theme="dark"] .diff-sub {
        color: #EAEAEA;
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
            <li><span style="background-color: rgba(220, 53, 69, 0.2); padding: 2px 5px; border-radius: 3px;">红色背景 (带删除线)</span>: 表示被删除的内容。</li>
        </ul>
    """, unsafe_allow_html=True)
st.divider()

# --- 4. 核心功能区 ---

# 初始化 session_state
if 'text1' not in st.session_state:
    st.session_state.text1 = "Streamlit is an open-source app framework.\nIt's a faster way to build and share data apps.\nThis line will be removed.\nThis line will be modified."
if 'text2' not in st.session_state:
    st.session_state.text2 = "Streamlit is a great open-source app framework.\nIt's a faster way to build and share data apps.\nThis line is new.\nThis line has been modified."

# 输入框布局
with st.container(border=True):
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.subheader("📝 原始文本 (Original)")
        text1_input = st.text_area("原始文本", value=st.session_state.text1, height=300, key="text1_area",
                                   label_visibility="collapsed")
    with col2:
        st.subheader("🖋️ 修改后文本 (Modified)")
        text2_input = st.text_area("修改后文本", value=st.session_state.text2, height=300, key="text2_area",
                                   label_visibility="collapsed")

st.write("")


# --- 5. 对比逻辑和结果展示 ---

def generate_side_by_side_diff(text1_lines, text2_lines):
    """
    生成左右分栏对比视图的HTML。
    """
    left_html = []
    right_html = []

    matcher = difflib.SequenceMatcher(None, text1_lines, text2_lines)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in text1_lines[i1:i2]:
                escaped_line = html_converter.escape(line)
                left_html.append(f"<span>{escaped_line}</span>")
                right_html.append(f"<span>{escaped_line}</span>")

        elif tag == 'replace':
            # 将“替换”操作分解为“删除”和“添加”
            for line in text1_lines[i1:i2]:
                escaped_line = html_converter.escape(line)
                left_html.append(f'<span class="diff-sub">{escaped_line}</span>')
            for line in text2_lines[j1:j2]:
                escaped_line = html_converter.escape(line)
                right_html.append(f'<span class="diff-add">{escaped_line}</span>')

            # 通过添加空行来保持两侧对齐
            len_left = i2 - i1
            len_right = j2 - j1
            if len_left < len_right:
                left_html.extend(['<span>&nbsp;</span>'] * (len_right - len_left))
            elif len_right < len_left:
                right_html.extend(['<span>&nbsp;</span>'] * (len_left - len_right))

        elif tag == 'delete':
            for line in text1_lines[i1:i2]:
                escaped_line = html_converter.escape(line)
                left_html.append(f'<span class="diff-sub">{escaped_line}</span>')
                right_html.append('<span>&nbsp;</span>')

        elif tag == 'insert':
            for line in text2_lines[j1:j2]:
                left_html.append('<span>&nbsp;</span>')
                escaped_line = html_converter.escape(line)
                right_html.append(f'<span class="diff-add">{escaped_line}</span>')

    # 使用<br>连接每一行，以便在HTML中正确换行
    return "<br>".join(left_html), "<br>".join(right_html)


if st.button("🚀 开始对比", type="primary", use_container_width=True):
    if not text1_input or not text2_input:
        st.warning("⚠️ 请确保左右两个文本框都输入了内容。")
    else:
        text1_lines = text1_input.splitlines()
        text2_lines = text2_input.splitlines()

        left_diff_html, right_diff_html = generate_side_by_side_diff(text1_lines, text2_lines)

        st.divider()
        st.subheader("📊 对比结果")

        # 使用新的左右分栏布局来展示结果
        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.markdown(f'<div class="diff-container">{left_diff_html}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="diff-container">{right_diff_html}</div>', unsafe_allow_html=True)

