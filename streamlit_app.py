import streamlit as st

st.set_page_config(layout="wide")

st.title("🚀 我的脚本中心")

# --- 假设你将文件名修改为了 a.py 和 b.py ---

col1, col2 = st.columns(2)

with col1:
    if st.button("📌 标题提取工具", help="从HTML提取标题", use_container_width=True):
        # 使用新的、有效的文件名
        st.switch_page(r"pages/a.py")

with col2:
    if st.button("📊 Excel合并工具", help="合并多个Excel文件", use_container_width=True):
        # 使用新的、有效的文件名
        st.switch_page(r"pages/b.py")