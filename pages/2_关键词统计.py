import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter
from typing import Optional, Dict, Tuple, List
from io import BytesIO
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏


# --- 核心功能函数 ---
def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    从标准文件名中解析出ASIN等信息。
    文件名格式: ReverseASIN-US-B01N9KSITZ(1584)-20251012.xlsx
    """
    pattern = re.compile(r'ReverseASIN-(.*?)-([A-Z0-9]{10})\(.*\)-\d+')
    match = pattern.match(filename)
    if match:
        return {'country': match.group(1), 'asin': match.group(2)}
    return None


def process_uploaded_file(uploaded_file) -> Optional[Tuple[str, pd.DataFrame, pd.DataFrame]]:
    """
    处理单个上传的Excel文件。
    1. 读取第一个sheet。
    2. 解析文件名获取ASIN。
    3. 创建一个新DataFrame，并在第一列添加ASIN信息。

    Args:
        uploaded_file: Streamlit上传的文件对象。

    Returns:
        Optional[Tuple[str, pd.DataFrame, pd.DataFrame]]:
        一个元组，包含:
        - 原始sheet的名称。
        - 原始sheet的完整DataFrame (用于单独存放)。
        - 添加了ASIN列的DataFrame (用于总表合并)。
        如果文件处理失败或文件名格式不正确，则返回None。
    """
    try:
        # 解析文件名
        file_info = parse_filename(uploaded_file.name)
        if not file_info:
            st.warning(f"文件名 '{uploaded_file.name}' 格式不符合要求，已跳过。")
            return None

        asin = file_info['asin']

        # 读取Excel的第一个sheet
        # `sheet_name=0` 表示读取第一个sheet
        # `engine='openpyxl'` 是为了更好地兼容.xlsx文件
        original_df = pd.read_excel(uploaded_file, sheet_name=0, engine='openpyxl')

        # 获取第一个sheet的名称，用于在新Excel中创建同名sheet
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet_name = xls.sheet_names[0]

        # 准备用于合并到总表的数据
        df_for_consolidation = original_df.copy()
        # 在第一列插入ASIN信息
        df_for_consolidation.insert(0, 'ASIN', asin)

        return sheet_name, original_df, df_for_consolidation

    except Exception as e:
        st.error(f"处理文件 '{uploaded_file.name}' 时出错: {e}")
        return None


def create_excel_file(individual_sheets: Dict[str, pd.DataFrame], consolidated_df: pd.DataFrame) -> BytesIO:
    """
    将处理好的数据写入一个新的Excel文件（在内存中）。

    Args:
        individual_sheets (Dict[str, pd.DataFrame]): 一个字典，键是sheet名，值是对应的原始DataFrame。
        consolidated_df (pd.DataFrame): 整合了所有ASIN信息的总表DataFrame。

    Returns:
        BytesIO: 包含新Excel文件内容的二进制流对象。
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. 写入总表，并将其放在第一个
        consolidated_df.to_excel(writer, sheet_name='总表-所有ASIN整合', index=False)

        # 2. 写入每个独立的ASIN sheet
        for sheet_name, df in individual_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # 重置指针到文件开头，以便st.download_button可以读取它
    output.seek(0)
    return output


