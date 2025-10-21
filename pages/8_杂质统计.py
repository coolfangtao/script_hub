# -*- coding: utf-8 -*-

"""
一个使用Streamlit构建的Web应用，用于分析X射线能谱（EDS）截图来判断物质中的杂质类型。

功能:
1. 用户上传一张或多张EDS结果截图。
2. 用户输入Google Gemini API密钥并选择使用的AI模型。
3. 应用调用Gemini Pro Vision API识别图片中的元素及其含量。
4. 将识别出的数据以可编辑的表格形式展示。
5. 根据预设规则对杂质进行自动分类。
6. 为每张图片并排展示其分析结果。
"""

import streamlit as st
import google.generativeai as genai
import time
import re
from PIL import Image
import pandas as pd
from shared.config import Config
from shared.sidebar import create_common_sidebar


# 实例化配置
cfg = Config()


# --- 核心功能函数 ---
# 以下是您已经提供，并在此基础上进行整合和优化的函数。

def get_gemini_response(image: Image.Image, prompt: str, model_name: str):
    """
    向 Gemini Pro Vision 模型发送图片和提示，并获取响应。

    参数:
    image (PIL.Image.Image): 用户上传的图片。
    prompt (str): 用于指导模型分析图片的提示词。
    model_name (str): 使用的AI模型。

    返回:
    tuple: 模型的文本响应和API调用耗时，如果出错则返回 (None, 0)。
    """
    start_time = time.time()  # 记录开始时间
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([prompt, image], stream=True)
        response.resolve()
        end_time = time.time()  # 记录结束时间
        duration = end_time - start_time  # 计算耗时
        return response.text, duration
    except Exception as e:
        # 在界面上显示更具体的错误信息
        st.error(f"调用 Gemini API 时发生错误: {e}")
        return None, 0


def extract_eds_data_to_dict(markdown_text: str) -> dict:
    """
    从包含EDS分析结果的Markdown表格字符串中提取元素和质量百分比。

    Args:
        markdown_text: 包含Markdown表格的字符串。

    Returns:
        一个字典，其中键是元素符号（字符串），值是质量百分比（浮点数）。
        例如：{'C': 13.35, 'O': 19.33, ...}
    """
    if not isinstance(markdown_text, str):
        return {}

    element_data = {}
    lines = markdown_text.strip().split('\n')

    # 从第三行开始遍历，跳过表头和分隔线
    for line in lines[2:]:
        # 使用'|'分割行内容
        parts = [p.strip() for p in line.split('|') if p.strip()]

        # 确保行中有足够的数据列
        if len(parts) < 3:
            continue

        element = parts[0]
        mass_percent_str = parts[2]

        # 如果是总计行，则停止解析
        if '总计' in element or 'Total' in element:
            break

        # 使用正则表达式提取'±'符号前的浮点数
        # 这个正则表达式会匹配一个或多个数字，可能包含一个小数点
        match = re.search(r'(\d+\.\d+|\d+)', mass_percent_str)

        if match:
            mass_percent_val = float(match.group(1))
            element_data[element] = mass_percent_val

    return element_data


def classify_inclusion(eds_data: dict, threshold: float = 0.5) -> str:
    """
    根据EDS定量分析结果和设定的优先级规则，对夹杂物进行分类。
    优先级规则: Ti/Nb > Al/Mg > La/Ce（稀土类） > Mn/S
    """
    if not eds_data:
        return "无有效数据"

    # 检查各种元素是否存在且超过阈值
    has_ti_nb = eds_data.get('Ti', 0) > threshold or eds_data.get('Nb', 0) > threshold
    has_al_mg = eds_data.get('Al', 0) > threshold or eds_data.get('Mg', 0) > threshold
    has_la_ce = eds_data.get('La', 0) > threshold or eds_data.get('Ce', 0) > threshold
    has_mn_s = eds_data.get('Mn', 0) > threshold or eds_data.get('S', 0) > threshold

    # 根据优先级返回分类结果
    if has_ti_nb:
        return 'Ti、Nb 类夹杂物'
    elif has_al_mg:
        return 'Al、Mg 类夹杂物'
    elif has_la_ce:
        return '稀土类夹杂物'
    elif has_mn_s:
        return 'MnS 类夹杂物'
    else:
        return '其他类型'


# --- Streamlit 界面渲染函数 ---

