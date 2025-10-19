import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from shared.sidebar import create_sidebar # <-- 1. 导入函数
create_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 1. 核心功能函数 ---
def load_merged_data(uploaded_file):
    """
    加载上传的Excel文件，并专门读取名为'总表-所有ASIN整合'的sheet。
    """
    if uploaded_file is not None:
        try:
            # 读取指定的sheet
            df = pd.read_excel(uploaded_file, sheet_name='总表-所有ASIN整合', engine='openpyxl')
            return df
        except ValueError:
            st.error("错误：上传的Excel文件中未找到名为 '总表-所有ASIN整合' 的Sheet。请检查文件内容。")
            return None
        except Exception as e:
            st.error(f"加载文件时出错: {e}")
            return None
    return None

def clean_data(df):
    """
    对数据进行清洗，特别是将关键指标列转换为数值类型。
    """
    # 定义需要转换为数值的列
    numeric_cols = ['流量占比', '预估周曝光量', '需供比', '购买量', '购买率']
    for col in numeric_cols:
        if col in df.columns:
            # '购买率' 可能包含百分号，需要特殊处理
            if df[col].dtype == 'object' and col == '购买率':
                df[col] = df[col].astype(str).str.replace('%', '', regex=False)

            df[col] = pd.to_numeric(df[col], errors='coerce')

            # 如果是购买率，转换回百分比小数
            if col == '购买率':
                 df[col] = df[col] / 100
    return df


def display_metrics(df):
    """
    根据筛选后的数据，计算并展示核心业务指标。
    """
    st.header("核心指标概览 (已聚合)")

    if df.empty:
        st.warning("当前筛选条件下无数据。")
        return

    # 计算指标
    total_weekly_impressions = df['预估周曝光量'].sum()
    average_supply_demand_ratio = df['需供比'].mean()
    total_purchase = df['购买量'].sum()
    # 购买率的平均值应该基于总购买量/总点击量（如果可用），这里为简化先用平均值
    average_purchase_rate = df['购买率'].mean()

    # 创建列来并排显示指标
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("预估周曝光总量", f"{int(total_weekly_impressions):,}")
    col2.metric("平均需供比", f"{average_supply_demand_ratio:.2f}")
    col3.metric("关键词总购买量", f"{int(total_purchase):,}")
    col4.metric("平均购买率", f"{average_purchase_rate:.2%}")


def plot_asin_contribution(df):
    """
    (新增功能) 绘制各ASIN的流量贡献对比图。
    """
    st.subheader("各ASIN流量贡献对比")
    if df.empty or 'ASIN' not in df.columns:
        st.warning("无数据显示或缺少ASIN列。")
        return

    # 按ASIN分组，计算每个ASIN的预估周曝光量总和
    asin_performance = df.groupby('ASIN')['预估周曝光量'].sum().sort_values(ascending=False).reset_index()

    fig = px.bar(
        asin_performance,
        x='ASIN',
        y='预估周曝光量',
        title='各ASIN总预估周曝光量对比',
        labels={'预估周曝光量': '预估周曝光量总和', 'ASIN': 'ASIN'},
        text='预估周曝光量'
    )
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

def plot_aggregated_top_keywords(df):
    """
    根据多个ASIN的数据，聚合计算并绘制流量最高的TOP 10关键词。
    """
    st.subheader("TOP 10 聚合流量关键词")
    if df.empty:
        st.warning("当前筛选条件下无数据。")
        return

    # 按“流量词”分组，并加总“预估周曝光量”
    top_keywords = df.groupby('流量词')['预估周曝光量'].sum().sort_values(ascending=False).head(10).reset_index()

    fig = px.bar(
        top_keywords,
        x='预估周曝光量',
        y='流量词',
        orientation='h',
        title='预估周曝光量最高的10个关键词 (已聚合)',
        labels={'预估周曝光量': '预估周曝光量总和', '流量词': '关键词'},
        text='预估周曝光量'
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    fig.update_traces(texttemplate='%{x:,.0f}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)


def plot_keyword_type_distribution(df):
    """
    绘制关键词类型的分布饼图。
    """
    st.subheader("关键词类型分布 (已聚合)")
    if df.empty:
        st.warning("当前筛选条件下无数据。")
        return

    type_counts = df['关键词类型'].value_counts().reset_index()
    type_counts.columns = ['关键词类型', '数量']

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
    st.subheader("关键词词云 (已聚合)")
    if df.empty:
        st.warning("当前筛选条件下无数据。")
        return

    text = " ".join(keyword for keyword in df['流量词'].dropna().astype(str))
    if not text:
        st.warning("关键词数据为空，无法生成词云。")
        return

    wordcloud = WordCloud(width=800, height=400, background_color='white', collocations=False).generate(text)
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)


# --- 2. Streamlit 页面主函数 ---

def main():
    """
    多ASIN分析面板的主函数。
    """
    st.set_page_config(page_title="多ASIN关键词分析面板", layout="wide")
    st.title("📊 多ASIN反查关键词分析面板")

    # --- 侧边栏 ---
    with st.sidebar:
        st.header("上传与筛选")
        uploaded_file = st.file_uploader("上传合并后的Excel文件", type=["xlsx"])

        # 占位符，用于之后显示ASIN筛选器
        filter_container = st.container()

    if uploaded_file is None:
        st.info("👋 欢迎使用！请在左侧上传包含 '总表-所有ASIN整合' Sheet的Excel文件以开始分析。")
        return

    # --- 数据加载与处理 ---
    df_original = load_merged_data(uploaded_file)
    if df_original is None:
        return # 如果加载失败，则停止执行

    # 清洗数据
    df_cleaned = clean_data(df_original.copy())

    # --- 在侧边栏中动态创建ASIN筛选器 ---
    all_asins = df_cleaned['ASIN'].unique()
    selected_asins = filter_container.multiselect("选择要分析的ASIN (可多选)", options=all_asins, default=all_asins)

    # 根据选择筛选数据
    if selected_asins:
        df_filtered = df_cleaned[df_cleaned['ASIN'].isin(selected_asins)]
    else:
        # 如果没有选择任何ASIN，则显示空状态
        st.warning("请至少选择一个ASIN进行分析。")
        return

    # --- 页面主内容展示 ---
    display_metrics(df_filtered)
    st.markdown("---")

    # 新增的ASIN对比图
    if len(selected_asins) > 1: # 仅在选择多个ASIN时显示对比图才有意义
        plot_asin_contribution(df_filtered)
        st.markdown("---")

    # 聚合图表
    col1, col2 = st.columns(2)
    with col1:
        plot_aggregated_top_keywords(df_filtered)
    with col2:
        plot_keyword_type_distribution(df_filtered)

    generate_word_cloud(df_filtered)
    st.markdown("---")

    # 详细数据表
    st.subheader("详细数据表 (已筛选)")
    st.dataframe(df_filtered)

# --- 3. 应用启动 ---

if __name__ == "__main__":
    main()