# --- 数据分析与可视化函数 ---
def display_key_metrics(df: pd.DataFrame, is_consolidated: bool = False, asin: str = ""):
    """展示关键指标总览。"""
    st.subheader("关键指标总览 (Key Metrics)")

    total_keywords = df['流量词'].nunique()
    total_search_volume = df['月搜索量'].sum()
    total_purchases = df['购买量'].sum()
    avg_purchase_rate = df['购买率'].mean()

    cols = st.columns(4)
    with cols[0]:
        st.metric("关键词总数", f"{total_keywords:,}")
    with cols[1]:
        st.metric("月搜索总量", f"{int(total_search_volume):,}")
    with cols[2]:
        st.metric("月购买总量", f"{int(total_purchases):,}")
    with cols[3]:
        st.metric("平均购买率", f"{avg_purchase_rate:.2%}")

    if is_consolidated:
        total_asins = df['ASIN'].nunique()
        st.info(f"当前数据为 **{total_asins}** 个ASIN的合并分析结果。")
    else:
        st.info(f"当前数据为单个ASIN **{asin}** 的分析结果。")


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
        },
        text="占比"  # 添加文本显示
    )

    # 格式化文本显示
    fig.update_traces(
        texttemplate='%{text:.1%}',  # 显示为百分比格式，保留1位小数
        textposition='inside',  # 文本显示在柱子内部
        insidetextanchor='middle'  # 文本在柱子中间
    )

    fig.update_layout(
        xaxis_title="流量占比",
        yaxis_title="关键词",
        yaxis={'categoryorder': 'total ascending'},
        height=800,
        legend_title_text='流量类型',
        xaxis=dict(
            tickformat=".1%",  # x轴刻度显示为百分比
            range=[0, top_20_traffic["流量占比"].max() * 1.1]  # 调整x轴范围
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def calculate_word_frequency(df: pd.DataFrame) -> Tuple[Dict[str, int], pd.DataFrame]:
    """从流量词列计算单词频率。"""
    words = df['流量词'].dropna().str.lower().str.split().sum()
    word_counts = Counter(words)
    total_words = sum(word_counts.values())

    freq_df = pd.DataFrame(word_counts.items(), columns=['单词', '出现次数'])
    freq_df['频率'] = freq_df['出现次数'] / total_words
    freq_df = freq_df.sort_values(by='出现次数', ascending=False).reset_index(drop=True)

    return word_counts, freq_df


def display_word_frequency_analysis(df: pd.DataFrame):
    """展示单词频率词云和表格。"""
    st.subheader("组成关键词的单词频率 (Word Frequency)")
    word_counts, freq_df = calculate_word_frequency(df)

    if not word_counts:
        st.warning("没有有效的流量词来生成单词频率分析。")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("单词词云")
        wordcloud = WordCloud(
            width=800, height=500, background_color='white',
            max_words=150, collocations=False
        ).generate_from_frequencies(word_counts)
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    with col2:
        st.write("单词频率统计 (Top 20)")
        st.dataframe(
            freq_df.head(20).style.format({"频率": "{:.2%}"}),
            height=500, use_container_width=True
        )

def display_word_cloud(word_counts):
    st.write("单词词云")
    wordcloud = WordCloud(
        width=1600,  # 增大画布尺寸
        height=900,
        background_color=None,
        mode="RGBA",
        # max_words=200,  # 限制单词数量
        max_font_size=200,  # 设置最大字体
        min_font_size=10,  # 设置最小字体
        prefer_horizontal=0.9,  # 调整水平显示偏好
        # relative_scaling=0.5,  # 调整缩放比例
        collocations=False  # 禁用词组
    ).generate_from_frequencies(word_counts)

    # 创建图形时设置更高的DPI
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')

    # 设置图形背景透明
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # 保存为高分辨率图像
    st.pyplot(fig, bbox_inches='tight', pad_inches=0, dpi=300)


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

def plot_search_volume_and_purchases(df: pd.DataFrame):
    """展示关键词搜索量和购买量的堆叠条形图。"""
    st.subheader("关键词搜索量和购买量 (Search Volume and Purchases)")

    df_filtered = df[df['月搜索量'] > 0].copy()
    if df_filtered.empty:
        st.warning("没有有效的月搜索量数据可供展示。")
        return

    top_20_search = df_filtered.sort_values(by="月搜索量", ascending=False).head(20)
    top_20_search["未购买量"] = top_20_search["月搜索量"] - top_20_search["购买量"]

    plot_df = top_20_search.melt(
        id_vars=["流量词", "购买率"],
        value_vars=["购买量", "未购买量"],
        var_name="类型", value_name="数量"
    )

    fig = px.bar(
        plot_df, y="流量词", x="数量", color="类型", orientation='h',
        title="Top 20 关键词搜索量与购买量",
        labels={"流量词": "关键词", "数量": "月搜索量"},
        color_discrete_map={"购买量": "#00CC96", "未购买量": "#FECB52"}
    )

    # 为每个条形添加购买率标注
    annotations = []
    for _, row in top_20_search.iterrows():
        annotations.append(dict(
            x=row['月搜索量'] * 0.98, y=row['流量词'],
            text=f"购买率: {row['购买率']:.2%}",
            showarrow=False, font=dict(color="black", size=10),
            xanchor='right'
        ))
    fig.update_layout(annotations=annotations)

    fig.update_layout(
        xaxis_title="月搜索量", yaxis_title="关键词",
        yaxis={'categoryorder': 'total ascending'}, height=800,
        legend_title_text='类型'
    )
    st.plotly_chart(fig, use_container_width=True)


def display_raw_data(df: pd.DataFrame, title: str = "原始数据 (Raw Data)"):
    """展示原始数据表格。"""
    st.subheader(title)
    st.dataframe(df)


# --- 合并文件后的专属可视化函数 ---

def plot_asin_traffic_contribution(df: pd.DataFrame):
    """展示各ASIN流量贡献对比的柱状图。"""
    st.subheader("各ASIN流量贡献对比 (ASIN Traffic Contribution)")

    # 计算每个ASIN的总流量贡献值（流量占比 * 月搜索量）
    df['流量贡献值'] = df['流量占比'] * df['月搜索量']
    asin_traffic = df.groupby('ASIN')['流量贡献值'].sum().sort_values(ascending=False).reset_index()

    fig = px.bar(
        asin_traffic, x='ASIN', y='流量贡献值',
        title="各ASIN流量贡献值对比",
        labels={'ASIN': '产品ASIN', '流量贡献值': '流量贡献值 (流量占比 * 月搜索量)'},
        text='流量贡献值'
    )
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


def display_aggregated_word_frequency(df: pd.DataFrame):
    """为合并数据展示单词频率表格和词云。"""
    st.subheader("聚合后的单词频率 (Aggregated Word Frequency)")
    word_counts, freq_df = calculate_word_frequency(df)

    if not word_counts:
        st.warning("没有有效的流量词来生成单词频率分析。")
        return

    st.write("单词频率统计表格")
    st.dataframe(freq_df.style.format({"频率": "{:.2%}"}), use_container_width=True)

    st.write("单词词云")
    wordcloud = WordCloud(
        width=1600, height=800, background_color='white',
        max_words=200, collocations=False
    ).generate_from_frequencies(word_counts)
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)


# --- Streamlit 页面主函数 ---

def main():
    st.set_page_config(layout="wide", page_title="ASIN关键词分析面板")
    st.title("📊 ASIN反查关键词数据分析面板")

    uploaded_files = st.file_uploader(
        "请上传一个或多个ASIN反查的Excel文件",
        type="xlsx",
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("请上传文件以开始分析。")
        return

    # --- 单文件处理逻辑 ---
    if len(uploaded_files) == 1:
        uploaded_file = uploaded_files[0]
        result = process_uploaded_file(uploaded_file)
        if result:
            _, df, _ = result
            asin_info = parse_filename(uploaded_file.name)
            asin = asin_info['asin'] if asin_info else "未知"

            st.success(f"成功加载文件: **{uploaded_file.name}**")

            # 单文件仪表盘
            display_key_metrics(df, asin=asin) # todo：新增专用函数
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

            plot_search_volume_and_purchases(df)
            display_raw_data(df)

    # --- 多文件处理逻辑 ---
    elif len(uploaded_files) > 1:
        individual_sheets = {}
        dfs_for_consolidation = []

        with st.spinner("正在处理和合并文件..."):
            for file in uploaded_files:
                result = process_uploaded_file(file)
                if result:
                    sheet_name, original_df, df_for_consolidation = result
                    individual_sheets[sheet_name] = original_df
                    dfs_for_consolidation.append(df_for_consolidation)

        if not dfs_for_consolidation:
            st.error("所有上传的文件都处理失败，请检查文件格式是否正确。")
            return

        consolidated_df = pd.concat(dfs_for_consolidation, ignore_index=True)
        st.success(f"成功合并 **{len(dfs_for_consolidation)}** 个文件！")

        # 提供合并后的文件下载
        excel_bytes = create_excel_file(individual_sheets, consolidated_df)
        st.download_button(
            label="📥 下载合并后的Excel文件",
            data=excel_bytes,
            file_name="Consolidated_ASIN_Keywords.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 创建下拉选择器
        asin_options = ["合并后文件统计信息"] + sorted(list(consolidated_df['ASIN'].unique()))
        choice = st.selectbox("请选择要查看的视图:", asin_options)

        if choice == "合并后文件统计信息":
            display_key_metrics(consolidated_df, is_consolidated=True)
            plot_asin_traffic_contribution(consolidated_df)
            plot_keyword_traffic(consolidated_df)
            display_aggregated_word_frequency(consolidated_df)
            display_raw_data(consolidated_df, title="合并后的数据表 (Consolidated Data)")
        else:
            # 根据选择的ASIN筛选原始数据进行展示
            # 注意：我们需要从合并前的数据中找到对应的DataFrame
            selected_asin_df = None
            for sheet_name, df in individual_sheets.items():
                if choice in sheet_name:
                    selected_asin_df = df
                    break

            if selected_asin_df is not None:
                display_key_metrics(selected_asin_df, asin=choice)
                plot_keyword_traffic(selected_asin_df)
                display_word_frequency_analysis(selected_asin_df)
                plot_search_volume_and_purchases(selected_asin_df)
                display_raw_data(selected_asin_df)


if __name__ == "__main__":
    main()

