import streamlit as st
from shared.sidebar import create_common_sidebar
from shared.changelog import show_changelog
from shared.feedback import setup_database, show_feedback_module
# --- 新增导入 ---
from shared.auth import init_db, show_auth_page

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
    st.title("🚀 欢迎来到 FT 的脚本中心")
    st.markdown("一个集成了运营维护、文本处理和图像处理等多种高效工具的在线平台。")
    st.markdown("⬅️ 请从左侧侧边栏选择一个工具开始使用。")
    st.divider()


def display_core_features():
    """显示核心功能模块。"""
    st.header("🌟 核心功能一览")

    # 定义功能卡片的数据
    features = [
        {"icon": "🤖", "title": "AI工具", "description": "与强大的 AI 模型进行对话，无需特殊网络环境即可体验 Gemini 2.5 Pro。", "key": "ai",
         "page": r"pages/7_AI_对话页面.py"},
        {"icon": "📊", "title": "关键词分析", "description": "一键对多个ASIN的关键词分析Excel文件进行合并和分析，方便后续分析。", "key": "merge_asin",
         "page": r"pages/2_关键词统计.py"},
        {"icon": "🖼️", "title": "智能替换背景", "description": "上传产品图，自动移除并替换为指定的纯色或场景背景，提升图片质量。", "key": "remove_bg",
         "page": r"pages/5_替换图片背景.py"},
        {"icon": "🔊", "title": "文字转语音", "description": "输入任意文本，选择多种音色，快速生成高质量的语音文件，支持多语言。", "key": "tts",
         "page": r"pages/3_文字转语音.py"}
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
            © 2025 FT的脚本中心 | ✉️ 邮箱：morebetter2025@163.com
        </p>
        """,
        unsafe_allow_html=True
    )


def render_main_app():
    """
    应用主函数，负责渲染整个页面。 (这是你之前的 main 函数)
    """
    # --- 1. 渲染侧边栏和初始化 ---
    create_common_sidebar()
    setup_database() # 用于 feedback 的数据库

    # 在侧边栏添加欢迎和登出按钮
    st.sidebar.divider()
    st.sidebar.success(f"欢迎, {st.session_state['username']}!")
    if st.sidebar.button("登出"):
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None) # 安全地移除用户名
        st.rerun()

    # --- 2. 页面主体内容渲染 ---
    display_welcome_banner()
    display_core_features()

    # 更新日志
    show_changelog()
    st.divider()

    # 反馈模块
    show_feedback_module()
    st.divider()

    display_friendly_links()
    display_footer()


def main():
    """
    新的主函数，作为程序的总入口，控制认证流程。
    """
    # 初始化用户数据库
    init_db()

    # 检查 session_state 中 'logged_in' 的状态
    # get 方法提供一个默认值 False，避免第一次运行时出错
    if st.session_state.get('logged_in', False):
        # 如果用户已登录，渲染主应用
        render_main_app()
    else:
        # 如果用户未登录，显示认证页面
        show_auth_page()


# --- 程序入口 ---
if __name__ == "__main__":
    main()