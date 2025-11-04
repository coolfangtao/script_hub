import streamlit as st
import difflib
import re
from typing import List, Tuple
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数
st.set_page_config(page_title="文本对比工具", layout="wide")
create_common_sidebar(current_label="📄 文本对比")


# --- CSS样式 (无需改动) ---
def inject_custom_css():
    """
    注入自定义CSS样式，以美化差异化文本的展示效果，并兼容亮暗两种主题。
    """
    st.markdown(
        """
        <style>
            .diff-container {
                display: block; /* 改为block以保留换行 */
                white-space: pre-wrap; /* 保留空白和换行 */
                font-family: 'Courier New', Courier, monospace;
                line-height: 1.6;
                width: 100%;
            }
            .diff-container span {
                padding: 0.1em 0.2em;
                margin: 0.1em 0;
                border-radius: 0.3em;
            }
            .legend-item {
                padding: 0.1em 0.3em;
                margin: 0.1em 0;
                border-radius: 0.3em;
                display: inline-block;
            }
            .diff-add, .legend-add {
                background-color: rgba(46, 125, 50, 0.3);
                border: 1px solid rgba(46, 125, 50, 0.8);
            }
            .diff-delete, .legend-delete {
                background-color: rgba(198, 40, 40, 0.3);
                border: 1px solid rgba(198, 40, 40, 0.8);
                text-decoration: line-through;
            }
            .diff-replace, .legend-replace {
                background-color: rgba(255, 179, 0, 0.3);
                border: 1px solid rgba(255, 179, 0, 0.8);
            }

            /* 暗色主题微调 */
            body[data-theme="dark"] .diff-add,
            body[data-theme="dark"] .legend-add {
                background-color: rgba(46, 125, 50, 0.5);
            }
            body[data-theme="dark"] .diff-delete,
            body[data-theme="dark"] .legend-delete {
                background-color: rgba(198, 40, 40, 0.5);
            }
            body[data-theme="dark"] .diff-replace,
            body[data-theme="dark"] .legend-replace {
                background-color: rgba(255, 179, 0, 0.5);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- 核心逻辑 (无需改动) ---

def tokenize_text(text: str) -> List[str]:
    """
    将文本分割成单个字符的序列，以实现字符级的精确对比。
    """
    return list(text)


def get_diff_ops(text1: str, text2: str) -> List[Tuple[str, int, int, int, int]]:
    """
    使用difflib和新的分词器计算两段文本的差异操作码。
    """
    matcher = difflib.SequenceMatcher(None, tokenize_text(text1), tokenize_text(text2), autojunk=False)
    return matcher.get_opcodes()


def generate_diff_html(text: str, ops: List[Tuple[str, int, int, int, int]], is_original: bool) -> str:
    """
    根据差异操作码生成用于展示的HTML字符串。
    """
    tokens = tokenize_text(text)
    html_parts = []

    for tag, i1, i2, j1, j2 in ops:
        if is_original:
            segment_tokens = tokens[i1:i2]
            segment_html = "".join(segment_tokens)
            if tag == 'equal':
                html_parts.append(segment_html)
            elif tag == 'delete':
                html_parts.append(f'<span class="diff-delete">{segment_html}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="diff-replace">{segment_html}</span>')
        else:
            segment_tokens = tokens[j1:j2]
            segment_html = "".join(segment_tokens)
            if tag == 'equal':
                html_parts.append(segment_html)
            elif tag == 'insert':
                html_parts.append(f'<span class="diff-add">{segment_html}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="diff-replace">{segment_html}</span>')

    return "".join(html_parts)


# --- UI展示 (已优化) ---

def display_legend():
    """
    在页面上显示标记说明。
    """
    st.subheader("标记说明")
    st.markdown(
        """
        - <span class="legend-add" style="color: black;">荧光绿高亮</span>: 新增的内容
        - <span class="legend-delete" style="color: black;">红色删除线</span>: 被删除的内容
        - <span class="legend-replace" style="color: black;">荧光黄高亮</span>: 被修改的内容
        """,
        unsafe_allow_html=True
    )


def main():
    """
    主函数，构建Streamlit应用界面。
    """
    inject_custom_css()

    st.title("📝 文本对比工具")
    st.caption("输入原文和修改后的文本，快速高亮显示差异之处。\n相关网站：https://www.jyshare.com/front-end/8006/")
    st.divider()

    display_legend()

    # --- 新增：Session State 初始化 ---
    # 使用 session_state 来持久化输入和输出，确保页面切换或刷新后数据不丢失。
    if "original_text" not in st.session_state:
        st.session_state.original_text = "这是第一行。\n这是第二行，内容相同。\n这是将被修改的第三行。"
    if "modified_text" not in st.session_state:
        st.session_state.modified_text = "这是第1行。\n这是第二行，内容不相同。\n这是被修改过的第三行。"
    if "original_diff_html" not in st.session_state:
        st.session_state.original_diff_html = ""
    if "modified_diff_html" not in st.session_state:
        st.session_state.modified_diff_html = ""

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("原文")
        # 使用 key 参数将 text_area 组件与 session_state 自动双向绑定
        st.text_area("输入原始文本", height=300, key="original_text")

    with col2:
        st.subheader("修改后")
        st.text_area("输入修改后的文本", height=300, key="modified_text")

    if st.button("🔍 对比文本", use_container_width=True):
        # 从 session_state 获取最新的文本内容
        original_text = st.session_state.original_text
        modified_text = st.session_state.modified_text

        if original_text and modified_text:
            ops = get_diff_ops(original_text, modified_text)
            # 将计算出的HTML结果也存入 session_state
            st.session_state.original_diff_html = generate_diff_html(original_text, ops, is_original=True)
            st.session_state.modified_diff_html = generate_diff_html(modified_text, ops, is_original=False)
        else:
            # 如果输入为空，则清空之前可能存在的对比结果
            st.session_state.original_diff_html = ""
            st.session_state.modified_diff_html = ""
            st.warning("请输入原文和修改后的文本以便进行对比。")

    # --- 优化：结果展示逻辑 ---
    # 只要 session_state 中有结果，就总是显示它们。
    # 这使得结果在页面重载后依然可见，直到下一次点击按钮或清空输入。
    if st.session_state.original_diff_html and st.session_state.modified_diff_html:
        st.divider()
        st.subheader("对比结果")

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.markdown("#### 原文差异")
            st.markdown(f'<div class="diff-container">{st.session_state.original_diff_html}</div>', unsafe_allow_html=True)

        with res_col2:
            st.markdown("#### 修改后差异")
            st.markdown(f'<div class="diff-container">{st.session_state.modified_diff_html}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()