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
    统一使用正斜杠 (/) 作为路径分隔符，以实现跨平台兼容。
    """
    path_map = {}
    for group, scripts_in_group in SCRIPTS_BY_GROUP.items():
        for script in scripts_in_group:
            # 统一使用正斜杠
            normalized_path = script["path"].replace("\\", "/")
            path_map[normalized_path] = script["label"]

    # 添加主页
    path_map["streamlit_app.py".replace("\\", "/")] = "🏠 主页"
    return path_map


PATH_TO_LABEL = _get_path_to_label_map()


def _get_current_page_label():
    """
    (已修复)
    使用Streamlit的内部上下文来获取当前正在运行的脚本路径，
    并将其转换为 "标签"。
    """
    try:
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx is None:
            return None

        current_path = None
        try:
            # 1. 尝试获取子页面的路径
            current_path = ctx.page_script_name
        except AttributeError:
            # 2. 如果失败 (AttributeError)，说明我们在主页上
            current_path = "streamlit_app.py"

        if current_path is None:
            return None

        # 3. 规范化路径 (统一使用 /) 并从字典中查找
        normalized_current_path = current_path.replace("\\", "/")
        label = PATH_TO_LABEL.get(normalized_current_path)

        if label is None:
            # 调试: 仅在查找失败时显示错误
            st.sidebar.error(f"调试: 路径 `{normalized_current_path}` 未在字典中找到。")

        return label

    except Exception as e:
        # 捕获其他意外错误
        st.sidebar.error(f"调试: _get_current_page_label 发生异常: {e}")
        return None


# --- 替换结束 ---

def create_common_sidebar():
    """
    在Streamlit应用的侧边栏中创建一个可折叠的公共分组导航。
    """

    # --- 页面访问跟踪 ---
    # 自动获取当前页面的标签
    current_label = _get_current_page_label()
    if current_label:
        st.sidebar.caption(f"🔍 正在检测页面: {current_label}")
    else:
        st.sidebar.caption("🔍 未检测到页面标签")
    if current_label:
        track_page_visit(current_label)

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


    # 5. 小新动画
    shin_chan_animation()