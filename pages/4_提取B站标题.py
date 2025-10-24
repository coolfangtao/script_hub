import streamlit as st
import re
from shared.sidebar import create_common_sidebar

# --- 1. 页面配置 (建议放在脚本顶部) ---
st.set_page_config(
    page_title="B站标题提取工具",
    page_icon="📌",
    layout="wide"
)

# --- 2. 初始化 Session State ---
# 这是实现数据持久化的关键。
# st.session_state 是一个类似字典的对象，在用户的整个会话期间保持不变。
# 我们在这里为该页面需要用到的变量进行初始化，防止首次运行时出错。

# 'bili_html_input' 用于存储用户在文本框中粘贴的HTML内容
if 'bili_html_input' not in st.session_state:
    st.session_state.bili_html_input = ""

# 'bili_extracted_titles' 用于存储提取出的标题列表
if 'bili_extracted_titles' not in st.session_state:
    st.session_state.bili_extracted_titles = None  # 初始设为None，表示还未提取过


# --- 3. 核心功能函数 ---
@st.cache_data  # 使用缓存装饰器，对于相同的输入，函数会直接返回缓存结果，提高效率
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

    # 精确匹配 title="..." 属性，且其后紧跟着 class="title"
    precise_regex = r'title="([^"]+)"\s+class="title"'
    return re.findall(precise_regex, html_content)


# --- 4. 回调函数 (Callback) ---
# 当点击按钮时，我们不再把逻辑直接写在按钮的 if 判断里，
# 而是通过一个回调函数来更新 session_state。这样做更符合Streamlit的最佳实践。
def run_extraction():
    """
    执行提取逻辑并把结果存入 session_state。
    """
    if st.session_state.bili_html_input and st.session_state.bili_html_input.strip():
        # 如果输入不为空，则调用函数提取标题
        titles = extract_titles(st.session_state.bili_html_input)
        st.session_state.bili_extracted_titles = titles
        if titles:
            st.balloons()  # 提取成功时放个气球庆祝一下
    else:
        # 如果输入为空，则将结果设置为空列表，用于后续显示警告
        st.session_state.bili_extracted_titles = []


# --- 5. 侧边栏 ---
try:
    create_common_sidebar()
except Exception as e:
    st.sidebar.error(f"加载侧边栏失败: {e}")

# --- 6. 主界面UI ---

# 页面主标题
st.title("📌 B站标题提取工具")
st.caption("一个简单的小工具，用于从 Bilibili 播放列表等页面的 HTML 源码中批量提取视频标题。")

# 使用可折叠容器来组织输入区域
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
        key='bili_html_input',  # 将这个组件的值与 session_state 中的 'bili_html_input' 键绑定
        label_visibility="collapsed"
    )

# 提取按钮，点击时调用 run_extraction 回调函数
st.button(
    "🚀 开始提取",
    type="primary",
    use_container_width=True,
    on_click=run_extraction  # 绑定回调函数
)

# --- 7. 结果展示 ---
# 这部分逻辑不再依赖于按钮是否被点击，而是直接依赖 session_state 的状态。
# 只要 st.session_state.bili_extracted_titles 不是初始的 None，就说明用户已经进行过提取操作。
if st.session_state.bili_extracted_titles is not None:
    st.header("第二步：复制提取结果")

    # 获取缓存的结果
    titles = st.session_state.bili_extracted_titles

    if titles:
        # 将结果列表转换为以换行符分隔的字符串
        result_text = "\n".join(titles)
        st.code(result_text, language='text')
        st.success(f"🎉 成功提取了 {len(titles)} 个标题！点击上方结果框右上角的图标即可一键复制。")
    elif isinstance(titles, list) and len(titles) == 0:
        # `isinstance` 判断用于区分 "从未提取过(None)" 和 "提取了但没结果([])"
        st.error("❌ 未找到任何标题。请确认您复制的是完整的HTML源代码，并且其中包含 `title=\"...\" class=\"title\"` 格式的内容。")