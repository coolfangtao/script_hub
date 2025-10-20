# 文件路径: streamlit_app.py

import streamlit as st
from shared.sidebar import create_common_sidebar  # 导入我们创建的侧边栏函数
from shared.changelog import show_changelog
# from shared.feedback import render_feedback_section # <-- 1. 导入新的反馈函数

# --- 页面基础设置 (必须是第一个st命令) ---
st.set_page_config(
    page_title="FT的脚本中心",
    page_icon="🚀",
    layout="wide"
)

# --- 渲染侧边栏 ---
# 这一行代码会负责搞定所有侧边栏的显示逻辑
create_common_sidebar()

# =====================================================================
# --- 新的主页内容 ---
# =====================================================================

# --- 1. 欢迎横幅 ---
st.title("🚀 欢迎来到 FT 的脚本中心")
st.markdown("一个集成了运营维护、文本处理和图像处理等多种高效工具的在线平台。")
st.markdown("---")

# --- 2. 如何使用 ---
st.subheader("💡 如何使用")
st.write("只需三步，轻松上手：")

how_col1, how_col2, how_col3 = st.columns(3)
with how_col1:
    with st.container(border=True, height=150):
        st.markdown("<div style='text-align: center;'><h3>① 选择工具</h3><p>从左侧的侧边栏选择您需要的功能。</p></div>", unsafe_allow_html=True)
with how_col2:
    with st.container(border=True, height=150):
        st.markdown("<div style='text-align: center;'><h3>② 上传文件</h3><p>根据页面提示上传您的文件或输入信息。</p></div>", unsafe_allow_html=True)
with how_col3:
    with st.container(border=True, height=150):
        st.markdown("<div style='text-align: center;'><h3>③ 获取结果</h3><p>点击执行按钮，立即获得处理好的结果。</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 3. 核心功能 & 快速入口 ---
st.subheader("🌟 核心功能一览")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>📊</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>关键词分析</h5>", unsafe_allow_html=True)
        st.write("一键对多个ASIN的关键词分析Excel文件进行合并和分析，方便后续分析。")
        if st.button("立即开始", key="merge_asin", use_container_width=True):
            st.switch_page(r"pages/2_关键词统计.py")

with col2:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>🖼️</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>智能替换背景</h5>", unsafe_allow_html=True)
        st.write("上传产品图，自动移除并替换为指定的纯色或场景背景，提升图片质量。")
        if st.button("立即开始", key="remove_bg", use_container_width=True):
            st.switch_page(r"pages/5_替换图片背景.py")

with col3:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>🔊</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>文字转语音</h5>", unsafe_allow_html=True)
        st.write("输入任意文本，选择多种音色，快速生成高质量的语音文件，支持多语言。")
        if st.button("立即开始", key="tts", use_container_width=True):
            st.switch_page(r"pages/3_文字转语音.py")

with col4:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>🤖</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>AI工具</h5>", unsafe_allow_html=True)
        st.write("与强大的 AI 模型进行对话，无需特殊网络环境即可体验 Gemini 2.5 Pro。")
        if st.button("立即开始", key="ai", use_container_width=True):
            st.switch_page(r"pages/7_AI_对话页面.py")

st.markdown("---")

# --- 4. 更新日志 ---
show_changelog()
st.markdown("---")

# --- 5. 联系与反馈 ---
# render_feedback_section() # <-- 2. 在这里调用函数

# --- 5. 友情链接 ---
st.subheader("🔗 友情链接")
st.write("发现更多有用的工具和资源。")

# 使用列表和字典来管理链接，未来增删链接只需修改这里
FRIENDLY_LINKS = [
    {
        "title": "PDF24 Tools: 免费且易于使用的在线PDF工具",
        "url": "https://tools.pdf24.org/zh/",
        "description": "PDF24 Tools: 免费且易于使用的在线PDF工具"
    },
    {
        "title": "菜鸟工具 - 不止于工具",
        "url": "https://www.jyshare.com/",
        "description": "菜鸟工具 - 不止于工具"
    },
    {
        "title": "GD音乐台 - GD Studio's Online Music Platform",
        "url": "https://music.gdstudio.org/",
        "description": "GD音乐台 - GD Studio's Online Music Platform"
    }
]

# 遍历列表，为每个链接创建一个独立的容器
for link in FRIENDLY_LINKS:
    with st.container(border=True):
        st.markdown(f"##### {link['title']}")
        # st.write(link['description'])
        # 使用 st.link_button 创建一个更美观的跳转按钮
        st.link_button("前往查看 →", link['url'])

st.markdown("---")

# --- 6. 页脚 ---
st.markdown(
    """
    <p style='text-align: center; color: grey;'>
        © 2025 FT的脚本中心 | ✉️ 邮箱：19210860039@fudan.edu.cn
    </p>
    """,
    unsafe_allow_html=True
)