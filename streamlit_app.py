import streamlit as st

# 页面基础设置
st.set_page_config(layout="wide")

# --- 核心数据结构: 统一管理所有脚本和分组 ---
# 主页和侧边栏都将使用这个字典来生成内容
scripts_by_group = {
    "📊 电商运维": [
        {
            "label": "统计单个ASIN关键词结果",
            "path": r"pages/2_统计单个ASIN关键词结果.py"
        },
        {
            "label": "统计多个ASIN关键词结果",
            "path": r"pages/2_统计多个ASIN关键词结果.py"
        },
        {
            "label": "合并多个ASIN的关键词结果",
            "path": r"pages/2_合并多个ASIN关键词结果.py"
        },
        {
            "label": "根据ASIN关键词结果自动生成Listing标题",
            "path": r"pages/2_根据ASIN关键词结果自动生成Listing标题.py"
        },
    ],
    "📝 文本处理": [
        {
            "label": "B站标题提取工具",
            "path": r"pages/1_提取B站标题.py"
        },
        {
            "label": "文字转语音",
            "path": r"pages/3_文字转语音.py"
        },
        {
            "label": "句子语音现象分析",
            "path": r"pages/3_英语句子语音现象分析.py"
        },
        {
            "label": "文本对比",
            "path": r"pages/4_文本对比.py"
        },
    ],
    "🖼️ 图像处理": [
        {
            "label": "替换图片背景",
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
    ]
}


# --- 新增功能: 自定义侧边栏导航 ---
# 1. 隐藏 streamlit 默认生成的侧边栏
# 注意: 这是一种CSS "hack"，未来Streamlit版本更新可能会影响其效果
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# 2. 使用我们自己的字典来构建侧边栏
st.sidebar.title("🛠️ 功能导航")
st.sidebar.divider()

for group_name, scripts_in_group in scripts_by_group.items():
    st.sidebar.subheader(group_name)
    for script in scripts_in_group:
        # 使用 st.page_link 创建到每个页面的链接
        st.sidebar.page_link(script["path"], label=script["label"])
    st.sidebar.divider()


# --- 页面主内容: 保持不变 ---
st.title("🚀 FT的脚本中心")
st.markdown("---")

NUM_COLUMNS = 3

# 遍历每个分组
for group_name, scripts_in_group in scripts_by_group.items():
    with st.expander(group_name, expanded=True):
        cols = st.columns(NUM_COLUMNS)
        for index, script in enumerate(scripts_in_group):
            col = cols[index % NUM_COLUMNS]
            with col:
                if st.button(script["label"], help=script.get("help", script["label"]), use_container_width=True, key=script["path"] + str(index)):
                    st.switch_page(script["path"])

st.markdown("---")
st.info("💡 提示：点击上方按钮或左侧导航栏，即可跳转到对应的工具页面。")