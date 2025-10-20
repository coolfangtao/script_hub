# 文件路径: streamlit_app.py

import streamlit as st
from shared.sidebar import create_common_sidebar  # 导入我们创建的侧边栏函数
from shared.changelog import show_changelog
from shared.feedback import setup_database, show_feedback_module
from shared.elements import shin_chan_animation  # 导入我们的动画函数

# --- 1. 显示顶部动画 (默认效果) ---
# 只需调用这一行函数，所有复杂的HTML/CSS代码都已封装好
shin_chan_animation()

# --- 渲染侧边栏 ---
# 这一行代码会负责搞定所有侧边栏的显示逻辑
create_common_sidebar()


# --- 页面基础设置 (必须是第一个st命令) ---
st.set_page_config(
    page_title="FT的脚本中心",
    page_icon="🚀",
    layout="wide"
)

# --- 初始化数据库 ---
# 在应用启动时，确保反馈表已经创建
setup_database()

# import streamlit.components.v1 as components
# from shared.particles_component import particles_js_code
# # --- 1. 注入自定义CSS，让Streamlit的背景变透明 ---
# # 使用 st.markdown 来插入 HTML 和 CSS
# # [data-testid="stAppViewContainer"] 是 Streamlit 应用的主容器
# # [data-testid="stHeader"] 是顶部的 Header
# custom_css = """
# <style>
#     /* 让主应用容器和顶栏的背景都变成透明 */
#     [data-testid="stAppViewContainer"],
#     [data-testid="stHeader"] {
#         background: transparent;
#     }
#
#     /* 如果你需要，也可以让侧边栏透明 (可选) */
#     /*
#     [data-testid="stSidebar"] {
#         background: transparent;
#     }
#     */
# </style>
# """
# st.markdown(custom_css, unsafe_allow_html=True)
# # --- 2. 渲染粒子动画HTML组件 ---
# # 这会将 id="particles-js" 的 div 插入到页面中
# # 由于它的 CSS 设置了 position: fixed 和 z-index: -1，它会自动铺满整个背景
# components.html(particles_js_code, height=200, scrolling=False)

# =====================================================================
# --- 新的主页内容 ---
# =====================================================================

# --- 1. 欢迎横幅 ---
st.title("🚀 欢迎来到 FT 的脚本中心")
st.markdown("一个集成了运营维护、文本处理和图像处理等多种高效工具的在线平台。")
st.markdown("⬅️左侧打开即可使用。")
st.markdown("---")

# --- 3. 核心功能 & 快速入口 ---
st.header("🌟 核心功能一览")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>🤖</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>AI工具</h5>", unsafe_allow_html=True)
        st.write("与强大的 AI 模型进行对话，无需特殊网络环境即可体验 Gemini 2.5 Pro。")
        if st.button("立即开始", key="ai", use_container_width=True):
            st.switch_page(r"pages/7_AI_对话页面.py")

with col2:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>📊</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>关键词分析</h5>", unsafe_allow_html=True)
        st.write("一键对多个ASIN的关键词分析Excel文件进行合并和分析，方便后续分析。")
        if st.button("立即开始", key="merge_asin", use_container_width=True):
            st.switch_page(r"pages/2_关键词统计.py")

with col3:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>🖼️</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>智能替换背景</h5>", unsafe_allow_html=True)
        st.write("上传产品图，自动移除并替换为指定的纯色或场景背景，提升图片质量。")
        if st.button("立即开始", key="remove_bg", use_container_width=True):
            st.switch_page(r"pages/5_替换图片背景.py")

with col4:
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center;'>🔊</h3>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center;'>文字转语音</h5>", unsafe_allow_html=True)
        st.write("输入任意文本，选择多种音色，快速生成高质量的语音文件，支持多语言。")
        if st.button("立即开始", key="tts", use_container_width=True):
            st.switch_page(r"pages/3_文字转语音.py")

st.markdown("---")

# --- 4. 更新日志 ---
show_changelog()
st.markdown("---")

# --- 5. 联系与反馈 ---
# 只需调用这一个函数，即可显示整个反馈模块（包括输入表单和历史记录）
show_feedback_module()
st.markdown("---")

# --- 5. 友情链接 ---
st.header("🔗 友情链接")
st.write("发现更多有用的工具和资源。")
# 使用列表和字典来管理链接，未来增删链接只需修改这里
FRIENDLY_LINKS = [
    {
        "title": "PDF24 Tools: 免费且易于使用的在线PDF工具",
        "url": "https://tools.pdf24.org/zh/",
        "description": "PDF24 Tools: 免费且易于使用的在线PDF工具"
    },
    {
        "title": "imagesTool，无需上传文件也可在线处理图片，可以图片转换、拼接、裁剪、压缩、加水印，GIF 压缩、提取、转换等，功能非常齐全。",
        "url": "https://imagestool.com/zh_CN/",
        "description": "菜鸟工具 - 不止于工具"
    },
    {
        "title": "格式转换（图片/视频/音频等）",
        "url": "https://www.aconvert.com/cn/",
        "description": "菜鸟工具 - 不止于工具"
    },
    {
        "title": "菜鸟工具 - 不止于工具",
        "url": "https://www.jyshare.com/",
        "description": "菜鸟工具 - 不止于工具"
    },
    {
        "title": "MikuTools - 一个轻量的工具集合",
        "url": "https://tools.miku.ac/",
        "description": "菜鸟工具 - 不止于工具"
    },
    {
        "title": "图像无损放大",
        "url": "https://www.waifu2x.net/",
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
        © 2025 FT的脚本中心 | ✉️ 邮箱：morebetter2025@163.com
    </p>
    """,
    unsafe_allow_html=True
)