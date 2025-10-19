import streamlit as st
import pandas as pd
import akshare as ak
import plotly.express as px
from datetime import datetime, time

# 设置 Streamlit 页面配置
# Use st.set_page_config() as the first Streamlit command.
st.set_page_config(
    page_title="中国股市板块实时监控",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 数据获取与处理 ---
# 定义我们感兴趣的板块名称
# 注意：这些名称需要与 akshare 数据源中的概念板块名称精确匹配或近似匹配
# 我们选择了一些最相关的名称，例如 "国家大基金-半导体" 来代表半导体板块
TARGET_SECTORS = {
    "黄金概念": "黄金",
    "国家大基金-半导体": "半导体",
    "人工智能AIGC": "人工智能",
    "稀土永磁": "稀土",
    "航母概念": "军工"
}


@st.cache_data(ttl=60)  # 设置缓存，每60秒过期
def get_sector_data():
    """
    从 akshare 获取所有概念板块的实时数据，并筛选出我们感兴趣的板块。
    """
    try:
        # 获取所有概念板块的实时行情数据
        all_sectors_df = ak.stock_board_concept_spot_em()

        # 根据我们定义的目标板块名称列表，筛选出相应的数据
        # 我们需要的数据列: 板块名称 (name), 涨跌幅 (change_rate)
        all_sectors_df = all_sectors_df[['名称', '涨跌幅']]
        all_sectors_df = all_sectors_df.rename(columns={'名称': 'name', '涨跌幅': 'change_rate'})

        # 筛选出我们关注的板块
        target_df = all_sectors_df[all_sectors_df['name'].isin(TARGET_SECTORS.keys())].copy()

        # 映射为我们自定义的更简洁的板块名
        target_df['display_name'] = target_df['name'].map(TARGET_SECTORS)

        # 数据清洗，确保涨跌幅是数值类型
        target_df['change_rate'] = pd.to_numeric(target_df['change_rate'], errors='coerce')
        target_df = target_df.dropna(subset=['change_rate'])

        return target_df

    except Exception as e:
        st.error(f"数据加载失败，请稍后再试。错误: {e}")
        return pd.DataFrame()  # 返回空的DataFrame


# --- 界面渲染 ---

# 标题和数据更新时间
st.title("💹 中国股市板块实时监控")
last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"**数据更新于: {last_update_time}** (每分钟自动刷新)")

# 获取数据
sector_data = get_sector_data()

if not sector_data.empty:
    # --- 指标卡片展示 ---
    st.header("核心板块表现")

    # 创建列来展示指标
    cols = st.columns(len(TARGET_SECTORS))

    # 为了能按我们定义的顺序显示，我们遍历TARGET_SECTORS
    display_order = list(TARGET_SECTORS.values())
    sorted_data = sector_data.set_index('display_name').reindex(display_order).reset_index()

    for i, row in sorted_data.iterrows():
        col = cols[i]
        change_rate = row['change_rate']

        # 使用 st.metric 来展示，delta_color='inverse'会让正数显示为红色，负数显示为绿色，符合A股习惯
        # 如果需要标准的红涨绿跌，则使用 'normal'
        with col:
            st.metric(
                label=row['display_name'],
                value=f"{change_rate:.2f}%",
                delta=f"{change_rate:.2f}",
                delta_color="inverse"  # A股习惯：红涨绿跌
            )

    st.markdown("---")  # 分割线

    # --- 可视化图表 ---
    st.header("板块涨跌幅对比")

    # 根据涨跌幅的正负来定义颜色
    colors = ['#d62728' if x > 0 else '#2ca02c' for x in sorted_data['change_rate']]

    # 使用 Plotly 创建条形图
    fig = px.bar(
        sorted_data,
        x='display_name',
        y='change_rate',
        title='各板块实时涨跌幅 (%)',
        text_auto='.2f',  # 在条形上显示数值
        labels={'display_name': '板块名称', 'change_rate': '涨跌幅 (%)'}
    )

    fig.update_traces(
        marker_color=colors,  # 设置条形颜色
        textposition='outside'  # 将数值标签放在条形外部
    )

    fig.update_layout(
        xaxis_title=None,  # 隐藏x轴标题
        yaxis_title="涨跌幅 (%)",
        font=dict(size=14),
        title_font_size=22,
        title_x=0.5  # 标题居中
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("未能获取到有效的板块数据。可能是因为闭市期间或网络问题。")

# --- 自动刷新机制 ---
# 检查当前是否为A股交易时间 (9:30-11:30, 13:00-15:00)
# 这样做可以避免在非交易时间频繁请求数据
now_time = datetime.now().time()
is_trading_time = (time(9, 30) <= now_time <= time(11, 30)) or \
                  (time(13, 0) <= now_time <= time(15, 00))

if is_trading_time:
    st.rerun()

st.info("提示：页面将在交易时间内每分钟自动刷新一次。您也可以手动刷新浏览器来获取最新数据。")