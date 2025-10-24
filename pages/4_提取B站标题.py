import streamlit as st
from bs4 import BeautifulSoup  # 导入新库
from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="B站标题提取工具",
    page_icon="📌",
    layout="wide"
)

# --- 2. 初始化 Session State ---
if 'bili_html_input' not in st.session_state:
    st.session_state.bili_html_input = ""
if 'bili_extracted_titles' not in st.session_state:
    st.session_state.bili_extracted_titles = None

# --- 3. 核心功能函数 (已优化) ---
@st.cache_data
def extract_titles(html_content: str) -> list[str]:
    """
    使用 BeautifulSoup 解析HTML，精确提取 class="title" 的 div 标签中的 title 属性。

    Args:
        html_content: 包含HTML的字符串。

    Returns:
        一个包含所有匹配到的标题的列表。
    """
    if not html_content:
        return []

    # ===================================================================
    # 使用 BeautifulSoup 进行精确解析
    # 1. 创建 BeautifulSoup 对象，使用 'lxml' 解析器（速度快）
    soup = BeautifulSoup(html_content, 'lxml')

    # 2. 查找所有 <div> 标签，这些标签必须同时满足 class="title" 的条件
    #    注意：class 是Python的关键字，所以 beautifulsoup 用 class_ 来代替
    title_elements = soup.find_all('div', class_='title')

    # 3. 从找到的元素中提取 'title' 属性的值。
    #    使用 .get('title') 是一个安全的做法，如果某个标签没有title属性，会返回None。
    #    最后的 if tag.get('title') 确保我们只添加非空的标题。
    titles = [
        tag['title'] for tag in title_elements if tag.get('title')
    ]
    # ===================================================================

    return titles


# --- 4. 回调函数 ---
def run_extraction():
    """
    执行提取逻辑并把结果存入 session_state。
    """
    if st.session_state.bili_html_input and st.session_state.bili_html_input.strip():
        titles = extract_titles(st.session_state.bili_html_input)
        st.session_state.bili_extracted_titles = titles
        if titles:
            st.balloons()
    else:
        st.session_state.bili_extracted_titles = []


# --- 5. 侧边栏 ---
try:
    # track_script_usage("🎬 B站标题")
    create_common_sidebar()
except Exception as e:
    st.sidebar.error(f"加载侧边栏失败: {e}")

# --- 6. 主界面UI ---
st.title("📌 B站标题提取工具")
st.caption("一个简单的小工具，用于从 Bilibili 播放列表等页面的 HTML 源码中批量提取视频标题。")

with st.expander("第一步：粘贴HTML内容", expanded=True):
    st.markdown("""
    1. 在B站的播放列表页面（或其他需要提取标题的页面），右键点击页面空白处。
    2. 选择 **“显示网页源代码”** (View Page Source) 或 **“检查”** (Inspect)。
    3. **全选 (Ctrl+A)** 并 **复制 (Ctrl+C)** 源代码。
    4. 将复制的内容粘贴到下方的文本框中。
    """)
    st.text_area(
        "在此处粘贴HTML源代码...",
        height=300,
        key='bili_html_input',
        label_visibility="collapsed"
    )

st.button(
    "🚀 开始提取",
    type="primary",
    use_container_width=True,
    on_click=run_extraction
)

# --- 7. 结果展示 ---
if st.session_state.bili_extracted_titles is not None:
    st.header("第二步：复制提取结果")
    titles = st.session_state.bili_extracted_titles
    if titles:
        result_text = "\n".join(titles)
        st.code(result_text, language='text')
        st.success(f"🎉 成功提取了 {len(titles)} 个标题！点击上方结果框右上角的图标即可一键复制。")
    elif isinstance(titles, list) and len(titles) == 0:
        st.error("❌ 未找到任何标题。请确认您复制的是完整的HTML源代码，并且其中包含带有 `title` 属性和 `class=\"title\"` 的 `<div>` 标签。")