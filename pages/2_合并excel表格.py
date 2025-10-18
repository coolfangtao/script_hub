import streamlit as st
import pandas as pd

st.title("📊 合并多个ASIN的关键词结果")

if st.button("← 返回主页"):
    st.switch_page("streamlit_app.py")

files = st.file_uploader("上传Excel文件", accept_multiple_files=True)
if files:
    dfs = [pd.read_excel(file) for file in files]
    merged = pd.concat(dfs)
    st.dataframe(merged)