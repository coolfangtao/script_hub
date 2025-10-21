import streamlit as st
import difflib
from typing import List, Tuple


# --- CSS Styling ---
# 为了确保在不同主题下都有良好的可读性，我们为高亮效果定义了独立的CSS样式。
# 使用st.markdown来注入CSS。
def inject_custom_css():
    """
    注入自定义CSS样式，以美化差异化文本的展示效果，并兼容亮暗两种主题。
    """
    st.markdown(
        """
        <style>
            .diff-container {
                display: flex;
                flex-wrap: wrap;
                font-family: 'Courier New', Courier, monospace;
                line-height: 1.6;
            }
            .diff-container span {
                padding: 0.1em 0.2em;
                margin: 0.1em 0;
                border-radius: 0.3em;
            }
            .diff-add {
                background-color: rgba(46, 125, 50, 0.3); /* 荧光绿，增加透明度 */
                border: 1px solid rgba(46, 125, 50, 0.8);
            }
            .diff-delete {
                background-color: rgba(198, 40, 40, 0.3); /* 红色，增加透明度 */
                border: 1px solid rgba(198, 40, 40, 0.8);
                text-decoration: line-through;
            }
            .diff-replace {
                background-color: rgba(255, 179, 0, 0.3); /* 荧光黄，增加透明度 */
                border: 1px solid rgba(255, 179, 0, 0.8);
            }

            /* 针对Streamlit暗色主题的微调 */
            body[data-theme="dark"] .diff-add {
                background-color: rgba(46, 125, 50, 0.5);
            }
            body[data-theme="dark"] .diff-delete {
                background-color: rgba(198, 40, 40, 0.5);
            }
            body[data-theme="dark"] .diff-replace {
                background-color: rgba(255, 179, 0, 0.5);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- 核心逻辑 ---
# 这部分代码负责计算文本差异，并且与Streamlit的UI代码解耦。

def get_diff_ops(text1: str, text2: str) -> List[Tuple[str, int, int, int, int]]:
    """
    使用difflib计算两段文本的差异操作码。

    Args:
        text1: 原文。
        text2: 修改后的文本。

    Returns:
        一个包含差异操作码的列表。
    """
    matcher = difflib.SequenceMatcher(None, text1.split(), text2.split())
    return matcher.get_opcodes()


def generate_diff_html(text: str, ops: List[Tuple[str, int, int, int, int]], is_original: bool) -> str:
    """
    根据差异操作码生成用于展示的HTML字符串。

    Args:
        text: 要处理的文本（原文或修改后的文本）。
        ops: difflib生成的差异操作码。
        is_original: 布尔值，如果为True，则处理原文；否则处理修改后的文本。

    Returns:
        一个包含高亮标记的HTML字符串。
    """
    words = text.split()
    html_parts = []

    for tag, i1, i2, j1, j2 in ops:
        if is_original:
            segment = words[i1:i2]
            if tag == 'equal':
                html_parts.append(' '.join(segment))
            elif tag == 'delete':
                html_parts.append(f'<span class="diff-delete">{" ".join(segment)}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="diff-replace">{" ".join(segment)}</span>')
        else:
            segment = words[j1:j2]
            if tag == 'equal':
                html_parts.append(' '.join(segment))
            elif tag == 'insert':
                html_parts.append(f'<span class="diff-add">{" ".join(segment)}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="diff-replace">{" ".join(segment)}</span>')

    # 用一个空格连接所有部分，并处理连续空格，以保留原始格式
    return ' '.join(html_parts).replace(' \n ', '\n')


# --- Streamlit UI ---
# 这部分代码负责构建网页界面。

def main():
    """
    主函数，构建Streamlit应用界面。
    """
    st.set_page_config(page_title="文本对比工具", layout="wide")
    inject_custom_css()

    st.title("📝 文本对比工具")
    st.caption("输入原文和修改后的文本，快速高亮显示差异之处。")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("原文")
        original_text = st.text_area(
            "输入原始文本",
            height=300,
            key="original",
            value="Streamlit is an open-source Python library that makes it easy to create and share beautiful, custom web apps for machine learning and data science."
        )

    with col2:
        st.subheader("修改后")
        modified_text = st.text_area(
            "输入修改后的文本",
            height=300,
            key="modified",
            value="Streamlit is a great open-source library that makes it simple to build and share powerful web apps for data science."
        )

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