# 文件路径: shared/sidebar.py
import streamlit as st
from shared.elements import shin_chan_animation
from shared.usage_tracker import track_page_visit
import os

# --- 核心数据结构: 统一管理所有脚本和分组 ---
SCRIPTS_BY_GROUP = {
    "🤖 AI工具": [
        {
            "label": "💬 AI对话",
            "path": r"pages/7_AI_对话页面.py"
        },
        # {
        #     "label": "🎵 语句分析（已废弃）",
        #     "path": r"pages/3_英语句子语音现象分析.py"
        # },
        {
            "label": "🎵 音变分析",
            "path": r"pages/3_音变分析.py"
        },
        {
            "label": "📈 杂质统计",
            "path": r"pages/8_杂质统计.py"
        },
    ],
    "📊 运营工具": [
        {
            "label": "🔍 关键词统计",
            "path": r"pages/2_关键词统计.py"
        },
        {
            "label": "📝 Listing生成",
            "path": r"pages/2_Listing生成.py"
        },
        {
            "label": "✅ 任务看板",
            "path": r"pages/0_任务看板.py"
        },
        {
            "label": "🛍️ 商品信息提取",
            "path": r"pages/4_一键提取亚马逊页面关键信息.py"
        },
        # {
        #     "label": "👬 群成员名称提取",
        #     "path": r"pages/4_提取掌上大学群成员名称.py"
        # },
        {
            "label": "📦 商品信息提取（完整版）",
            "path": r"pages/2_Amazon评论获取.py"
        },
        {
            "label": "🕸️ 浏览器抓取编排",
            "path": r"pages/4_网页元素梳理.py"
        },
    ],
    "📝 文本处理": [
        {
            "label": "🎬 B站标题提取",
            "path": r"pages/4_提取B站标题.py"
        },
        {
            "label": "📚 读书笔记转换",
            "path": r"pages/4_读书笔记转markdown文档.py"
        },
        {
            "label": "🔊 文字转语音",
            "path": r"pages/3_文本转语音.py"
        },
        {
            "label": "📄 文本对比",
            "path": r"pages/4_文本对比.py"
        },
        {
            "label": "🧹 去除空行",
            "path": r"pages/4_去除空白行.py"
        },
    ],
    "🖼️ 图像处理": [
        {
            "label": "🎨 替换背景",
            "path": r"pages/5_替换图片背景.py"
        },
        {
            "label": "📦 图像压缩",
            "path": r"pages/6_图像压缩.py"
        },
        {
            "label": "🌐 图片翻译",
            "path": r"pages/6_图片翻译.py"
        },
        {
            "label": "🔗 在线图床",
            "path": r"pages/6_生成图片在线地址.py"
        },
    ],
    "🧩 其他工具": [
        {
            "label": "📈 基金盯盘",
            "path": r"pages/8_基金涨跌.py"
        },
        {
            "label": "🧪 测试页面",
            "path": r"pages/8_测试页面.py"
        },
    ],
}


# --- 辅助函数，用于反向查找标签 ---
@st.cache_data
def _get_path_to_label_map():
    """
    创建一个从 "路径" 到 "标签" 的映射字典。
    使用 @st.cache_data 缓存这个字典。
    """
    path_map = {}
    for group, scripts_in_group in SCRIPTS_BY_GROUP.items():
        for script in scripts_in_group:
            # 规范化路径以进行可靠的比较
            normalized_path = os.path.normpath(script["path"])
            path_map[normalized_path] = script["label"]

    # 添加主页
    path_map[os.path.normpath("streamlit_app.py")] = "🏠 主页"
    return path_map


PATH_TO_LABEL = _get_path_to_label_map()


def _get_current_page_label():
    """
    使用Streamlit的内部上下文来获取当前正在运行的脚本路径，
    并将其转换为 "标签"。
    """
    try:
        # 获取当前脚本的运行上下文
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx is None:
            return None

        # page_script_name 属性包含脚本路径 (例如 "pages/7_AI_对话页面.py")
        current_path = ctx.page_script_name
        normalized_current_path = os.path.normpath(current_path)

        # 从我们的映射中查找标签
        return PATH_TO_LABEL.get(normalized_current_path)
    except Exception:
        # 出错时安全返回
        return None

def create_common_sidebar():
    """
    在Streamlit应用的侧边栏中创建一个可折叠的公共分组导航。
    """

    # 1. 注入CSS以隐藏默认的Streamlit导航 (保持不变)
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. 创建自定义的侧边栏头部 (保持不变)
    st.sidebar.page_link("streamlit_app.py", label="🏠 返回主页")
    st.sidebar.title("🛠️ 功能导航")
    st.sidebar.divider()

    # --- 主要修改部分 ---
    # 3. 使用 st.expander 创建可折叠的导航菜单
    for group_name, scripts_in_group in SCRIPTS_BY_GROUP.items():
        # 为每个分组创建一个可折叠的容器
        # expanded=False 表示默认是折叠的, 你可以根据需要设置为 True 让某个分组默认展开
        with st.sidebar.expander(group_name, expanded=True):
            # 在折叠容器内部，为每个脚本创建页面链接
            for script in scripts_in_group:
                st.page_link(script["path"], label=script["label"])

    # 4. 添加使用统计信息
    # show_usage_stats()

    # 5. 小新动画
    shin_chan_animation()