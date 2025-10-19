import streamlit as st
import pandas as pd
import akshare as ak
import plotly.express as px
from datetime import datetime, time
import os
import json
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 核心配置 ---
# 设置 Streamlit 页面
st.set_page_config(
    page_title="中国股市板块实时监控",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 定义我们感兴趣的板块名称
TARGET_SECTORS = {
    "黄金概念": "黄金",
    "国家大基金-半导体": "半导体",
    "人工智能AIGC": "人工智能",
    "稀土永磁": "稀土",
    "航母概念": "军工"
}

# 用于存储最新数据的文件名
DATA_CACHE_FILE = "latest_sector_data.json"


# --- 数据处理函数 ---

def is_trading_time():
    """检查当前是否为A股交易时间"""
    now = datetime.now()
    # 检查是否为工作日 (Monday=0, Sunday=6)
    if now.weekday() >= 5:
        return False
    # 检查是否在交易时间段内
    now_time = now.time()
    is_morning_session = time(9, 30) <= now_time <= time(11, 30)
    is_afternoon_session = time(13, 0) <= now_time <= time(15, 0)
    return is_morning_session or is_afternoon_session


@st.cache_data(ttl=60)  # 在交易时间内，数据每60秒重新获取
def fetch_live_data():
    """从akshare获取实时数据"""
    try:
        all_sectors_df = ak.stock_board_concept_spot_em()
        required_cols = ['名称', '涨跌幅']
        if not all(col in all_sectors_df.columns for col in required_cols):
            return pd.DataFrame()  # 非交易时段可能返回不同格式，返回空表

        all_sectors_df = all_sectors_df.rename(columns={'名称': 'name', '涨跌幅': 'change_rate'})
        target_df = all_sectors_df[all_sectors_df['name'].isin(TARGET_SECTORS.keys())].copy()
        target_df['display_name'] = target_df['name'].map(TARGET_SECTORS)
        target_df['change_rate'] = pd.to_numeric(target_df['change_rate'], errors='coerce').dropna()

        # 保存数据到缓存文件
        if not target_df.empty:
            target_df.to_json(DATA_CACHE_FILE, orient='records', force_ascii=False, indent=4)
        return target_df

    except Exception as e:
        st.error(f"实时数据加载失败: {e}")
        return pd.DataFrame()


def load_cached_data():
    """从本地JSON文件加载缓存数据"""
    if os.path.exists(DATA_CACHE_FILE):
        try:
            return pd.read_json(DATA_CACHE_FILE, orient='records')
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"缓存文件格式错误，无法读取: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


# --- 界面渲染函数 ---

def display_dashboard(df, source_info):
    """根据给定的DataFrame渲染整个仪表盘"""
    st.title("💹 中国股市板块实时监控")
    last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**{source_info}** (数据更新于: {last_update_time})")

    if df.empty:
        st.warning("暂无数据可供显示。请在交易时段运行一次程序以生成缓存。")
        return

    # --- 指标卡片展示 ---
    st.header("核心板块表现")
    cols = st.columns(len(TARGET_SECTORS))
    display_order = list(TARGET_SECTORS.values())
    sorted_data = df.set_index('display_name').reindex(display_order).reset_index()

    for i, row in sorted_data.iterrows():
        if i < len(cols) and pd.notna(row['change_rate']):
            col = cols[i]
            change_rate = row['change_rate']
            with col:
                st.metric(
                    label=row['display_name'],
                    value=f"{change_rate:.2f}%",
                    delta=f"{change_rate:.2f}",
                    delta_color="inverse"
                )

    # --- 可视化图表 ---
    st.header("板块涨跌幅对比")
    colors = ['#d62728' if x > 0 else '#2ca02c' for x in sorted_data['change_rate']]
    fig = px.bar(
        sorted_data, x='display_name', y='change_rate',
        title='各板块涨跌幅 (%)', text_auto='.2f',
        labels={'display_name': '板块名称', 'change_rate': '涨跌幅 (%)'}
    )
    fig.update_traces(marker_color=colors, textposition='outside')
    fig.update_layout(
        xaxis_title=None, yaxis_title="涨跌幅 (%)", font=dict(size=14),
        title_font_size=22, title_x=0.5
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 主逻辑 ---

trading_now = is_trading_time()
data_to_display = pd.DataFrame()
data_source_message = ""

if trading_now:
    # 交易时间：获取实时数据
    data_to_display = fetch_live_data()
    data_source_message = "当前显示为 **实时行情**"
    if data_to_display.empty:
        # 如果实时获取失败，尝试加载缓存
        data_source_message = "实时行情获取失败，显示最近一次 **收盘数据**"
        data_to_display = load_cached_data()
else:
    # 非交易时间：加载缓存数据
    data_source_message = "当前为非交易时段，显示最近一次 **收盘数据**"
    data_to_display = load_cached_data()

# 渲染界面
display_dashboard(data_to_display, data_source_message)

# 自动刷新逻辑
if trading_now:
    st.info("提示：页面将在交易时间内每分钟自动刷新一次。")
    st.rerun()
else:
    st.info("提示：当前为非交易时间，数据不再自动刷新。")