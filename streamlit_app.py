import streamlit as st

st.set_page_config(layout="wide")

st.title("🚀 FT的脚本中心")

# --- 假设你将文件名修改为了 1_提取B站标题.py 和 2_合并多个ASIN的关键词结果.py ---

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📌 B站标题提取工具", help="从HTML提取标题", use_container_width=True):
        # 使用新的、有效的文件名
        st.switch_page(r"pages/1_提取B站标题.py")

with col2:
    if st.button("📊 合并多个ASIN的关键词结果", help="合并多个Excel文件到一个Excel中", use_container_width=True):
        # 使用新的、有效的文件名
        st.switch_page(r"pages/2_合并多个ASIN的关键词结果.py")

with col3:
    if st.button("🔊 文字转语音", help="输入文字，输出语音", use_container_width=True):
        # 使用新的、有效的文件名
        st.switch_page(r"pages/3_文字转语音.py")