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
from shared.sidebar import create_common_sidebar
from io import BytesIO  # 导入BytesIO用于处理字节数据


class Config:
    """
    这个类用于集中存放所有Streamlit应用的配置参数。理论上所有的硬编码都应该放在这里
    它支持从YAML文件加载配置、动态设置/获取值以及清晰地打印所有配置项。
    """

    def __init__(self):
        # 杂质检测可用的AI模型
        self.ZAZHI_JIANCE_GEMINI_MODEL_OPTIONS = [
            "gemini-2.5-flash-lite",  # 默认模型，可用，2.15秒
            "gemini-2.0-flash",  # 可用，5.11秒
            "gemini-2.5-pro",   # 可用，14.93秒
            "gemini-2.0-flash-exp",  # 可用，4.28秒
            "gemini-2.0-flash-lite",  # 可用，9.62秒
            "gemini-2.5-flash",  # 可用，6.74秒
            "gemini-robotics-er-1.5-preview",  # 可用，8.73秒
        ]

        self.ZAZHI_JIANCE_GET_ELEMENTS_DATA_PROMPT = """
                        请仔细分析提供的图片，该图片展示了X射线能谱（EDS）分析的结果界面。你的任务是从右上角的‘定量结果’表格中，提取所有检测到的元素的定量分析数据。
                        对于表格中列出的每一个元素，请提取并清晰地列出以下两个数值：
                        - 质量百分比（Mass %）： 提取该元素在‘质量%’列中的数值及其不确定度。
                        - 原子百分比（Atomic %）： 提取该元素在‘原子%’列中的数值及其不确定度。
                        请以 Markdown 表格的格式呈现这些数据，确保所有数值及其对应的不确定度都完整且准确地体现在输出中。
                        然后关注‘定量结果’列表中的元素及其含量，并结合能谱图的峰位，简要分析该物质的主要组成成分（例如是氧化镁还是碳化物或者硫化物等）。
                        最后依据结果界面的数据给出杂质（左上图中黑点）的具体尺寸（微米）。
                        """


# 实例化配置
cfg = Config()


# --- 核心功能函数 ---

# 使用 st.cache_data 装饰器来缓存API的返回结果
# 这意味着如果使用相同的图片、提示和模型再次调用此函数，将直接返回缓存的结果，无需再次调用API
@st.cache_data
def get_gemini_response(image_bytes: bytes, prompt: str, model_name: str):
    """
    向 Gemini Pro Vision 模型发送图片和提示，并获取响应。
    使用 st.cache_data 缓存结果以避免重复调用。

    参数:
    image_bytes (bytes): 用户上传的图片的字节数据。
    prompt (str): 用于指导模型分析图片的提示词。
    model_name (str): 使用的AI模型。

    返回:
    tuple: 模型的文本响应和API调用耗时，如果出错则返回 (None, 0)。
    """
    start_time = time.time()  # 记录开始时间
    try:
        # 从字节数据重新构建图片对象
        image = Image.open(BytesIO(image_bytes))
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([prompt, image], stream=True)
        response.resolve()
        end_time = time.time()  # 记录结束时间
        duration = end_time - start_time  # 计算耗时
        return response.text, duration
    except Exception as e:
        # 在界面上显示更具体的错误信息
        # 注意：在缓存的函数中直接调用st.error可能会产生意外行为，更好的做法是返回错误信息
        # 但对于这个应用场景，直接显示错误也是可以接受的。
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
                help="推荐使用 'gemini-1.5-flash-latest' 以获得最佳的速度与性能平衡。"
            )

        uploaded_files = st.file_uploader(
            "📂 请上传EDS分析截图，至少要包含完整的元素质量数据",
            type=['png', 'jpg', 'jpeg', 'bmp', 'webp'],
            accept_multiple_files=True
        )

    analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True)

    return api_key, model_name, uploaded_files, analyze_button


