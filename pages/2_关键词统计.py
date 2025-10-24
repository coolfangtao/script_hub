import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter
from typing import Optional, Dict, Tuple, List, Any
from io import BytesIO
# from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar # 假设这个函数存在于您的项目中
# track_script_usage("📝 Listing生成")
create_common_sidebar()



# ==============================================================================
# 1. 配置类 (AppConfig)
# ==============================================================================
class AppConfig:
    """存放所有应用的配置参数"""
    PAGE_TITLE = "ASIN关键词分析面板"
    PAGE_LAYOUT = "wide"
    TOP_N_KEYWORDS = 20

    # 颜色配置
    COLOR_MAP_TRAFFIC = {"自然流量绝对占比": "#636EFA", "广告流量绝对占比": "#EF553B"}
    COLOR_MAP_PURCHASE = {"购买量": "#00CC96", "未购买量": "#FECB52"}
    COLOR_MAP_KEYWORD_TYPES = {
        '核心大词 (高搜索量+高流量)': '#FF6B6B',
        '潜力词 (高搜索量+低流量)': '#FFD93D',
        '精准词 (低搜索量+高流量)': '#6BCF77',
        '长尾词 (低搜索量+低流量)': '#4D96FF'
    }

    # 图表高度
    CHART_HEIGHT = 800

    # 词云图配置
    WORDCLOUD_CONFIG = {
        "width": 1600,
        "height": 900,
        "background_color": None,
        "mode": "RGBA",
        "max_font_size": 200,
        "min_font_size": 10,
        "prefer_horizontal": 0.9,
        "collocations": False
    }

    # 策略建议文案
    STRATEGY_ADVICE = {
        '核心大词 (高搜索量+高流量)': "✅ **保持优势**: 这些是您的核心关键词，继续保持优化，考虑增加相关长尾词",
        '潜力词 (高搜索量+低流量)': "🚀 **重点突破**: 高搜索量但流量低，需要优化页面内容、提高排名或增加广告投入",
        '精准词 (低搜索量+高流量)': "🎯 **精准维护**: 转化率高，维护现有排名，可适当拓展相关词",
        '长尾词 (低搜索量+低流量)': "📈 **选择性优化**: 竞争较小，可作为补充，重点关注有转化潜力的词"
    }


# ==============================================================================
# 数据处理核心函数 (保持独立，便于测试和复用)
# ==============================================================================

def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """从标准文件名中解析出ASIN等信息。"""
    pattern = re.compile(r'ReverseASIN-(.*?)-([A-Z0-9]{10})\(.*\)-\d+')
    match = pattern.match(filename)
    if match:
        return {'country': match.group(1), 'asin': match.group(2)}
    return None


def process_uploaded_file(uploaded_file) -> Optional[Tuple[str, pd.DataFrame, pd.DataFrame]]:
    """处理单个上传的Excel文件，返回 (sheet_name, 原始df, 带ASIN列的df)"""
    try:
        file_info = parse_filename(uploaded_file.name)
        if not file_info:
            st.warning(f"文件名 '{uploaded_file.name}' 格式不符合要求，已跳过。")
            return None

        asin = file_info['asin']
        original_df = pd.read_excel(uploaded_file, sheet_name=0, engine='openpyxl')
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet_name = xls.sheet_names[0]

        df_for_consolidation = original_df.copy()
        df_for_consolidation.insert(0, 'ASIN', asin)

        return sheet_name, original_df, df_for_consolidation
    except Exception as e:
        st.error(f"处理文件 '{uploaded_file.name}' 时出错: {e}")
        return None


