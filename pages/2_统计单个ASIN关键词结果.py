import streamlit as st
import pandas as pd
import re
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from shared.sidebar import create_common_sidebar

# 初始化侧边栏
create_common_sidebar()

# --- 1. 核心功能函数 ---

@st.cache_data  # 缓存解析结果
def parse_filename(filename):
    """
    从文件名中解析出国家、ASIN、关键词数量和日期。
    文件名格式: ReverseASIN-US-B01N9KSITZ(1584)-20251012.xlsx
    """
    match = re.search(r'ReverseASIN-(.+)-(.+)\((\d+)\)-(\d+)', filename)
    if match:
        country, asin, keyword_count, date = match.groups()
        # 格式化日期
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        return country, asin, int(keyword_count), formatted_date
    return None, None, None, None

@st.cache_data  # 缓存加载的数据
def load_data(uploaded_file):
    """
    加载上传的Excel文件，并读取第一个sheet的数据。
    """
    if uploaded_file is not None:
        try:
            # 读取第一个sheet
            df = pd.read_excel(uploaded_file, engine='openpyxl', sheet_name=0)
            return df
        except Exception as e:
            st.error(f"加载文件时出错: {e}")
            return None
    return None

# --- 2. Streamlit 页面主函数 ---

def main():
    """
    Streamlit应用的主函数。
    """
    st.set_page_config(page_title="ASIN反查关键词分析面板", layout="wide")

    st.title("📊 ASIN反查关键词分析面板")

    # 文件上传组件
    st.header("上传数据文件")
    uploaded_file = st.file_uploader("请在此处上传您的ASIN反查关键词Excel文件以开始分析", type=["xlsx"])

    # 如果没有上传文件，显示提示信息
    if uploaded_file is None:
        st.info("👋 欢迎使用！请上传文件以开始分析。")
        return

    # 解析文件名并显示信息
    filename = uploaded_file.name
    country, asin, keyword_count, date = parse_filename(filename)

    if asin:
        st.success(f"文件解析成功！**国家:** {country}, **ASIN:** {asin}, **关键词总数:** {keyword_count}, **导出日期:** {date}")
    else:
        st.warning("无法从文件名中解析信息，请检查文件名格式是否为 'ReverseASIN-国家-ASIN(数量)-日期.xlsx'")

    # 加载数据
    df = load_data(uploaded_file)

    if df is not None:
        # 显示核心指标
        display_metrics(df)

        st.markdown("---") # 分隔线

        # 创建两个并排的列用于放置图表
        col1, col2 = st.columns(2)
        with col1:
            plot_top_keywords_by_traffic(df)
        with col2:
            plot_keyword_type_distribution(df)

        # 词云图
        generate_word_cloud(df)

        st.markdown("---") # 分隔线

        # 显示可交互的完整数据表
        st.subheader("详细数据表")
        st.dataframe(df)

# 确保其他函数也使用缓存（如果需要）
@st.cache_data
def display_metrics(df):
    """计算并展示核心业务指标。"""
    # ... (保持原有代码不变)

@st.cache_data
def plot_top_keywords_by_traffic(df):
    """绘制流量占比最高的TOP 10关键词条形图。"""
    # ... (保持原有代码不变)

@st.cache_data
def plot_keyword_type_distribution(df):
    """绘制关键词类型的分布饼图。"""
    # ... (保持原有代码不变)

@st.cache_data
def generate_word_cloud(df):
    """根据“流量词”生成并展示词云。"""
    # ... (保持原有代码不变)

if __name__ == "__main__":
    main()