import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

def display_key_metrics(df):
    """
    展示关键指标总览。

    Args:
        df (pd.DataFrame): 包含关键词数据的DataFrame。
    """
    st.subheader("关键指标总览 (Key Metrics)")

    total_keywords = len(df)
    total_weekly_impressions = df["预估周曝光量"].sum()
    total_monthly_searches = df["月搜索量"].sum()
    total_purchases = df["购买量"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("关键词总数", f"{total_keywords}")
    col2.metric("预估周曝光量总计", f"{int(total_weekly_impressions):,}")
    col3.metric("月搜索量总计", f"{int(total_monthly_searches):,}")
    col4.metric("购买量总计", f"{int(total_purchases):,}")


def plot_keyword_traffic(df):
    """
    展示关键词流量的堆叠条形图。

    Args:
        df (pd.DataFrame): 包含关键词数据的DataFrame。
    """
    st.subheader("关键词流量 (Keyword Traffic)")

    # 选取流量占比最高的前20个关键词
    top_20_traffic = df.sort_values(by="流量占比", ascending=False).head(20)

    # 计算自然流量和广告流量的绝对占比
    top_20_traffic["自然流量绝对占比"] = top_20_traffic["流量占比"] * top_20_traffic["自然流量占比"]
    top_20_traffic["广告流量绝对占比"] = top_20_traffic["流量占比"] * top_20_traffic["广告流量占比"]

    # 融化DataFrame以适配Plotly的格式
    plot_df = top_20_traffic.melt(
        id_vars=["流量词"],
        value_vars=["自然流量绝对占比", "广告流量绝对占比"],
        var_name="流量类型",
        value_name="占比"
    )

    # 绘制图表
    fig = px.bar(
        plot_df,
        y="流量词",
        x="占比",
        color="流量类型",
        orientation='h',
        title="Top 20 关键词流量分布",
        labels={"流量词": "关键词", "占比": "流量占比"},
        color_discrete_map={
            "自然流量绝对占比": "#636EFA",
            "广告流量绝对占比": "#EF553B"
        }
    )

    fig.update_layout(
        xaxis_title="流量占比",
        yaxis_title="关键词",
        yaxis={'categoryorder': 'total ascending'},
        height=800,
        legend_title_text='流量类型'
    )
    st.plotly_chart(fig, use_container_width=True)


def display_word_cloud(word_counts):
    """
    根据词频数据生成并展示词云。

    Args:
        word_counts (Counter): 包含单词及其出现次数的Counter对象。
    """
    st.write("单词词云")
    wordcloud = WordCloud(
        width=800,
        height=600,
        background_color=None, # 设置为None以获得透明背景
        mode="RGBA" # 确保使用RGBA模式以支持透明度
    ).generate_from_frequencies(word_counts)

    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)


def display_frequency_table(freq_df):
    """
    展示格式化后的单词频率统计表格。

    Args:
        freq_df (pd.DataFrame): 包含单词、出现次数和频率的DataFrame。
    """
    st.write("单词频率统计")
    st.dataframe(
        freq_df.head(20).style.format({"频率": "{:.2%}"}),
        height=600,
        use_container_width=True
    )


def plot_search_volume_and_clicks(df):
    """
    展示关键词搜索量和购买量的堆叠条形图。

    Args:
        df (pd.DataFrame): 包含关键词数据的DataFrame。
    """
    st.subheader("关键词搜索量和购买量 (Search Volume and Purchases)")

    # 选取月搜索量最高的前20个关键词
    top_20_search = df.sort_values(by="月搜索量", ascending=False).head(20)

    # 计算未购买的量
    top_20_search["未购买量"] = top_20_search["月搜索量"] - top_20_search["购买量"]

    # 融化DataFrame
    plot_df = top_20_search.melt(
        id_vars=["流量词", "购买率"],
        value_vars=["购买量", "未购买量"],
        var_name="类型",
        value_name="数量"
    )

    # 绘制图表
    fig = px.bar(
        plot_df,
        y="流量词",
        x="数量",
        color="类型",
        orientation='h',
        title="Top 20 关键词搜索量与购买量",
        labels={"流量词": "关键词", "数量": "月搜索量"},
        color_discrete_map={
            "购买量": "#00CC96",
            "未购买量": "#FECB52"
        }
    )

    # 添加标注，使其位于整个柱子的中间
    for index, row in top_20_search.iterrows():
        fig.add_annotation(
            x=row['月搜索量'] / 2,  # X轴位置为总长度的一半
            y=row['流量词'],  # Y轴位置为关键词
            text=f"购买率: {row['购买率']:.2%}",
            showarrow=False,
            font=dict(
                color="black",
                size=12
            )
        )

    fig.update_layout(
        xaxis_title="月搜索量",
        yaxis_title="关键词",
        yaxis={'categoryorder': 'total ascending'},
        height=800,
        legend_title_text='类型'
    )
    st.plotly_chart(fig, use_container_width=True)


def display_raw_data(df):
    """
    在页面底部展示完整的原始数据表格。

    Args:
        df (pd.DataFrame): 包含关键词数据的DataFrame。
    """
    st.subheader("原始数据 (Raw Data)")
    st.dataframe(df)


def main():
    """
    Streamlit应用的主函数。
    """
    st.set_page_config(layout="wide", page_title="ASIN关键词分析")
    st.title("ASIN反查关键词分析工具")

    uploaded_file = st.file_uploader("请上传你的Excel或CSV文件", type=["xlsx", "csv"])

    # 文件上传后直接分析，无需按钮
    if uploaded_file is not None:
        try:
            with st.spinner('正在分析数据，请稍候...'):
                # 根据文件类型读取数据
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, sheet_name=0)

                # 显示关键指标
                display_key_metrics(df)

                # 显示关键词流量图
                plot_keyword_traffic(df)

                # --- 词频分析 ---
                st.subheader("组成关键词的单词频率 (Word Frequency)")

                # 1. 计算词频 (公共逻辑)
                text = ' '.join(df['流量词'].dropna())
                words = re.findall(r'\b\w+\b', text.lower())
                word_counts = Counter(words)
                total_words = sum(word_counts.values())
                freq_df = pd.DataFrame(word_counts.items(), columns=["单词", "出现次数"])
                freq_df["频率"] = freq_df["出现次数"] / total_words
                freq_df = freq_df.sort_values(by="出现次数", ascending=False)

                # 2. 依次展示词云和表格
                display_word_cloud(word_counts)
                display_frequency_table(freq_df)

                # 显示搜索量和购买量
                plot_search_volume_and_clicks(df)

                # 新增：显示原始数据
                display_raw_data(df)

            st.success("分析完成！")

        except Exception as e:
            st.error(f"处理文件时出错: {e}")


if __name__ == "__main__":
    main()