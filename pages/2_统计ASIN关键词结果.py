import streamlit as st
import pandas as pd
import re
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- 1. 核心功能函数 ---

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

def display_metrics(df):
    """
    计算并展示核心业务指标。
    """
    st.header("核心指标概览")

    # 计算指标
    total_weekly_impressions = df['预估周曝光量'].sum()
    average_supply_demand_ratio = df['需供比'].mean()
    total_purchase = df['购买量'].sum()
    average_purchase_rate = df['购买率'].mean()


    # 创建列来并排显示指标
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("预估周曝光总量", f"{int(total_weekly_impressions):,}")
    col2.metric("平均需供比", f"{average_supply_demand_ratio:.2f}")
    col3.metric("关键词总购买量", f"{int(total_purchase):,}")
    col4.metric("平均购买率", f"{average_purchase_rate:.2%}")


def plot_top_keywords_by_traffic(df):
    """
    绘制流量占比最高的TOP 10关键词条形图。
    """
    st.subheader("流量占比 TOP 10 关键词")
    # 按“流量占比”降序排序并选取前10
    top_10_keywords = df.sort_values(by='流量占比', ascending=False).head(10)

    # 创建条形图
    fig = px.bar(
        top_10_keywords,
        x='流量占比',
        y='流量词',
        orientation='h',
        title='流量占比最高的10个关键词',
        labels={'流量占比': '流量占比 (%)', '流量词': '关键词'},
        text='流量占比' # 在条上显示数值
    )
    # 更新图表布局
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'}, # 让流量最高的在顶部
        xaxis_title="流量占比",
        yaxis_title="关键词"
    )
    fig.update_traces(texttemplate='%{x:.2%}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)


def plot_keyword_type_distribution(df):
    """
    绘制关键词类型的分布饼图。
    """
    st.subheader("关键词类型分布")
    # 统计每种“关键词类型”的数量
    type_counts = df['关键词类型'].value_counts().reset_index()
    type_counts.columns = ['关键词类型', '数量']

    # 创建饼图
    fig = px.pie(
        type_counts,
        names='关键词类型',
        values='数量',
        title='各类关键词数量占比'
    )
    st.plotly_chart(fig, use_container_width=True)

def generate_word_cloud(df):
    """
    根据“流量词”生成并展示词云。
    """
    st.subheader("关键词词云")
    # 将所有“流量词”合并成一个长字符串
    text = " ".join(keyword for keyword in df['流量词'].astype(str))

    try:
        # 创建词云对象
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            collocations=False # 避免重复词语
        ).generate(text)

        # 显示词云
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    except Exception as e:
        st.warning("无法生成词云，可能是因为关键词数据为空。")


# --- 2. Streamlit 页面主函数 ---

def main():
    """
    Streamlit应用的主函数。
    """
    st.set_page_config(page_title="ASIN反查关键词分析面板", layout="wide")

    st.title("📊 ASIN反查关键词分析面板")

    # 创建一个侧边栏用于文件上传
    with st.sidebar:
        st.header("上传数据文件")
        uploaded_file = st.file_uploader("请在此处上传您的Excel文件", type=["xlsx"])

    # 如果没有上传文件，显示提示信息
    if uploaded_file is None:
        st.info("👋 欢迎使用！请在左侧侧边栏上传您的ASIN反查关键词Excel文件以开始分析。")
        return

    # --- 文件处理与数据展示 ---
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

# --- 3. 应用启动 ---

if __name__ == "__main__":
    main()