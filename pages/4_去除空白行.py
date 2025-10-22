import streamlit as st
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数

create_common_sidebar()

# --- 页面配置 ---
st.set_page_config(
    page_title="空白行去除工具",
    page_icon="🧹"
)

# --- 页面标题 ---
st.title("🧹 文本空白行去除工具")
st.write("这是一个简单的小工具，可以快速删除文本中所有的空白行。")

# --- 输入文本框 ---
st.subheader("1. 在下方粘贴您的文本")
input_text = st.text_area(
    "输入文本框",
    height=300,
    placeholder="请在这里粘贴包含空白行的文本...",
    label_visibility="collapsed"
)

# --- 处理按钮 ---
if st.button("去除空白行", type="primary"):
    if input_text:
        # 1. 将输入文本按行分割成列表
        lines = input_text.splitlines()

        # 2. 使用列表推导式过滤掉所有只包含空白字符的行
        # line.strip() 会移除行首和行尾的空白符，如果结果为空字符串，则说明是空白行
        non_empty_lines = [line for line in lines if line.strip()]

        # 3. 将处理后的行重新用换行符连接成一个字符串
        output_text = "\n".join(non_empty_lines)

        # --- 显示结果 ---
        st.subheader("2. 处理完成的文本")
        st.text_area(
            "结果文本框",
            value=output_text,
            height=300,
            label_visibility="collapsed"
        )
        st.success("所有空白行已成功去除！")
    else:
        # 如果用户没有输入任何文本就点击按钮，则发出警告
        st.warning("请输入一些文本再进行处理。")