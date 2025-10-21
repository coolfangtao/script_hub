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
import plotly.express as px
from shared.config import Config
from shared.sidebar import create_common_sidebar


# 实例化配置
cfg = Config()


# --- 核心功能函数 ---
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


def extract_eds_data_to_dataframe(markdown_text: str) -> pd.DataFrame:
    """
    从包含EDS分析结果的Markdown表格字符串中提取元素、质量百分比和原子百分比。

    Args:
        markdown_text: 包含Markdown表格的字符串。

    Returns:
        一个Pandas DataFrame，包含'元素', '质量百分比(%)', 和 '原子百分比(%)' 列。
    """
    if not isinstance(markdown_text, str):
        return pd.DataFrame(columns=['元素', '质量百分比(%)', '原子百分比(%)'])

    elements, atomic_percents, mass_percents = [], [], []
    lines = markdown_text.strip().split('\n')

    # 从第三行开始遍历，跳过表头和分隔线
    for line in lines[2:]:
        parts = [p.strip() for p in line.split('|') if p.strip()]

        # 确保行中有足够的数据列 (元素, 质量%, 原子%)
        if len(parts) < 3:
            continue

        element = parts[0]
        mass_percent_str = parts[1]
        atomic_percent_str = parts[2]

        # 如果是总计行，则停止解析
        if '总计' in element or 'Total' in element:
            break

        # 使用正则表达式提取数值
        mass_match = re.search(r'(\d+\.\d+|\d+)', mass_percent_str)
        atomic_match = re.search(r'(\d+\.\d+|\d+)', atomic_percent_str)

        if element and mass_match and atomic_match:
            elements.append(element)
            mass_percents.append(float(mass_match.group(1)))
            atomic_percents.append(float(atomic_match.group(1)))

    df = pd.DataFrame({
        '元素': elements,
        '质量百分比(%)': mass_percents,
        '原子百分比(%)': atomic_percents
    })
    return df


def classify_inclusion(eds_df: pd.DataFrame, threshold: float = 0.5) -> str:
    """
    根据EDS定量分析结果（DataFrame）和设定的优先级规则，对夹杂物进行分类。
    优先级规则: Ti/Nb > Al/Mg > La/Ce（稀土类） > Mn/S
    """
    if eds_df.empty:
        return "无有效数据"

    # 将元素列设为索引，以便快速查询
    # 使用 .get(col, default_value) 来安全地访问列数据
    def get_mass_percent(element):
        if '元素' in eds_df.columns and '质量百分比(%)' in eds_df.columns:
            element_row = eds_df[eds_df['元素'] == element]
            if not element_row.empty:
                return element_row['质量百分比(%)'].iloc[0]
        return 0.0

    # 检查各种元素是否存在且超过阈值
    has_ti_nb = get_mass_percent('Ti') > threshold or get_mass_percent('Nb') > threshold
    has_al_mg = get_mass_percent('Al') > threshold or get_mass_percent('Mg') > threshold
    has_la_ce = get_mass_percent('La') > threshold or get_mass_percent('Ce') > threshold
    has_mn_s = get_mass_percent('Mn') > threshold or get_mass_percent('S') > threshold

    # 根据优先级返回分类结果
    if has_ti_nb:
        return 'Ti、Nb'
    elif has_al_mg:
        return 'Al、Mg'
    elif has_la_ce:
        return '稀土'
    elif has_mn_s:
        return 'MnS'
    else:
        return '其他'


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


def display_elemental_composition_chart(df: pd.DataFrame):
    """
    在Streamlit中创建一个可折叠区域，并使用Plotly Express绘制左右两列、
    具有水平轴标签的条形图，分别展示元素的质量和原子百分比。

    Args:
        df (pd.DataFrame): 包含元素分析数据的DataFrame，
                           需要有 '元素', '质量百分比(%)', 和 '原子百分比(%)' 这几列。
    """
    # 确保DataFrame不为空且包含所需列
    if df is not None and not df.empty and all(col in df.columns for col in ['元素', '质量百分比(%)', '原子百分比(%)']):
        with st.expander("📊 图表分析：元素组成", expanded=True):
            col_mass, col_atomic = st.columns(2)

            # --- 左侧列: 质量百分比图表 ---
            with col_mass:
                st.subheader("质量百分比 (%)", anchor=False, divider='blue')

                # 使用 Plotly Express 创建条形图
                fig_mass = px.bar(
                    df,
                    x='元素',
                    y='质量百分比(%)',
                    title="质量百分比构成",
                    labels={'元素': '元素', '质量百分比(%)': '百分比'},  # 自定义轴标签
                    text='质量百分比(%)'  # 在条形图上显示数值
                )

                # 更新图表布局和样式
                fig_mass.update_layout(
                    title_font_size=18,
                    xaxis_title_font_size=16,
                    yaxis_title_font_size=16,
                    xaxis_tickangle=0  # 强制X轴标签水平显示
                )
                # 更新条形图上的文本样式
                fig_mass.update_traces(
                    texttemplate='%{text:.2f}%',  # 格式化文本，显示两位小数并加百分号
                    textposition='outside'  # 将文本放在条形图的外部
                )

                # 在Streamlit中显示Plotly图表
                st.plotly_chart(fig_mass, use_container_width=True)

            # --- 右侧列: 原子百分比图表 ---
            with col_atomic:
                st.subheader("原子百分比 (%)", anchor=False, divider='green')

                fig_atomic = px.bar(
                    df,
                    x='元素',
                    y='原子百分比(%)',
                    title="原子百分比构成",
                    labels={'元素': '元素', '原子百分比(%)': '百分比'},
                    text='原子百分比(%)'
                )

                fig_atomic.update_layout(
                    title_font_size=18,
                    xaxis_title_font_size=16,
                    yaxis_title_font_size=16,
                    xaxis_tickangle=0
                )
                fig_atomic.update_traces(
                    texttemplate='%{text:.2f}%',
                    textposition='outside'
                )

                st.plotly_chart(fig_atomic, use_container_width=True)

            st.caption("上方图表分别展示了识别出的各种元素的质量百分比与原子百分比。可将鼠标悬停在条形图上查看详细数据。")


