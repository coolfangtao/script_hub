# 文件路径: streamlit_app.py

import streamlit as st
from shared.sidebar import create_common_sidebar
from shared.update_log import show_changelog
from shared.feedback import setup_database, show_feedback_module
# from shared.usage_tracker import usage_tracker

# --- 页面基础设置 (必须是第一个st命令) ---
st.set_page_config(
    page_title="FT的脚本中心",
    page_icon="🚀",
    layout="wide"
)

# --- 静态常量定义 ---
# 将不常变动的数据（如链接）统一管理，方便维护
FRIENDLY_LINKS = [
    {
        "title": "PDF24 Tools: 免费且易于使用的在线PDF工具",
        "url": "https://tools.pdf24.org/zh/"
    },
    {
        "title": "imagesTool: 在线图片处理工具集",
        "url": "https://imagestool.com/zh_CN/"
    },
    {
        "title": "AConvert: 免费在线文件格式转换",
        "url": "https://www.aconvert.com/cn/"
    },
    {
        "title": "菜鸟工具: 不止于工具",
        "url": "https://www.jyshare.com/"
    },
    {
        "title": "MikuTools: 一个轻量的工具集合",
        "url": "https://tools.miku.ac/"
    },
    {
        "title": "Waifu2x: 图像无损放大",
        "url": "https://www.waifu2x.net/"
    },
    {
        "title": "GD音乐台: GD Studio's Online Music Platform",
        "url": "https://music.gdstudio.org/"
    }
]


# --- 页面核心功能函数 ---

def create_feature_card(icon, title, description, button_key, target_page):
    """创建一个标准的功能展示卡片。"""
    with st.container(border=True):
        st.markdown(f"<h3 style='text-align: center;'>{icon}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='text-align: center;'>{title}</h5>", unsafe_allow_html=True)
        st.write(description)
        if st.button("立即开始", key=button_key, use_container_width=True):
            st.switch_page(target_page)


def display_welcome_banner():
    """显示页面的欢迎横幅。"""
    st.title("🚀 欢迎来到 TF 的脚本中心")
    st.markdown("一个集成了运营维护、文本处理和图像处理等多种高效工具的在线平台。")
    # --- 新增的座右铭 ---
    # 使用 Markdown 和一点 HTML/CSS 来美化样式，使其居中、斜体并带有灰色调
    st.markdown(
        """
        <p style='text-align: center; font-style: italic; color: #888;'>
            做难事必有所得，在混乱中创造秩序。
        </p>
        """,
        unsafe_allow_html=True
    )
    # --- 座右铭结束 ---
    st.markdown("⬅️ 请从左侧侧边栏选择一个工具开始使用。")
    st.divider()


def display_core_features():
    """显示核心功能模块。"""
    st.header("🌟 核心功能一览")

    # 定义功能卡片的数据
    features = [
        {"icon": "📋", "title": "任务看板", "description": "高效记录并管理日常任务，清晰掌握工作进度，提升个人时间管理效率。", "key": "task_board",
         "page": r"pages/0_任务看板.py"},
        {"icon": "📝", "title": "文本对比", "description": "快速比对两个文本内容的差异，直观显示修改位置，轻松找出变动之处。", "key": "text_compare",
         "page": r"pages/4_文本对比.py"},
        {"icon": "🖼️", "title": "生成图片在线地址", "description": "上传本地图片，一键生成可分享的在线访问链接，方便快捷地获取图片网络地址。", "key": "image_url",
         "page": r"pages/6_生成图片在线地址.py"},
        {"icon": "🎬", "title": "B站标题提取", "description": "输入B站视频链接，自动提取页面中视频合集的所有标题内容，支持批量导出。", "key": "bilibili_title",
         "page": r"pages/4_提取B站标题.py"}
    ]

    cols = st.columns(len(features))
    for i, feature in enumerate(features):
        with cols[i]:
            create_feature_card(
                icon=feature["icon"],
                title=feature["title"],
                description=feature["description"],
                button_key=feature["key"],
                target_page=feature["page"]
            )
    st.divider()


def display_friendly_links():
    """显示友情链接模块。"""
    st.header("🔗 友情链接")
    st.write("发现更多有用的工具和资源。")

    for link in FRIENDLY_LINKS:
        with st.container(border=True):
            st.markdown(f"##### {link['title']}")
            st.link_button("前往查看 →", link['url'])
    st.divider()


def display_footer():
    """显示页脚信息。"""
    st.markdown(
        """
        <p style='text-align: center; color: grey;'>
            © 2025 TF的脚本中心 | ✉️ 邮箱：morebetter2025@163.com
        </p>
        """,
        unsafe_allow_html=True
    )


def main():
    """
    应用主函数，负责渲染整个页面。
    """
    # --- 1. 渲染侧边栏和初始化 ---
    create_common_sidebar()
    setup_database()

    # --- 2. 页面主体内容渲染 ---
    display_welcome_banner()
    display_core_features()
    # show_global_usage_stats()

    # 更新日志
    show_changelog()
    st.divider()

    # 反馈模块
    show_feedback_module()
    st.divider()

    display_friendly_links()
    display_footer()


# --- 程序入口 ---
if __name__ == "__main__":
    main()