def setup_ui():
    """
    设置Streamlit界面的主要元素，并返回用户的输入。
    """
    st.set_page_config(page_title="EDS能谱杂质分析工具", layout="wide")
    st.title("🔬 EDS能谱杂质智能分析工具")
    st.markdown("上传一张或多张EDS分析截图，工具将自动识别元素含量并判断杂质类型。")
    create_common_sidebar()

    # 在主页面创建输入组件
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            api_key = st.text_input("🔑 请输入您的Google Gemini API密钥", type="password", help="您的API密钥将仅用于本次分析，不会被储存。")
        with col2:
            model_name = st.selectbox(
                "🤖 请选择AI模型",
                options=cfg.ZAZHI_JIANCE_GEMINI_MODEL_OPTIONS,
                index=0,  # 默认选择第一个
                help="推荐使用 'gemini-2.5-flash-lite' 以获得更快的速度和更优的性能。"
            )

        uploaded_files = st.file_uploader(
            "📂 请上传EDS分析截图，至少要包含完整的元素质量数据",
            type=['png', 'jpg', 'jpeg', 'bmp', 'webp'],
            accept_multiple_files=True
        )

    analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True)

    return api_key, model_name, uploaded_files, analyze_button


def process_and_display_image(image_file, prompt, model_name, image_index):
    """
    处理单张上传的图片，并显示其分析结果。
    """
    st.markdown("---")
    col_img, col_results = st.columns([1, 1.2])

    with col_img:
        st.subheader(f"图片: {image_file.name}", divider='rainbow')
        img = Image.open(image_file)
        st.image(img, caption="上传的EDS截图", use_column_width=True)

    with col_results:
        st.subheader("分析结果", divider='rainbow')

        # 调用API获取结果
        response_text, duration = get_gemini_response(img, prompt, model_name)

        if response_text:
            # 提取数据
            eds_data_dict = extract_eds_data_to_dict(response_text)

            # 使用Metric展示关键信息
            st.metric(label="AI模型调用耗时", value=f"{duration:.2f} 秒")

            # st.info("下方表格中的数据是可编辑的。修改后，下方的分类结果将自动更新。")

            # 将字典转换为DataFrame以便于使用st.data_editor
            if eds_data_dict:
                df = pd.DataFrame(list(eds_data_dict.items()), columns=['元素', '质量百分比(%)'])
            else:
                # 如果AI未能提取任何数据，则提供一个空模板
                st.warning("AI未能从图片中提取有效数据，请检查图片清晰度或在下方表格中手动输入。")
                df = pd.DataFrame({'元素': ['C', 'O', 'Al', 'Ti'], '质量百分比(%)': [0.0, 0.0, 0.0, 0.0]})

            # 创建可编辑的数据表格，使用唯一的key
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                key=f"editor_{image_index}"  # 为每个编辑器设置唯一key
            )

            # 将编辑后的DataFrame转换回字典
            edited_eds_data = dict(zip(edited_df['元素'], edited_df['质量百分比(%)']))

            # 使用编辑后的数据进行分类
            final_classification = classify_inclusion(edited_eds_data)

            # 使用st.success突出显示最终分类结果
            st.success(f"**最终杂质分类:** {final_classification}")

            # 提供一个可展开的区域来显示原始的AI响应文本，方便调试
            with st.expander("查看AI模型原始返回文本"):
                st.markdown("**AI原始响应（Markdown格式）:**")
                st.code(response_text, language="markdown")
        else:
            st.error("无法获取AI模型的响应，请检查您的API密钥、网络连接或图片是否有效。")


def main():
    """
    应用主函数
    """
    api_key, model_name, uploaded_files, analyze_button = setup_ui()

    if analyze_button:
        # 校验输入
        if not api_key:
            st.warning("请输入您的Gemini API密钥。")
        elif not uploaded_files:
            st.warning("请至少上传一张图片。")
        else:
            try:
                # 配置Gemini API
                genai.configure(api_key=api_key)

                with st.spinner('正在分析中，请稍候...'):
                    # 根据上传文件的数量决定布局
                    if len(uploaded_files) == 1:
                        process_and_display_image(
                            uploaded_files[0],
                            cfg.ZAZHI_JIANCE_GET_ELEMENTS_DATA_PROMPT,
                            model_name,
                            0
                        )
                    else:
                        st.header("📊 批量分析结果", anchor=False)
                        for i, uploaded_file in enumerate(uploaded_files):
                            process_and_display_image(
                                uploaded_file,
                                cfg.ZAZHI_JIANCE_GET_ELEMENTS_DATA_PROMPT,
                                model_name,
                                i
                            )
                st.balloons()
                st.success("所有图片分析完成！")

            except Exception as e:
                st.error(f"发生了一个未预料的错误: {e}")
                st.info("这可能是由于API密钥无效或权限问题导致的。请检查您的密钥。")


if __name__ == "__main__":
    main()
