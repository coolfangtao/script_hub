# -*- coding: utf-8 -*-
"""
一个使用 Streamlit 和 Google Gemini Pro Vision 模型
从图片中提取表格数据的应用程序。
"""

import streamlit as st
import google.generativeai as genai
from PIL import Image
import re
import time  # 导入 time 模块用于计时


def configure_genai(api_key):
    """
    使用用户提供的 API 密钥配置 Google Generative AI。

    参数:
    api_key (str): 用户的 Google API 密钥。
    """
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"API 密钥配置失败: {e}")
        return False


def get_gemini_response(image, prompt):
    """
    向 Gemini Pro Vision 模型发送图片和提示，并获取响应。

    参数:
    image (PIL.Image.Image): 用户上传的图片。
    prompt (str): 用于指导模型分析图片的提示词。

    返回:
    tuple: 模型的文本响应和API调用耗时，如果出错则返回 (None, 0)。
    """
    start_time = time.time()  # 记录开始时间
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-tts')
        response = model.generate_content([prompt, image], stream=True)
        response.resolve()
        end_time = time.time()  # 记录结束时间
        duration = end_time - start_time  # 计算耗时
        return response.text, duration
    except Exception as e:
        st.error(f"调用 Gemini API 时发生错误: {e}")
        return None, 0


def perform_integrity_check(response_text):
    """
    解析模型的响应文本，提取数值并进行完整性检查。

    参数:
    response_text (str): 从 Gemini 模型获取的 Markdown 格式的文本。

    返回:
    tuple: 包含质量百分比总和、原子百分比总和以及检查结果消息的元组。
    """
    mass_sum = 0.0
    atomic_sum = 0.0

    # 使用正则表达式查找 Markdown 表格中的数值行
    # 这会匹配像 "| 任意字符 | 数字 ± 数字 | 数字 ± 数字 |" 这样的行
    pattern = r"\|\s*([A-Za-z\s]+ K?)\s*\|\s*([\d\.]+)\s*±\s*[\d\.]+\s*\|\s*([\d\.]+)\s*±\s*[\d\.]+\s*\|"

    lines = response_text.split('\n')
    found_data = False

    for line in lines:
        match = re.search(pattern, line)
        if match:
            # 检查第一个捕获组，确保不是表头
            element = match.group(1).strip()
            if "元素" in element or "Element" in element:
                continue

            found_data = True
            # 提取质量百分比和原子百分比的数值部分
            mass_percent = float(match.group(2).strip())
            atomic_percent = float(match.group(3).strip())

            mass_sum += mass_percent
            atomic_sum += atomic_percent

    if not found_data:
        return 0.0, 0.0, "无法从模型响应中解析出有效数据行，请检查模型输出格式是否为预期的 Markdown 表格。"

    # 检查总和是否接近 100
    mass_check_ok = abs(mass_sum - 100.0) < 0.1
    atomic_check_ok = abs(atomic_sum - 100.0) < 0.1

    # 构建结果消息
    messages = []
    messages.append(f"**质量百分比 (Mass %) 计算总和:** `{mass_sum:.2f}`")
    if mass_check_ok:
        messages.append("✅ 质量百分比完整性检查通过 (总和约等于 100)。")
    else:
        messages.append("⚠️ **警告:** 质量百分比完整性检查不通过 (总和不等于 100)。")

    messages.append(f"**原子百分比 (Atomic %) 计算总和:** `{atomic_sum:.2f}`")
    if atomic_check_ok:
        messages.append("✅ 原子百分比完整性检查通过 (总和约等于 100)。")
    else:
        messages.append("⚠️ **警告:** 原子百分比完整性检查不通过 (总和不等于 100)。")

    return mass_sum, atomic_sum, "\n\n".join(messages)


def main():
    """
    应用程序主函数。
    """
    st.set_page_config(page_title="图片表格识别工具", page_icon="📊", layout="wide")

    # --- 页面标题和说明 ---
    st.title("📊 使用 Gemini AI 从图片中提取表格数据")
    st.markdown("""
    本工具可以帮助您从包含X射线能谱（EDS）分析结果的图片中，自动识别并提取**定量结果**表格中的数据。
    """)

    # --- 侧边栏：API 密钥和文件上传 ---
    with st.sidebar:
        st.header("⚙️ 设置")
        api_key = st.text_input("请输入您的 Google Gemini API Key:", type="password", help="您的密钥将仅用于本次会话。")

        uploaded_file = st.file_uploader(
            "上传您的目标图片",
            type=["png", "jpg", "jpeg", "bmp", "webp"],
            help="请上传包含 '定量结果' 表格的图片文件。"
        )

        analyze_button = st.button("开始识别", type="primary", use_container_width=True)

    # --- 主内容区：图片展示和结果输出 ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🖼️ 您上传的图片")
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                st.image(image, caption="已上传的图片", use_column_width=True)
            except Exception as e:
                st.error(f"图片加载失败: {e}")
                image = None
        else:
            st.info("请在左侧上传一张图片。")
            image = None

    with col2:
        st.subheader("📈 识别结果")
        if analyze_button:
            if not api_key:
                st.warning("请输入您的 Google Gemini API Key。")
            elif image is None:
                st.warning("请先上传一张图片。")
            else:
                if configure_genai(api_key):
                    with st.spinner('正在调用 AI 模型进行识别，请稍候...'):

                        prompt = """
                        请仔细分析提供的图片，该图片展示了X射线能谱（EDS）分析的结果界面。你的任务是从右上角的‘定量结果’表格中，提取所有检测到的元素的定量分析数据。
                        对于表格中列出的每一个元素，请提取并清晰地列出以下两个数值：
                        - 质量百分比（Mass %）： 提取该元素在‘质量%’列中的数值及其不确定度。
                        - 原子百分比（Atomic %）： 提取该元素在‘原子%’列中的数值及其不确定度。
                        请以 Markdown 表格的格式呈现这些数据，确保所有数值及其对应的不确定度都完整且准确地体现在输出中。同时，请注意表格底部的‘总计’行，提取其质量百分比和原子百分比的总和数值（应为100.00）作为完整性检查。
                        """

                        # 更新函数调用以接收响应时间和耗时
                        response_text, duration = get_gemini_response(image, prompt)

                        if response_text:
                            # 在页面上显示耗时
                            st.info(f"模型响应耗时: **{duration:.2f}** 秒")

                            st.markdown("#### Gemini 模型提取内容:")
                            st.markdown(response_text)

                            st.markdown("---")

                            st.markdown("#### 完整性检查:")
                            _, _, check_message = perform_integrity_check(response_text)
                            st.markdown(check_message)
                        else:
                            st.error("未能从模型获取响应。")


if __name__ == "__main__":
    main()
