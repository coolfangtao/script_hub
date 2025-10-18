import streamlit as st

# 页面基础设置
st.set_page_config(layout="wide")
st.title("🚀 FT的脚本中心")

# --- 优化点 1: 将所有脚本信息集中存放在一个列表中 ---
# 以后每新增一个脚本，只需要在这里添加一个字典即可
# 格式: {"label": "按钮上显示的文字", "help": "鼠标悬停时的提示", "path": "脚本文件路径"}
scripts_config = [
    {
        "label": "📌 B站标题提取工具",
        "help": "从HTML提取标题",
        "path": r"pages/1_提取B站标题.py"
    },
    {
        "label": "📊 合并多个ASIN的关键词结果",
        "help": "合并多个Excel文件到一个Excel中",
        "path": r"pages/2_合并多个ASIN的关键词结果.py"
    },
    {
        "label": "🔊 文字转语音",
        "help": "输入文字，输出语音",
        "path": r"pages/3_文字转语音.py"
    },
    {
        "label": "🔎 文本对比",
        "help": "对比两段文本，发现修改的内容",
        "path": r"pages/4_文本对比.py"
    },
    {
        "label": "🖼️ 替换图片背景",
        "help": "替换图片背景",
        "path": r"pages/5_替换图片背景.py"
    },
    {
        "label": "图像压缩",
        "help": "图像压缩到目标大小",
        "path": r"pages/6_图像压缩.py"
    },
    # --- 示例: 如果未来要添加第4个工具，只需在这里新增一行即可 ---
    # {
    #     "label": "💡 新工具名称",
    #     "help": "这个新工具是用来做...",
    #     "path": r"pages/4_新工具.py"
    # },
]

# --- 优化点 2: 动态创建列和按钮 ---
# 你可以在这里轻松调整每行显示的列数
NUM_COLUMNS = 3
cols = st.columns(NUM_COLUMNS)

# 通过循环遍历配置列表，自动生成所有按钮
for index, script in enumerate(scripts_config):
    # 使用取模运算(%)来循环将按钮依次放入不同的列
    # 比如第0个按钮放第0列，第1个放第1列，第2个放第2列，第3个再回到第0列...
    col = cols[index % NUM_COLUMNS]
    with col:
        if st.button(script["label"], help=script["help"], use_container_width=True):
            st.switch_page(script["path"])