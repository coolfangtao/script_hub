import pandas as pd
import streamlit as st
import altair as alt
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏


def load_data(uploaded_file):
    """
    从上传的Excel文件中加载数据，并从文件名中提取ASIN等信息。
    """
    file_details = {}
    file_name = uploaded_file.name
    # 使用正则表达式从文件名解析信息
    match = re.search(r"ReverseASIN-([A-Z]{2})-([A-Z0-9]+)\((\d+)\)-(\d+)", file_name)
    if match:
        file_details['country'] = match.group(1)
        file_details['asin'] = match.group(2)
        file_details['keyword_count'] = int(match.group(3))
        file_details['date'] = match.group(4)

    # 读取Excel文件的第一个sheet
    df = pd.read_excel(uploaded_file, sheet_name=0)

    # 数据清洗和类型转换
    numeric_cols = ['流量占比', '预估周曝光量', '自然流量占比', '广告流量占比', '月搜索量', 'SPR', '需供比', '购买率']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=numeric_cols, inplace=True)
    return df, file_details


def calculate_word_frequency(df):
    """
    从'流量词'列计算单词频率。
    """
    # 将所有流量词合并成一个长字符串，并转换为小写
    text = ' '.join(df['流量词'].dropna().astype(str)).lower()
    # 使用正则表达式找到所有单词
    words = re.findall(r'\b[a-z]+\b', text)
    # 计算每个单词的频率
    word_counts = Counter(words)
    # 转换为DataFrame
    word_df = pd.DataFrame(word_counts.items(), columns=['词语', '出现频次']).sort_values(by='出现频次', ascending=False)
    return word_df


def display_metrics(df):
    """
    计算并以列的形式显示关键指标。
    """
    st.header("关键指标总览 (Key Metrics)")

    total_weekly_impressions = df['预估周曝光量'].sum()

    if df['流量占比'].sum() > 0:
        weighted_natural_traffic = (df['自然流量占比'] * df['流量占比']).sum() / df['流量占比'].sum()
        weighted_ad_traffic = (df['广告流量占比'] * df['流量占比']).sum() / df['流量占比'].sum()
    else:
        weighted_natural_traffic = 0
        weighted_ad_traffic = 0

    avg_spr = df['SPR'].mean()
    avg_supply_demand_ratio = df['需供比'].mean()
    avg_purchase_rate = df['购买率'].mean()
    total_monthly_search = df['月搜索量'].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("预估周曝光总量", f"{total_weekly_impressions:,.0f}")
    col2.metric("平均自然流量占比", f"{weighted_natural_traffic:.2%}")
    col3.metric("平均广告流量占比", f"{weighted_ad_traffic:.2%}")
    col4.metric("月搜索总量", f"{total_monthly_search:,.0f}")

    col5, col6, col7 = st.columns(3)
    col5.metric("平均SPR", f"{avg_spr:.2f}")
    col6.metric("平均供需比", f"{avg_supply_demand_ratio:.2f}")
    col7.metric("平均购买率", f"{avg_purchase_rate:.2%}")


def display_top_keywords_chart(df):
    """
    显示流量占比最高的10个关键词的横向柱状图。
    """
    st.header("流量占比Top 10关键词")
    top_10_keywords = df.nlargest(10, '流量占比')

    chart = alt.Chart(top_10_keywords).mark_bar().encode(
        x=alt.X('流量占比:Q', title='流量占比', axis=alt.Axis(format='%')),
        y=alt.Y('流量词:N', sort='-x', title='关键词'),
        tooltip=['流量词', '流量占比', '预估周曝光量', '月搜索量']
    ).properties(
        title='流量占比Top 10关键词'
    )
    st.altair_chart(chart, use_container_width=True)


def display_traffic_source_distribution(df):
    """
    显示总体流量来源分布的饼图。
    """
    st.header("总体流量来源分布")

    if df['流量占比'].sum() > 0:
        natural_traffic_total = (df['自然流量占比'] * df['流量占比']).sum()
        ad_traffic_total = (df['广告流量占比'] * df['流量占比']).sum()
    else:
        natural_traffic_total = 0
        ad_traffic_total = 0

    source_data = pd.DataFrame({
        '来源': ['自然流量', '广告流量'],
        '占比': [natural_traffic_total, ad_traffic_total]
    })

    chart = alt.Chart(source_data).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="占比", type="quantitative"),
        color=alt.Color(field="来源", type="nominal", title="流量来源"),
        tooltip=['来源', '占比']
    ).properties(
        title='自然流量 vs. 广告流量'
    )
    st.altair_chart(chart, use_container_width=True)


def display_word_cloud(word_df):
    """
    根据单词频率数据生成并显示词云，同时显示包含频率和占比的表格。
    """
    st.header("关键词词云")

    # 词云图只显示频率最高的100个词
    word_df_top100 = word_df.head(100)
    word_freq = dict(zip(word_df_top100['词语'], word_df_top100['出现频次']))

    if word_freq:
        wordcloud = WordCloud(width=800, height=400, background_color='white',
                              collocations=False).generate_from_frequencies(word_freq)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    else:
        st.warning("没有找到可以生成词云的关键词。")

    st.subheader("单词频率详情")
    total_words = word_df['出现频次'].sum()
    if total_words > 0:
        word_df['占比'] = (word_df['出现频次'] / total_words)
        st.dataframe(word_df[['词语', '出现频次', '占比']].style.format({'占比': '{:.2%}'}))
    else:
        st.write("无法计算单词频率。")


def main():
    """
    运行Streamlit应用的主函数。
    """
    st.set_page_config(layout="wide")
    st.title("ASIN关键词分析看板")

    # 将文件上传组件放在主页面
    uploaded_file = st.file_uploader("请在此处上传您的ASIN反查关键词Excel文件", type=["xlsx"])

    if uploaded_file:
        # 加载和处理数据
        df, file_details = load_data(uploaded_file)

        # 从主数据中计算词频
        word_df = calculate_word_frequency(df)

        st.header(f"ASIN: {file_details.get('asin', 'N/A')} 的分析报告")

        # 显示各个分析模块
        display_metrics(df)
        st.markdown("---")
        display_top_keywords_chart(df)
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            display_traffic_source_distribution(df)
        with col2:
            display_word_cloud(word_df)

    else:
        st.info("请上传一个Excel文件以开始分析。")


if __name__ == "__main__":
    main()