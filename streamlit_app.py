import streamlit as st
import re


def extract_and_clean_titles(html_text):
    # 定义正则表达式模式，匹配div title="content"中的内容
    pattern = r'div title="([^"]+)"'

    # 查找所有匹配的内容
    matches = re.findall(pattern, html_text)

    # 去除中文字符
    cleaned_titles = []
    for match in matches:
        # 去除中文字符
        cleaned = re.sub(r'[\u4e00-\u9fff]', '', match)
        cleaned_titles.append(cleaned)

    return cleaned_titles


def extract_and_clean_titles_for_jisuanjizuchengyuanli(html_text):
    # 定义正则表达式模式，匹配div title="content"中的内容
    pattern = r'title="([^"]+)"'

    # 查找所有匹配的内容
    matches = re.findall(pattern, html_text)

    return matches


def extract_and_clean_titles_for_shulun(html_text):
    # 定义正则表达式模式，匹配div title="content"中的内容
    pattern = r'title="([^"]+)"'

    # 查找所有匹配的内容
    matches = re.findall(pattern, html_text)

    return matches


def main():
    st.title("B站视频合集标题提取")
    st.write("这是一个用于从B站视频合集中批量提取标题的工具")

    # 创建文件上传器
    uploaded_file = st.file_uploader("选择文件", type=['txt', 'html'])

    # 创建选择提取方法的单选按钮
    method = st.radio("选择提取方法:",
                      ("通用提取", "计算机组成原理提取", "数论提取"))

    if uploaded_file is not None:
        # 读取文件内容
        html_text = uploaded_file.read().decode('utf-8')

        # 根据选择的方法提取标题
        if method == "通用提取":
            cleaned_titles = extract_and_clean_titles(html_text)
        elif method == "计算机组成原理提取":
            cleaned_titles = extract_and_clean_titles_for_jisuanjizuchengyuanli(html_text)
        else:
            cleaned_titles = extract_and_clean_titles_for_shulun(html_text)

        # 显示提取结果
        st.subheader("提取结果:")
        for i, title in enumerate(cleaned_titles, 1):
            st.write(f"{i}. {title}")

        # 提供下载结果的选项
        result_text = "\n".join(cleaned_titles)
        st.download_button(
            label="下载提取结果",
            data=result_text,
            file_name='extracted_titles.txt',
            mime='text/plain'
        )


if __name__ == "__main__":
    main()