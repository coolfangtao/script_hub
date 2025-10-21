import streamlit as st
import difflib
import re
from typing import List, Tuple
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数
create_common_sidebar()


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


# --- 核心逻辑 (Bug已修复) ---

def tokenize_text(text: str) -> List[str]:
    """
    【修复】将文本分割成单个字符的序列，以实现字符级的精确对比。
    这对于处理中文、日文等无空格语言至关重要。
    """
    return list(text)


def get_diff_ops(text1: str, text2: str) -> List[Tuple[str, int, int, int, int]]:
    """
    使用difflib和新的分词器计算两段文本的差异操作码。
    """
    # 使用修复后的分词器
    matcher = difflib.SequenceMatcher(None, tokenize_text(text1), tokenize_text(text2), autojunk=False)
    return matcher.get_opcodes()


def generate_diff_html(text: str, ops: List[Tuple[str, int, int, int, int]], is_original: bool) -> str:
    """
    根据差异操作码生成用于展示的HTML字符串。
    此函数无需改动，因为它能正确处理字符列表。
    """
    tokens = tokenize_text(text)
    html_parts = []

    for tag, i1, i2, j1, j2 in ops:
        if is_original:
            # 获取原文的字符片段并用span包裹
            segment_tokens = tokens[i1:i2]
            segment_html = "".join(segment_tokens)
            if tag == 'equal':
                html_parts.append(segment_html)
            elif tag == 'delete':
                html_parts.append(f'<span class="diff-delete">{segment_html}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="diff-replace">{segment_html}</span>')
        else:
            # 获取修改后文本的字符片段并用span包裹
            segment_tokens = tokens[j1:j2]
            segment_html = "".join(segment_tokens)
            if tag == 'equal':
                html_parts.append(segment_html)
            elif tag == 'insert':
                html_parts.append(f'<span class="diff-add">{segment_html}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="diff-replace">{segment_html}</span>')

    return "".join(html_parts)


# --- UI展示 (无需改动) ---

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
    st.set_page_config(page_title="文本对比工具", layout="wide")
    inject_custom_css()

    st.title("📝 文本对比工具")
    st.caption("输入原文和修改后的文本，快速高亮显示差异之处。\n相关网站：https://www.jyshare.com/front-end/8006/")
    st.divider()

    display_legend()

    # 使用一个更能体现字符级差异的示例文本
    sample_original = "这是第一行。\n这是第二行，内容相同。\n这是将被修改的第三行。"
    sample_modified = "这是第1行。\n这是第二行，内容不相同。\n这是被修改过的第三行。"

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("原文")
        original_text = st.text_area("输入原始文本", height=300, key="original", value=sample_original)

    with col2:
        st.subheader("修改后")
        modified_text = st.text_area("输入修改后的文本", height=300, key="modified", value=sample_modified)

    if st.button("🔍 对比文本", use_container_width=True):
        if original_text and modified_text:
            ops = get_diff_ops(original_text, modified_text)

            st.divider()
            st.subheader("对比结果")

            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.markdown("#### 原文差异")
                original_diff_html = generate_diff_html(original_text, ops, is_original=True)
                st.markdown(f'<div class="diff-container">{original_diff_html}</div>', unsafe_allow_html=True)

            with res_col2:
                st.markdown("#### 修改后差异")
                modified_diff_html = generate_diff_html(modified_text, ops, is_original=False)
                st.markdown(f'<div class="diff-container">{modified_diff_html}</div>', unsafe_allow_html=True)
        else:
            st.warning("请输入原文和修改后的文本以便进行对比。")


if __name__ == "__main__":
    main()