def process_and_display_image(image_file, prompt, model_name, image_index):
    """
    处理单张上传的图片，并显示其分析结果。
    """
    st.markdown("---")
    col_img, col_results = st.columns([1, 1.2])

    with col_img:
        st.subheader(f"EDS图片: {image_file.name}", divider='rainbow')
        img = Image.open(image_file)
        st.image(img, caption="上传的EDS截图", use_container_width=True)

    # 首先调用API获取结果
    response_text, duration = get_gemini_response(img, prompt, model_name)

    if response_text:
        # 在右侧列中显示主要的分析结果
        with col_results:
            st.subheader("分析结果", divider='rainbow')

            # 1. 创建两列用于并排显示指标
            metric_col1, metric_col2 = st.columns(2)

            # 2. 在第一列显示API耗时
            with metric_col1:
                st.metric(label="AI模型调用耗时", value=f"{duration:.2f} 秒")

            # 3. 在第二列创建一个空的占位符，稍后用来填充分类结果
            classification_placeholder = metric_col2.empty()

            # 提取数据为DataFrame
            df_template = extract_eds_data_to_dataframe(response_text)

            # 如果AI未能提取任何数据，则提供一个空模板
            if df_template.empty:
                st.warning("AI未能从图片中提取有效数据，请检查图片清晰度。")
                # 创建一个空的DataFrame，但包含正确的列名，以便后续代码正常运行
                df_template = pd.DataFrame(columns=['元素', '质量百分比(%)', '原子百分比(%)'])

            # 1. 因为表格变为不可编辑，所以我们直接用原始的 df_template 来进行分类
            final_classification = classify_inclusion(df_template)

            # 2. 计算总和
            #    首先检查DataFrame是否为空，避免计算出错
            if not df_template.empty:
                mass_sum = df_template['质量百分比(%)'].sum()
                atomic_sum = df_template['原子百分比(%)'].sum()

                # 3. 创建一个包含总计信息的新DataFrame
                #    为了让“总计”更突出，我们使用Markdown的加粗语法
                total_row = pd.DataFrame({
                    '元素': ['总计（百分比之和，并非原图中总计）'],
                    '质量百分比(%)': [mass_sum],
                    '原子百分比(%)': [atomic_sum]
                })

                # 4. 将总计_df和原始_df合并成一个新的df用于显示
                display_df = pd.concat([df_template, total_row], ignore_index=True)
            else:
                # 如果原始数据为空，则直接显示空的df_template
                display_df = df_template

            # 5. 使用 st.dataframe() 来显示一个静态的、不可编辑的表格
            st.dataframe(display_df, use_container_width=True)

            # 将最终分类结果填充到顶部的占位符中
            styled_classification_html = f"""
                        <div style="padding-top: 0.5rem;"> <div style="font-size: 0.875rem; color: #28a745; margin-bottom: 4px;">最终杂质分类</div>
                            <div style="font-size: 2.0rem; font-weight: 600; color: #28a745;">{final_classification}</div>
                        </div>
                        """
            classification_placeholder.markdown(styled_classification_html, unsafe_allow_html=True)
            # --- 主要改动结束 ---

        # --- 全宽区域：显示图表和原始数据 ---
        # 这个代码块现在位于 col_results 的外面，因此它将占据全部可用宽度
        if response_text and not df_template.empty:
            # 调用图表函数，它会创建一个全宽的折叠区域
            display_elemental_composition_chart(df_template)

            # 将原始文本的折叠区域也放在这里，保持布局一致性
            with st.expander("查看AI模型原始返回文本"):
                st.markdown(response_text)

    else:
        # 如果API调用失败，仍然在右侧列显示错误信息
        with col_results:
            st.subheader("分析结果", divider='rainbow')
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