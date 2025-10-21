import streamlit as st
import difflib
import html as html_converter

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="文本对比工具 | Diff Checker",
    page_icon="🔎",
    layout="wide"
)

# --- 2. 自定义CSS样式 (已更新) ---
# 增加了针对“修改”的高亮样式
CUSTOM_CSS = """
<style>
    /* 对比结果容器的样式 */
    .diff-container {
        border-radius: 0.5rem;
        padding: 10px;
        height: 400px;
        overflow-y: scroll;
        font-family: Menlo, Monaco, 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.5;
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

    /* 新增行的背景高亮 (绿色) */
    .diff-add {
        background-color: rgba(40, 167, 69, 0.2);
    }
    /* 删除行的背景高亮 (红色) */
    .diff-sub {
        background-color: rgba(220, 53, 69, 0.2);
        text-decoration: line-through;
    }
    /* (新) 包含修改的行的背景 (淡蓝色，用于区分) */
    .diff-mod {
        background-color: rgba(13, 110, 253, 0.1);
    }
    /* (新) 行内具体修改字符的高亮 (亮黄色) */
    .diff-change {
        background-color: rgba(255, 235, 59, 0.6);
        border-radius: 3px;
        font-weight: bold;
    }

    /* 确保深色主题下，高亮区域的文字依然清晰 */
    [data-theme="dark"] .diff-add,
    [data-theme="dark"] .diff-sub,
    [data-theme="dark"] .diff-mod,
    [data-theme="dark"] .diff-change {
        color: #EAEAEA;
    }
    [data-theme="dark"] .diff-change {
        background-color: rgba(255, 235, 59, 0.5);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- 3. 页面标题和简介 ---
st.title("🔎 文本对比工具 (Diff Checker)")
st.markdown("一个简单的小工具，用于比较两段文本之间的差异。请在下方左右两个文本框中输入或粘贴内容，然后点击“开始对比”按钮。")

# 更新使用说明
with st.expander("💡 使用说明"):
    st.markdown("""
        <ul>
            <li><span style="background-color: rgba(40, 167, 69, 0.2); padding: 2px 5px; border-radius: 3px;">绿色背景</span>: 表示整行是新增的内容。</li>
            <li><span style="background-color: rgba(220, 53, 69, 0.2); padding: 2px 5px; border-radius: 3px;">红色背景 (带删除线)</span>: 表示整行是被删除的内容。</li>
            <li><span style="background-color: rgba(13, 110, 253, 0.1); padding: 2px 5px; border-radius: 3px;">淡蓝色背景</span>: 表示该行有修改。
                <ul><li>行内<span style="background-color: rgba(255, 235, 59, 0.6); font-weight: bold; padding: 1px 4px; border-radius: 3px;">亮黄色高亮</span>的部分是具体的修改之处。</li></ul>
            </li>
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


# --- 5. 对比逻辑和结果展示 (已重构) ---

def highlight_character_diffs(old_line, new_line):
    """
    辅助函数：对两个字符串进行字符级对比，并用HTML标记差异。
    返回两个HTML字符串，分别用于左右两侧的显示。
    """
    matcher = difflib.SequenceMatcher(None, old_line, new_line)
    left_html = []
    right_html = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_fragment = html_converter.escape(old_line[i1:i2])
        new_fragment = html_converter.escape(new_line[j1:j2])

        if tag == 'equal':
            left_html.append(old_fragment)
            right_html.append(new_fragment)
        elif tag == 'replace':
            left_html.append(f'<span class="diff-change">{old_fragment}</span>')
            right_html.append(f'<span class="diff-change">{new_fragment}</span>')
        elif tag == 'delete':
            left_html.append(f'<span class="diff-change">{old_fragment}</span>')
        elif tag == 'insert':
            right_html.append(f'<span class="diff-change">{new_fragment}</span>')

    return "".join(left_html), "".join(right_html)


def generate_side_by_side_diff(text1_lines, text2_lines):
    """
    生成左右分栏对比视图的HTML。
    此版本会处理“替换”操作，进行字符级高亮。
    """
    left_html = []
    right_html = []
    matcher = difflib.SequenceMatcher(None, text1_lines, text2_lines, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in text1_lines[i1:i2]:
                escaped_line = html_converter.escape(line)
                left_html.append(f"<span>{escaped_line}</span>")
                right_html.append(f"<span>{escaped_line}</span>")

        elif tag == 'replace':
            old_chunk_lines = text1_lines[i1:i2]
            new_chunk_lines = text2_lines[j1:j2]

            # 对“替换”块中的每一行进行处理，尽量一一对应
            for i in range(max(len(old_chunk_lines), len(new_chunk_lines))):
                old_line = old_chunk_lines[i] if i < len(old_chunk_lines) else None
                new_line = new_chunk_lines[i] if i < len(new_chunk_lines) else None

                if old_line is not None and new_line is not None:
                    # 如果两侧都有行，进行字符级对比
                    left_diff, right_diff = highlight_character_diffs(old_line, new_line)
                    left_html.append(f'<span class="diff-mod">{left_diff}</span>')
                    right_html.append(f'<span class="diff-mod">{right_diff}</span>')
                elif old_line is not None:
                    # 如果只有旧行，视为删除
                    escaped_line = html_converter.escape(old_line)
                    left_html.append(f'<span class="diff-sub">{escaped_line}</span>')
                    right_html.append('<span>&nbsp;</span>')
                elif new_line is not None:
                    # 如果只有新行，视为新增
                    escaped_line = html_converter.escape(new_line)
                    left_html.append('<span>&nbsp;</span>')
                    right_html.append(f'<span class="diff-add">{escaped_line}</span>')

        elif tag == 'delete':
            for line in text1_lines[i1:i2]:
                escaped_line = html_converter.escape(line)
                left_html.append(f'<span class="diff-sub">{escaped_line}</span>')
                right_html.append('<span>&nbsp;</span>')

        elif tag == 'insert':
            for line in text2_lines[j1:j2]:
                escaped_line = html_converter.escape(line)
                left_html.append('<span>&nbsp;</span>')
                right_html.append(f'<span class="diff-add">{escaped_line}</span>')

    return "".join(left_html), "".join(right_html)


if st.button("🚀 开始对比", type="primary", use_container_width=True):
    if not text1_input or not text2_input:
        st.warning("⚠️ 请确保左右两个文本框都输入了内容。")
    else:
        text1_lines = text1_input.splitlines()
        text2_lines = text2_input.splitlines()

        left_diff_html, right_diff_html = generate_side_by_side_diff(text1_lines, text2_lines)

        st.divider()
        st.subheader("📊 对比结果")

        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.markdown(f'<div class="diff-container">{left_diff_html}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="diff-container">{right_diff_html}</div>', unsafe_allow_html=True)
