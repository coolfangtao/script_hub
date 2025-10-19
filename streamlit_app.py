import streamlit as st

# 页面基础设置
st.set_page_config(layout="wide")
st.title("🚀 FT的脚本中心")
st.markdown("---")

# --- 优化点 1: 将所有脚本信息按功能分组存放在一个字典中 ---
# Key是分组名称，Value是该分组下的脚本列表
# 以后每新增一个脚本，只需要在对应的分组列表中添加一个字典即可
scripts_by_group = {
    "📊 电商运维": [
        {
            "label": "统计单个ASIN关键词结果",
            "help": "统计单个ASIN关键词结果",
            "path": r"pages/2_统计单个ASIN关键词结果.py"
        },
        {
            "label": "统计多个ASIN关键词结果",
            "help": "统计多个ASIN关键词结果",
            "path": r"pages/2_统计多个ASIN关键词结果.py"
        },
        {
            "label": "合并多个ASIN的关键词结果",
            "help": "合并多个Excel文件到一个Excel中",
            "path": r"pages/2_合并多个ASIN关键词结果.py"
        },
        {
            "label": "根据ASIN关键词结果自动生成Listing标题",
            "help": "根据ASIN关键词结果自动生成Listing标题",
            "path": r"pages/2_根据ASIN关键词结果自动生成Listing标题.py"
        },
    ],
    "📝 文本处理": [
        {
            "label": "B站标题提取工具",
            "help": "从HTML提取标题",
            "path": r"pages/1_提取B站标题.py"
        },
        {
            "label": "文字转语音",
            "help": "输入文字，输出语音",
            "path": r"pages/3_文字转语音.py"
        },
        {
            "label": "句子语音现象分析",
            "help": "句子语音现象分析",
            "path": r"pages/3_英语句子语音现象分析.py"
        },
        {
            "label": "文本对比",
            "help": "对比两段文本，发现修改的内容",
            "path": r"pages/4_文本对比.py"
        },
    ],
    "🖼️ 图像处理": [
        {
            "label": "替换图片背景",
            "help": "替换图片背景",
            "path": r"pages/5_替换图片背景.py"
        },
        {
            "label": "图像压缩",
            "help": "图像压缩到目标大小",
            "path": r"pages/6_图像压缩.py"
        },
        {
            "label": "图像翻译",
            "help": "图片翻译",
            "path": r"pages/6_图片翻译.py"
        },
    ]
    # --- 示例: 如果未来要添加新的分组 ---
    # "💡 其他工具": [
    #     {
    #         "label": "新工具名称",
    #         "help": "这个新工具是用来做...",
    #         "path": r"pages/7_新工具.py"
    #     },
    # ]
}

# --- 优化点 2: 动态创建可折叠的分组和按钮 ---
# 你可以在这里轻松调整每行显示的列数
NUM_COLUMNS = 3

# 遍历每个分组
for group_name, scripts_in_group in scripts_by_group.items():
    # 使用st.expander创建一个可折叠的容器来展示每个分组
    # expanded=True 让所有分组默认展开，你也可以设为False，让它们默认折叠
    with st.expander(group_name, expanded=True):
        # 动态创建列
        cols = st.columns(NUM_COLUMNS)
        # 遍历该分组下的所有脚本，并创建按钮
        for index, script in enumerate(scripts_in_group):
            # 使用取模运算(%)来循环将按钮依次放入不同的列
            col = cols[index % NUM_COLUMNS]
            with col:
                # 使用path作为独立的key，避免因label重复导致Streamlit报错
                if st.button(script["label"], help=script["help"], use_container_width=True, key=script["path"] + str(index)):
                    st.switch_page(script["path"])

st.markdown("---")
st.info("💡 提示：点击上方按钮，即可跳转到对应的工具页面。")