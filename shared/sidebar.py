# 文件路径: shared/sidebar.py

import streamlit as st

# --- 核心数据结构: 统一管理所有脚本和分组 ---
# 这是你项目中唯一的"数据源"，所有页面都从这里读取导航信息
SCRIPTS_BY_GROUP = {
    "🤖 AI工具": [
        {
            "label": "AI对话",
            "path": r"pages/7_AI_对话页面.py"  # 假设新文件放在pages目录下
        }
    ],
    "📊 运营维护": [
        {
            "label": "统计单个ASIN关键词结果",
            "path": r"pages/2_统计单个ASIN关键词结果.py"
        },
        {
            "label": "统计单个ASIN关键词结果",
            "path": r"pages/2_统计单个ASIN关键词结果V2.py"
        },
        {
            "label": "合并多个ASIN的关键词结果",
            "path": r"pages/2_合并多个ASIN关键词结果.py"
        },
        {
            "label": "统计多个ASIN关键词结果",
            "path": r"pages/2_统计多个ASIN关键词结果.py"
        },
        {
            "label": "根据ASIN关键词结果自动生成Listing标题",
            "path": r"pages/2_根据ASIN关键词结果自动生成Listing标题.py"
        },
    ],
    "📝 文本处理": [
        {
            "label": "B站标题提取",
            "path": r"pages/1_提取B站标题.py"
        },
        {
            "label": "文字转语音",
            "path": r"pages/3_文字转语音.py"
        },
        {
            "label": "文本对比",
            "path": r"pages/4_文本对比.py"
        },
        {
            "label": "句子语音现象分析",
            "path": r"pages/3_英语句子语音现象分析.py"
        },
    ],
    "🖼️ 图像处理": [
        {
            "label": "替换背景",
            "path": r"pages/5_替换图片背景.py"
        },
        {
            "label": "图像压缩",
            "path": r"pages/6_图像压缩.py"
        },
        {
            "label": "图像翻译",
            "path": r"pages/6_图片翻译.py"
        },
    ],
    "其他": [
        {
            "label": "基金涨跌",
            "path": r"pages/8_基金涨跌.py"
        },
    ],
}


def create_common_sidebar():
    """
    在Streamlit应用的侧边栏中创建一个公共分组导航。
    """

    # 1. 注入CSS以隐藏默认的Streamlit导航
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 新增代码: 添加返回主页的按钮 ---
    # 假设你的主页文件名为 streamlit_app.py
    st.sidebar.page_link("streamlit_app.py", label="🏠 返回主页")
    st.sidebar.divider()

    # 2. 创建自定义的侧边栏内容
    st.sidebar.title("🛠️ 功能导航")
    st.sidebar.divider()


    for group_name, scripts_in_group in SCRIPTS_BY_GROUP.items():
        st.sidebar.subheader(group_name)
        for script in scripts_in_group:
            st.sidebar.page_link(script["path"], label=script["label"])
        st.sidebar.divider()