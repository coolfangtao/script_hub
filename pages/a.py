import streamlit as st
import re

st.title("📌 HTML标题提取工具")

# if st.button("← 返回主页"):
#     st.switch_page("streamlit_app.py")
#
# uploaded_file = st.file_uploader("上传HTML文件")
# if uploaded_file:
#     text = uploaded_file.read().decode()
#     titles = re.findall(r'title="([^"]+)"', text)
#     st.write("提取到的标题：")
#     for title in titles:
#         st.write(title)