def display_elemental_composition_chart(df: pd.DataFrame, image_index: int):
    """
    在Streamlit中创建一个可折叠区域，并使用Plotly Express绘制左右两列、
    具有水平轴标签的条形图，分别展示元素的质量和原子百分比。

    Args:
        df (pd.DataFrame): 包含元素分析数据的DataFrame。
        image_index (int): 当前图片的索引，用于生成唯一的组件key。
    """
    if df is not None and not df.empty and all(col in df.columns for col in ['元素', '质量百分比(%)', '原子百分比(%)']):
        with st.expander("📊 图表分析：元素组成", expanded=True):
            col_mass, col_atomic = st.columns(2)

            with col_mass:
                st.subheader("质量百分比 (%)", anchor=False, divider='blue')
                fig_mass = px.bar(df, x='元素', y='质量百分比(%)', title="质量百分比构成",
                                  labels={'元素': '元素', '质量百分比(%)': '百分比'},
                                  text='质量百分比(%)',
                                  color='质量百分比(%)',
                                  color_continuous_scale='viridis')
                fig_mass.update_layout(title_font_size=18, xaxis_title_font_size=16, yaxis_title_font_size=16,
                                       xaxis_tickangle=0)
                fig_mass.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                fig_mass.update_coloraxes(showscale=False)
                st.plotly_chart(fig_mass, use_container_width=True, key=f"mass_chart_{image_index}")

            with col_atomic:
                st.subheader("原子百分比 (%)", anchor=False, divider='green')
                fig_atomic = px.bar(df, x='元素', y='原子百分比(%)', title="原子百分比构成",
                                    labels={'元素': '元素', '原子百分比(%)': '百分比'},
                                    text='原子百分比(%)',
                                    color='原子百分比(%)',
                                    color_continuous_scale='plasma')
                fig_atomic.update_layout(title_font_size=18, xaxis_title_font_size=16, yaxis_title_font_size=16,
                                         xaxis_tickangle=0)
                fig_atomic.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                fig_atomic.update_coloraxes(showscale=False)
                st.plotly_chart(fig_atomic, use_container_width=True, key=f"atomic_chart_{image_index}")

            st.caption("上方图表分别展示了识别出的各种元素的质量百分比与原子百分比。可将鼠标悬停在条形图上查看详细数据。")


def process_and_display_image(image_file, prompt, model_name, image_index):
    """
    处理单张上传的图片，并显示其分析结果。
    """
    st.markdown("---")
    col_img, col_results = st.columns([1, 1.2])

    with col_img:
        st.subheader(f"EDS图片: {image_file.name}", divider='rainbow')
        # 直接传递上传的文件对象给 st.image，它能自动处理
        st.image(image_file, caption="上传的EDS截图", use_container_width=True)

    # 从缓存或API调用获取结果。
    # 我们传递 image_file.getvalue()，即图片的字节内容，作为缓存的键。
    # 这样，只要图片内容、提示和模型名称不变，就会从缓存中读取结果。
    response_text, duration = get_gemini_response(image_file.getvalue(), prompt, model_name)

    if response_text:
        with col_results:
            st.subheader("分析结果", divider='rainbow')
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric(label="AI模型调用耗时", value=f"{duration:.2f} 秒")

            classification_placeholder = metric_col2.empty()
            df_template = extract_eds_data_to_dataframe(response_text)

            if df_template.empty:
                st.warning("AI未能从图片中提取有效数据，请检查图片清晰度。")
                df_template = pd.DataFrame(columns=['元素', '质量百分比(%)', '原子百分比(%)'])

            final_classification = classify_inclusion(df_template)

            if not df_template.empty:
                mass_sum = df_template['质量百分比(%)'].sum()
                atomic_sum = df_template['原子百分比(%)'].sum()
                total_row = pd.DataFrame({
                    '元素': ['**总计 (识别数据求和)**'],
                    '质量百分比(%)': [mass_sum],
                    '原子百分比(%)': [atomic_sum]
                })
                display_df = pd.concat([df_template, total_row], ignore_index=True)
            else:
                display_df = df_template

            st.dataframe(display_df, use_container_width=True)
            styled_classification_html = f"""
                        <div style="padding-top: 0.5rem;"> <div style="font-size: 0.875rem; color: #28a745; margin-bottom: 4px;">最终杂质分类</div>
                            <div style="font-size: 2.0rem; font-weight: 600; color: #28a745;">{final_classification}</div>
                        </div>
                        """
            classification_placeholder.markdown(styled_classification_html, unsafe_allow_html=True)

        if response_text and not df_template.empty:
            display_elemental_composition_chart(df_template, image_index=image_index)
            with st.expander("查看AI模型原始返回文本"):
                st.markdown(response_text)
    else:
        with col_results:
            st.subheader("分析结果", divider='rainbow')
            st.error("无法获取AI模型的响应，请检查您的API密钥、网络连接或图片是否有效。")


def main():
    """
    应用主函数
    """
    api_key, model_name, uploaded_files, analyze_button = setup_ui()

    if analyze_button:
        if not api_key:
            st.warning("请输入您的Gemini API密钥。")
        elif not uploaded_files:
            st.warning("请至少上传一张图片。")
        else:
            try:
                genai.configure(api_key=api_key)
                with st.spinner('正在分析中，请稍候...'):
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