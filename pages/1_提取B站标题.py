import streamlit as st
import re
from shared.sidebar import create_common_sidebar

# --- 1. 页面配置 (建议放在脚本顶部) ---
st.set_page_config(
    page_title="B站标题提取工具",
    page_icon="📌"
)

# --- 2. 核心功能函数 ---
def extract_titles(html_content: str) -> list[str]:
    """
    使用更精确的正则表达式，仅从包含 class="title" 的标签中提取 title 内容。

    Args:
        html_content: 包含HTML的字符串。

    Returns:
        一个包含所有匹配到的标题的列表。
    """
    if not html_content:
        return []

    # ===================================================================
    # 更新后的正则表达式：
    # 它会查找一个 title="..." 属性，并且这个属性后面必须跟着 class="title"。
    # 这确保了我们只捕获视频列表项的标题，而忽略其他无关的title。
    # ===================================================================
    precise_regex = r'title="([^"]+)"\s+class="title"'

    return re.findall(precise_regex, html_content)

# --- 3. 侧边栏 ---
try:
    create_common_sidebar()
except Exception as e:
    st.sidebar.error(f"加载侧边栏失败: {e}")


# --- 4. 主界面UI ---

# 页面主标题
st.title("📌 B站标题提取工具")
st.caption("一个简单的小工具，用于从 Bilibili 播放列表等页面的 HTML 源码中批量提取视频标题。")

# 使用可折叠容器来组织输入区域，使界面更整洁
with st.expander("第一步：粘贴HTML内容", expanded=True):
    st.markdown("""
    1. 在B站的播放列表页面（或其他需要提取标题的页面），右键点击页面空白处。
    2. 选择 **“显示网页源代码”** (View Page Source) 或 **“检查”** (Inspect)。
    3. **全选 (Ctrl+A)** 并 **复制 (Ctrl+C)** 源代码。
    4. 将复制的内容粘贴到下方的文本框中。
    """)
    html_input = st.text_area(
        "在此处粘贴HTML源代码...",
        height=300,
        label_visibility="collapsed"
    )

# 提取按钮和结果展示
if st.button("🚀 开始提取", type="primary", use_container_width=True):
    if not html_input.strip():
        # 检查输入是否为空或仅包含空白字符
        st.warning("⚠️ 请先粘贴HTML内容再进行提取。")
    else:
        # 调用函数执行提取逻辑
        titles = extract_titles(html_input)

        st.header("第二步：复制提取结果")

        if titles:
            # 将结果列表转换为以换行符分隔的字符串
            result_text = "\n".join(titles)

            # st.code 自带复制按钮，非常适合展示结果
            st.code(result_text, language='text')

            # 显示成功信息
            st.success(f"🎉 成功提取了 {len(titles)} 个标题！点击上方结果框右上角的图标即可一键复制。")
        else:
            # 如果没有找到任何标题，显示提示信息
            st.error("❌ 未找到任何标题。请确认您复制的是完整的HTML源代码，并且其中包含 `title=\"...\"` 格式的内容。")