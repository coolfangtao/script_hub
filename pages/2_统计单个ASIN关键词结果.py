import streamlit as st
import pandas as pd
import re
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

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

    # 在计算前，强制将相关列转换为数字格式。
    df['预估周曝光量'] = pd.to_numeric(df['预估周曝光量'], errors='coerce')
    df['需供比'] = pd.to_numeric(df['需供比'], errors='coerce')
    df['购买量'] = pd.to_numeric(df['购买量'], errors='coerce')
    # '购买率' 可能包含百分号，需要先移除
    if df['购买率'].dtype == 'object':
         df['购买率'] = pd.to_numeric(df['购买率'].str.replace('%', '', regex=False), errors='coerce') / 100
    else:
        df['购买率'] = pd.to_numeric(df['购买率'], errors='coerce')

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

    # 在绘图前，确保'流量占比'列是数字类型
    if df['流量占比'].dtype == 'object':
        df['流量占比'] = pd.to_numeric(df['流量占比'].str.replace('%', '', regex=False), errors='coerce') / 100
    else:
        df['流量占比'] = pd.to_numeric(df['流量占比'], errors='coerce')

    # 按“流量占比”降序排序并选取前10
    top_10_keywords = df.sort_values(by='流量占比', ascending=False).head(10)

    # 创建条形图
    fig = px.bar(
        top_10_keywords,
        x='流量占比',
        y='流量词',
        orientation='h',
        title='流量占比最高的10个关键词',
        labels={'流量占比': '流量占比', '流量词': '关键词'},
        text='流量占比'
    )
    # 更新图表布局
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        xaxis_title="流量占比",
        yaxis_title="关键词",
        xaxis_tickformat=".2%"
    )
    fig.update_traces(texttemplate='%{x:.2%}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)


def plot_keyword_type_distribution(df):
    """
    绘制关键词类型的分布饼图。
    """
    st.subheader("关键词类型分布")
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
    st.subheader("关键词词云")
    text = " ".join(keyword for keyword in df['流量词'].dropna().astype(str))

    if not text:
        st.warning("关键词数据为空，无法生成词云。")
        return

    try:
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            collocations=False
        ).generate(text)

        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    except Exception as e:
        st.error(f"生成词云时出错: {e}")


# --- 2. Streamlit 页面主函数 (添加了加载状态) ---

def main():
    """
    Streamlit应用的主函数，具有清晰的数据加载和清除逻辑。
    """
    st.set_page_config(page_title="ASIN反查关键词分析面板", layout="wide")

    st.title("📊 ASIN反查关键词分析面板")

    # --- 核心交互逻辑 ---
    # 根据 session_state 中是否存在数据，决定显示“分析报告”还是“文件上传”界面
    if 'processed_data' in st.session_state:
        # --- 状态一：已加载数据，显示分析报告 ---
        df = st.session_state['processed_data']
        info = st.session_state['file_info']

        header_container = st.container()
        with header_container:
            col1, col2 = st.columns([0.85, 0.15]) # 调整宽度比例以适应按钮文字
            with col1:
                if info['asin']:
                    st.success(f"当前分析的文件: **{info['name']}** | 国家: **{info['country']}**, ASIN: **{info['asin']}**, 关键词总数: **{info['keyword_count']}**")
                else:
                    st.warning("无法从文件名中解析信息，请检查文件名格式。")
            with col2:
                if st.button("清除并分析新文件", use_container_width=True):
                    del st.session_state['processed_data']
                    del st.session_state['file_info']
                    st.rerun()

        # --- 显示所有图表和数据 ---
        display_metrics(df.copy())
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            plot_top_keywords_by_traffic(df.copy())
        with col2:
            plot_keyword_type_distribution(df.copy())
        generate_word_cloud(df.copy())
        st.markdown("---")
        st.subheader("详细数据表")
        st.dataframe(df)

    else:
        # --- 状态二：初始状态，显示文件上传界面 ---
        st.header("上传数据文件")
        uploaded_file = st.file_uploader(
            "请在此处上传您的ASIN反查关键词Excel文件以开始分析",
            type=["xlsx"],
            key="file_uploader"
        )

        if uploaded_file is not None:
            # ✨ 新增：使用 st.spinner 显示加载状态
            with st.spinner('正在加载和处理文件，请稍候...'):
                df = load_data(uploaded_file)
                if df is not None:
                    country, asin, keyword_count, date = parse_filename(uploaded_file.name)
                    st.session_state['processed_data'] = df
                    st.session_state['file_info'] = {
                        'name': uploaded_file.name,
                        'country': country,
                        'asin': asin,
                        'keyword_count': keyword_count,
                        'date': date
                    }
                    # 数据处理完成后，重新运行脚本以进入“分析报告”状态
                    st.rerun()
        else:
            st.info("👋 欢迎使用！请上传文件以开始分析。")


# --- 3. 应用启动 ---

if __name__ == "__main__":
    main()
