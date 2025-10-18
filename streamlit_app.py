import streamlit as st

st.set_page_config(layout="wide")

st.title("🚀 我的脚本中心")

col1, col2 = st.columns(2)

with col1:
    if st.button("📌 标题提取工具", help="从HTML提取标题", use_container_width=True):
        st.switch_page("1.py")

with col2:
    if st.button("📊 Excel合并工具", help="合并多个Excel文件", use_container_width=True):
        st.switch_page("2.py")