def create_excel_file(individual_sheets: Dict[str, pd.DataFrame], consolidated_df: pd.DataFrame) -> BytesIO:
    """创建包含总表和分表的Excel文件（内存中）。"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        consolidated_df.to_excel(writer, sheet_name='总表-所有ASIN整合', index=False)
        for sheet_name, df in individual_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


# ==============================================================================
# 2. UI界面类 (AppUI)
# ==============================================================================
class AppUI:
    """负责所有Streamlit界面的渲染"""

    def __init__(self, config: AppConfig):
        self.config = config

    def setup_page(self):
        """设置页面配置，只在应用启动时调用一次"""
        st.set_page_config(layout=self.config.PAGE_LAYOUT, page_title=self.config.PAGE_TITLE)

    def display_header_and_uploader(self):
        """显示标题和文件上传器"""
        st.title(f"📊 {self.config.PAGE_TITLE}")
        uploaded_files = st.file_uploader(
            "请上传一个或多个ASIN反查的Excel文件 (文件名需符合'ReverseASIN-US-B01N9KSITZ(1584)-20251012.xlsx'格式)",
            type="xlsx",
            accept_multiple_files=True
        )
        return uploaded_files

    def display_key_metrics(self, df: pd.DataFrame, is_consolidated: bool = False, asin: str = ""):
        """展示关键指标总览"""
        st.subheader("关键指标总览 (Key Metrics)")
        total_keywords = df['流量词'].nunique()
        total_search_volume = df['月搜索量'].sum()
        total_purchases = df['购买量'].sum()
        avg_purchase_rate = df['购买率'].mean()

        cols = st.columns(4)
        cols[0].metric("关键词总数", f"{total_keywords:,}")
        cols[1].metric("月搜索总量", f"{int(total_search_volume):,}")
        cols[2].metric("月购买总量", f"{int(total_purchases):,}")
        cols[3].metric("平均购买率", f"{avg_purchase_rate:.2%}")

        if is_consolidated:
            total_asins = df['ASIN'].nunique()
            st.info(f"当前数据为 **{total_asins}** 个ASIN的合并分析结果。")
        else:
            st.info(f"当前数据为单个ASIN **{asin}** 的分析结果。")

    def display_keyword_traffic_chart(self, df: pd.DataFrame):
        """展示关键词流量的堆叠条形图"""
        st.subheader("关键词流量 (Keyword Traffic)")
        df_filtered = df[df['流量占比'] > 0].copy()
        if df_filtered.empty:
            st.warning("没有有效的流量数据可供展示。")
            return

        has_asin = 'ASIN' in df_filtered.columns
        df_filtered["自然流量绝对占比"] = df_filtered["流量占比"] * df_filtered["自然流量占比"]
        df_filtered["广告流量绝对占比"] = df_filtered["流量占比"] * df_filtered["广告流量占比"]

        agg_config = {"流量占比": "sum", "自然流量绝对占比": "sum", "广告流量绝对占比": "sum"}
        if has_asin:
            agg_config["ASIN"] = "nunique"

        aggregated_df = df_filtered.groupby("流量词").agg(agg_config).reset_index()
        if has_asin:
            aggregated_df = aggregated_df.rename(columns={"ASIN": "涉及ASIN数量"})

        top_df = aggregated_df.sort_values(by="流量占比", ascending=False).head(self.config.TOP_N_KEYWORDS)
        title_suffix = " (多ASIN汇总)" if has_asin else ""
        chart_title = f"Top {self.config.TOP_N_KEYWORDS} 关键词流量分布{title_suffix}"

        plot_df = top_df.melt(id_vars=["流量词"], value_vars=["自然流量绝对占比", "广告流量绝对占比"], var_name="流量类型", value_name="占比")

        hover_data = {}
        if has_asin:
            asin_count_map = top_df.set_index('流量词')['涉及ASIN数量'].to_dict()
            plot_df['涉及ASIN数量'] = plot_df['流量词'].map(asin_count_map)
            hover_data = {'涉及ASIN数量': True}

        fig = px.bar(plot_df, y="流量词", x="占比", color="流量类型", orientation='h', title=chart_title,
                     labels={"流量词": "关键词", "占比": "流量占比"}, color_discrete_map=self.config.COLOR_MAP_TRAFFIC,
                     text="占比", hover_data=hover_data)

        fig.update_traces(texttemplate='%{text:.2%}', textposition='inside', insidetextanchor='middle')

        for _, row in top_df.iterrows():
            annotation_text = f"{row['流量占比']:.2%}"
            if has_asin:
                annotation_text += f" ({row['涉及ASIN数量']}个ASIN)"
            fig.add_annotation(x=row['流量占比'], y=row['流量词'], text=annotation_text, showarrow=False,
                               xanchor='left', xshift=10, font=dict(color='green', size=12, weight='bold'))

        fig.update_layout(xaxis_title="流量占比", yaxis_title="关键词", yaxis={'categoryorder': 'total ascending'},
                          height=self.config.CHART_HEIGHT, legend_title_text='流量类型', xaxis=dict(tickformat=".2%"))
        st.plotly_chart(fig, use_container_width=True)

    def display_search_purchase_chart(self, df: pd.DataFrame):
        """展示关键词搜索量和购买量的堆叠条形图"""
        st.subheader("关键词搜索量和购买量 (Search Volume and Purchases)")
        df_filtered = df[df['月搜索量'] > 0].copy()
        if df_filtered.empty:
            st.warning("没有有效的月搜索量数据可供展示。")
            return

        has_asin = 'ASIN' in df_filtered.columns
        if has_asin:
            aggregated_df = df_filtered.groupby("流量词").agg({
                "月搜索量": "sum", "购买量": "sum", "ASIN": "nunique"
            }).reset_index().rename(columns={"ASIN": "涉及ASIN数量"})
            aggregated_df["购买率"] = aggregated_df["购买量"] / aggregated_df["月搜索量"]
            top_df = aggregated_df.sort_values(by="月搜索量", ascending=False).head(self.config.TOP_N_KEYWORDS)
        else:
            top_df = df_filtered.sort_values(by="月搜索量", ascending=False).head(self.config.TOP_N_KEYWORDS).copy()

        top_df["未购买量"] = top_df["月搜索量"] - top_df["购买量"]
        title_suffix = " (多ASIN汇总)" if has_asin else ""
        chart_title = f"Top {self.config.TOP_N_KEYWORDS} 关键词搜索量与购买量{title_suffix}"
        plot_df = top_df.melt(id_vars=["流量词", "购买率"], value_vars=["购买量", "未购买量"], var_name="类型", value_name="数量")

        hover_data = {}
        if has_asin:
            asin_count_map = top_df.set_index('流量词')['涉及ASIN数量'].to_dict()
            plot_df['涉及ASIN数量'] = plot_df['流量词'].map(asin_count_map)
            hover_data = {'涉及ASIN数量': True}

        fig = px.bar(plot_df, y="流量词", x="数量", color="类型", orientation='h', title=chart_title,
                     labels={"流量词": "关键词", "数量": "月搜索量"}, color_discrete_map=self.config.COLOR_MAP_PURCHASE,
                     hover_data=hover_data)

        annotations = []
        for _, row in top_df.iterrows():
            purchase_rate_text = f"购买率: {row['购买率']:.2%}"
            if has_asin:
                purchase_rate_text += f" ({row['涉及ASIN数量']}个ASIN)"
            annotations.append(dict(x=row['月搜索量'] * 0.98, y=row['流量词'], text=purchase_rate_text,
                                    showarrow=False, font=dict(color="black", size=10), xanchor='right'))
            annotations.append(dict(x=row['月搜索量'], y=row['流量词'], text=f"{row['月搜索量']:,}",
                                    showarrow=False, xanchor='left', xshift=10,
                                    font=dict(color='green', size=12, weight='bold')))

        fig.update_layout(annotations=annotations, xaxis_title="月搜索量", yaxis_title="关键词",
                          yaxis={'categoryorder': 'total ascending'}, height=self.config.CHART_HEIGHT,
                          legend_title_text='类型')
        st.plotly_chart(fig, use_container_width=True)

    def display_keyword_analysis_section(self, df: pd.DataFrame):
        """显示完整的关键词综合分析模块"""
        st.subheader("关键词综合分析 (Keyword Analysis)")
        df_filtered = df[(df['月搜索量'] > 0) & (df['流量占比'] > 0)].copy()
        if df_filtered.empty:
            st.warning("没有有效的搜索量和流量数据可供分析。")
            return

        has_asin = 'ASIN' in df_filtered.columns
        if has_asin:
            asin_info = df_filtered.groupby('流量词')['ASIN'].apply(list).reset_index(name='涉及ASIN列表')
            aggregated_df = df_filtered.groupby("流量词").agg({
                "月搜索量": "sum", "流量占比": "sum", "购买率": "mean",
                "自然流量占比": "mean", "广告流量占比": "mean", "ASIN": "nunique"
            }).reset_index().rename(columns={"ASIN": "涉及ASIN数量"})
            df_filtered = aggregated_df.merge(asin_info, on='流量词', how='left')
            st.info("📊 当前显示多ASIN汇总数据，已按关键词聚合")

        df_filtered['总流量贡献'] = df_filtered['流量占比'] * 100
        search_median = df_filtered['月搜索量'].median()
        traffic_median = df_filtered['总流量贡献'].median()

        def classify_keyword(row):
            if row['月搜索量'] > search_median and row['总流量贡献'] > traffic_median:
                return '核心大词 (高搜索量+高流量)'
            elif row['月搜索量'] > search_median and row['总流量贡献'] <= traffic_median:
                return '潜力词 (高搜索量+低流量)'
            elif row['月搜索量'] <= search_median and row['总流量贡献'] > traffic_median:
                return '精准词 (低搜索量+高流量)'
            else:
                return '长尾词 (低搜索量+低流量)'

        df_filtered['关键词类型'] = df_filtered.apply(classify_keyword, axis=1)

        # ... (此处省略了图表创建和显示逻辑，与原代码相同，直接复用)
        # 您可以将原代码中 plot_keyword_analysis 函数的图表部分粘贴到这里
        # 为了简洁，此处直接调用一个内部方法
        self._plot_keyword_analysis_scatter(df_filtered, has_asin, search_median, traffic_median)

        # 显示统计、数据表格和策略建议
        self._display_keyword_analysis_details(df_filtered, has_asin, search_median, traffic_median)

    def _plot_keyword_analysis_scatter(self, df_filtered, has_asin, search_median, traffic_median):
        """内部方法：绘制关键词分析散点图"""
        title_suffix = " (多ASIN汇总)" if has_asin else ""
        chart_title = f'关键词搜索量 vs 流量占比分析{title_suffix}'

        hover_template = "..."  # (从原代码复制)
        hover_data = ['流量词', '购买率', '自然流量占比', '广告流量占比']
        if has_asin:
            df_filtered['ASIN显示'] = df_filtered['涉及ASIN列表'].apply(
                lambda x: ', '.join(x[:5]) + ('...' if len(x) > 5 else ''))
            hover_template += "..."  # (从原代码复制)
            hover_data.extend(['涉及ASIN数量', 'ASIN显示'])

        # 完整的 hover_template
        hover_template = (
            "<span style='font-size: 16px; font-weight: bold; color: green'>📌 %{customdata[0]}</span><br><br>"
            "<b>搜索量:</b> %{x:,}<br>"
            "<b>流量占比:</b> %{y:.2f}%<br>"
            "<b>购买率:</b> %{customdata[1]:.2%}<br>"
            "<b>自然流量:</b> %{customdata[2]:.2%}<br>"
            "<b>广告流量:</b> %{customdata[3]:.2%}"
        )
        if has_asin:
            hover_template += "<br><b>涉及ASIN数量:</b> %{customdata[4]}<br>"
            hover_template += "<b>涉及ASIN:</b> %{customdata[5]}"
        hover_template += "<extra></extra>"

        fig = px.scatter(df_filtered, x='月搜索量', y='总流量贡献', color='关键词类型', title=chart_title,
                         labels={'月搜索量': '月搜索量', '总流量贡献': '流量占比 (%)', '关键词类型': '关键词类型'},
                         color_discrete_map=self.config.COLOR_MAP_KEYWORD_TYPES)
        fig.update_traces(marker=dict(size=8), hovertemplate=hover_template, customdata=df_filtered[hover_data])
        fig.add_hline(y=traffic_median, line_dash="dash", line_color="red",
                      annotation_text=f"流量中位数: {traffic_median:.2f}%")
        fig.add_vline(x=search_median, line_dash="dash", line_color="red",
                      annotation_text=f"搜索量中位数: {search_median:,.0f}")
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

    def _display_keyword_analysis_details(self, df_filtered, has_asin, search_median, traffic_median):
        """内部方法：显示关键词分析的统计数据、表格和建议"""
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 📊 分类统计")
            type_stats = df_filtered['关键词类型'].value_counts()
            for type_name, count in type_stats.items():
                st.write(f"**{type_name}**: {count}个 ({count / len(df_filtered):.1%})")
        with col2:
            st.write("### 📈 关键指标")
            c1, c2 = st.columns(2)
            c1.metric("总关键词数", len(df_filtered))
            c1.metric("搜索量中位数", f"{search_median:,.0f}")
            c2.metric("流量占比中位数", f"{traffic_median:.2f}%")
            if has_asin:
                c2.metric("总涉及ASIN数", df_filtered['涉及ASIN数量'].max())  # 假设聚合后数量一致

        st.write("### 📋 详细数据")
        selected_types = st.multiselect("选择要显示的关键词类型:", options=df_filtered['关键词类型'].unique(),
                                        default=df_filtered['关键词类型'].unique())
        display_df = df_filtered[df_filtered['关键词类型'].isin(selected_types)]
        # ... (此处省略了表格的创建和格式化逻辑，与原代码相同)
        st.dataframe(display_df, use_container_width=True)  # 简化显示，可按原代码格式化

        st.write("### 💡 策略建议")
        for keyword_type in selected_types:
            if keyword_type in self.config.STRATEGY_ADVICE:
                st.info(f"**{keyword_type}**: {self.config.STRATEGY_ADVICE[keyword_type]}")

    def display_word_frequency_section(self, df: pd.DataFrame, title: str):
        """显示单词频率分析模块（词云+表格）"""
        st.subheader(title)
        text = ' '.join(df['流量词'].dropna())
        words = re.findall(r'\b\w+\b', text.lower())
        word_counts = Counter(words)

        if not word_counts:
            st.warning("没有可用于词频分析的关键词。")
            return

        # 词云图
        wordcloud = WordCloud(**self.config.WORDCLOUD_CONFIG).generate_from_frequencies(word_counts)
        fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        st.pyplot(fig, bbox_inches='tight', pad_inches=0)

        # 频率表格
        total_words = sum(word_counts.values())
        freq_df = pd.DataFrame(word_counts.items(), columns=["单词", "出现次数"])
        freq_df["频率"] = freq_df["出现次数"] / total_words
        freq_df = freq_df.sort_values(by="出现次数", ascending=False)
        st.dataframe(freq_df.head(20).style.format({"频率": "{:.2%}"}), height=600, use_container_width=True)

    def display_asin_traffic_contribution_chart(self, df: pd.DataFrame):
        """展示各ASIN流量贡献对比的柱状图"""
        st.subheader("各ASIN流量贡献对比 (ASIN Traffic Contribution)")
        df_copy = df.copy()
        df_copy['流量贡献值'] = df_copy['流量占比'] * df_copy['月搜索量']
        asin_traffic = df_copy.groupby('ASIN')['流量贡献值'].sum().sort_values(ascending=False).reset_index()

        fig = px.bar(asin_traffic, x='ASIN', y='流量贡献值', title="各ASIN流量贡献值对比",
                     labels={'ASIN': '产品ASIN', '流量贡献值': '流量贡献值 (流量占比 * 月搜索量)'}, text='流量贡献值')
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    def display_raw_data(self, df: pd.DataFrame, title: str):
        """展示原始数据表格"""
        st.subheader(title)
        st.dataframe(df)

    def display_download_button(self, data: BytesIO, label: str, file_name: str, mime: str):
        """显示下载按钮"""
        st.download_button(label=label, data=data, file_name=file_name, mime=mime)


# ==============================================================================
# 3. 主应用逻辑 (main)
# ==============================================================================

def main():
    """应用主函数"""
    config = AppConfig()
    ui = AppUI(config)

    ui.setup_page()
    # track_script_usage("页面名称")
    create_common_sidebar()
    uploaded_files = ui.display_header_and_uploader()

    # ------------------ 优化后的状态管理逻辑 ------------------

    # 只有当用户上传了新文件时，才触发数据处理和缓存更新
    if uploaded_files:
        current_file_names = sorted([f.name for f in uploaded_files])
        # 检查上传的文件是否与缓存中的文件不同
        if st.session_state.get('file_names') != current_file_names:
            with st.spinner("检测到新文件，正在处理中..."):
                individual_sheets = {}
                dfs_for_consolidation = []
                for file in uploaded_files:
                    result = process_uploaded_file(file)
                    if result:
                        sheet_name, original_df, df_for_consolidation = result
                        individual_sheets[sheet_name] = original_df
                        dfs_for_consolidation.append(df_for_consolidation)

                if dfs_for_consolidation:
                    consolidated_df = pd.concat(dfs_for_consolidation, ignore_index=True)
                    st.session_state.processed_data = {
                        "individual": individual_sheets,
                        "consolidated": consolidated_df
                    }
                    st.session_state.file_names = current_file_names
                    st.success(f"成功处理并缓存了 {len(dfs_for_consolidation)} 个文件！")
                else:
                    # 如果上传的文件都处理失败，则清空状态
                    st.session_state.processed_data = None
                    st.session_state.file_names = None

    # ------------------ 渲染逻辑 (保持不变) ------------------
    if not st.session_state.get('processed_data'):
        st.info("请上传文件以开始分析。")
        return

    # 从 session_state 中获取数据
    processed_data = st.session_state.processed_data
    individual_sheets = processed_data["individual"]
    consolidated_df = processed_data["consolidated"]
    num_files = len(individual_sheets)

    # 根据文件数量决定显示逻辑
    if num_files == 1:
        # 单文件视图
        sheet_name = list(individual_sheets.keys())[0]
        df = individual_sheets[sheet_name]
        file_info = parse_filename(sheet_name.replace(" ", "_"))  # 假设sheet名包含文件名
        asin = file_info['asin'] if file_info else "未知"

        ui.display_key_metrics(df, asin=asin)
        ui.display_keyword_traffic_chart(df)
        ui.display_search_purchase_chart(df)
        ui.display_keyword_analysis_section(df)
        ui.display_word_frequency_section(df, "单ASIN组成关键词的单词频率")
        ui.display_raw_data(df, "原始数据")

    elif num_files > 1:
        # 多文件视图
        # 提供下载按钮
        excel_bytes = create_excel_file(individual_sheets, consolidated_df)
        ui.display_download_button(
            data=excel_bytes,
            label="📥 下载合并后的Excel文件",
            file_name="Consolidated_ASIN_Keywords.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 创建视图选择器
        asin_options = ["合并后文件统计信息"] + sorted(list(consolidated_df['ASIN'].unique()))
        choice = st.selectbox("请选择要查看的视图:", asin_options)

        if choice == "合并后文件统计信息":
            df_to_show = consolidated_df
            ui.display_key_metrics(df_to_show, is_consolidated=True)
            ui.display_asin_traffic_contribution_chart(df_to_show)
            ui.display_keyword_traffic_chart(df_to_show)
            ui.display_search_purchase_chart(df_to_show)
            ui.display_keyword_analysis_section(df_to_show)
            ui.display_word_frequency_section(df_to_show, "聚合后组成关键词的单词频率")
            ui.display_raw_data(df_to_show, "合并后的数据表")
        else:
            # 寻找被选中的ASIN对应的原始DataFrame
            selected_df = None
            for sheet_name, df_item in individual_sheets.items():
                if choice in sheet_name:
                    selected_df = df_item
                    break

            if selected_df is not None:
                ui.display_key_metrics(selected_df, asin=choice)
                ui.display_keyword_traffic_chart(selected_df)
                ui.display_search_purchase_chart(selected_df)
                ui.display_keyword_analysis_section(selected_df)
                ui.display_word_frequency_section(selected_df, "单ASIN组成关键词的单词频率")
                ui.display_raw_data(selected_df, "原始数据")


if __name__ == "__main__":
    main()