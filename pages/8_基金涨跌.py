import streamlit as st
import pandas as pd
import akshare as ak
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import os
import json
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 核心配置 ---
st.set_page_config(
    page_title="中国股市板块实时监控",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 定义我们感兴趣的板块名称 (akshare中的官方名称)
TARGET_SECTOR_NAMES = ["国防军工", "半导体产业", "人工智能", "稀土永磁"]

# 用于存储最新数据的文件名
DATA_CACHE_FILE = "latest_sector_data_v2.json"


# --- 数据处理函数 ---

def is_trading_time():
    """检查当前是否为A股交易时间"""
    now = datetime.now()
    if now.weekday() >= 5: return False  # 周末休市
    now_time = now.time()
    is_morning = time(9, 30) <= now_time <= time(11, 30)
    is_afternoon = time(13, 0) <= now_time <= time(15, 0)
    return is_morning or is_afternoon


@st.cache_data(ttl=60)  # 交易时间内，数据每60秒重新获取
def fetch_live_data():
    """从akshare获取实时数据和历史数据"""
    try:
        # 1. 获取所有板块的实时快照数据
        spot_df = ak.stock_board_concept_spot_em()
        required_cols = ['代码', '名称', '最新价', '涨跌幅']
        if not all(col in spot_df.columns for col in required_cols):
            return pd.DataFrame()  # 非交易时段可能返回不同格式

        # 2. 筛选出我们关注的板块
        target_df = spot_df[spot_df['名称'].isin(TARGET_SECTOR_NAMES)].copy()

        # 3. 为每个板块获取最近60天的历史数据用于绘制迷你图
        history_list = []
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

        for code in target_df['代码']:
            try:
                hist_df = ak.stock_board_concept_hist_em(symbol=code, start_date=start_date, end_date=end_date)
                # 只保留收盘价数据点
                history_list.append(hist_df['收盘'].tolist())
            except Exception:
                history_list.append([])  # 如果获取失败，则为空列表

        target_df['history'] = history_list

        # 4. 数据清洗和重命名
        target_df = target_df[['名称', '代码', '最新价', '涨跌幅', 'history']].rename(columns={
            '名称': 'name', '代码': 'code', '最新价': 'price', '涨跌幅': 'change_rate'
        })

        # 5. 保存数据到缓存文件
        if not target_df.empty:
            target_df.to_json(DATA_CACHE_FILE, orient='records', force_ascii=False, indent=4)

        return target_df

    except Exception as e:
        st.error(f"实时数据加载失败: {e}")
        return pd.DataFrame()


def load_cached_data():
    """从本地JSON文件加载缓存数据"""
    if os.path.exists(DATA_CACHE_FILE):
        return pd.read_json(DATA_CACHE_FILE, orient='records')
    return pd.DataFrame()


# --- 界面渲染函数 ---

def create_sparkline(data, is_positive):
    """创建一个迷你的Plotly趋势图"""
    if not data or len(data) < 2:
        return go.Figure()  # 返回空图表

    color = "#d62728" if is_positive else "#2ca02c"  # 红涨绿跌
    fig = go.Figure(go.Scatter(
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',  # 填充到y=0的区域
        fillcolor='rgba(214, 39, 40, 0.1)' if is_positive else 'rgba(44, 160, 44, 0.1)'
    ))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        height=60,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def display_dashboard(df, source_info):
    """根据给定的DataFrame渲染整个仪表盘"""
    st.title("📈 中国股市板块监控")
    st.caption(f"{source_info} (最后更新: {datetime.now().strftime('%H:%M:%S')})")

    if df.empty:
        st.warning("暂无数据可供显示。请在交易时段运行一次程序以生成缓存。")
        return

    # 按照我们定义的顺序显示
    df['name'] = pd.Categorical(df['name'], categories=TARGET_SECTOR_NAMES, ordered=True)
    df = df.sort_values('name')

    for index, row in df.iterrows():
        name = row['name']
        code = row['code']
        price = row['price']
        change_rate = row['change_rate']
        history = row['history']

        is_positive = change_rate >= 0
        color = "#d62728" if is_positive else "#2ca02c"

        st.markdown("---", help=f"数据源: akshare, 板块代码: {code}")

        col1, col2, col3 = st.columns([2.5, 2, 2])

        with col1:
            st.markdown(f"""
            <div style="font-size: 1.2em; font-weight: bold; line-height: 1.5;">{name}</div>
            <span style="background-color: #333; color: #EEE; padding: 2px 6px; border-radius: 5px; font-size: 0.8em;">板 {code}</span>
            """, unsafe_allow_html=True)

        with col2:
            spark_fig = create_sparkline(history, is_positive)
            st.plotly_chart(spark_fig, use_container_width=True, config={'displayModeBar': False})

        with col3:
            st.markdown(f"""
            <div style="text-align: right; font-family: 'Helvetica Neue', sans-serif;">
                <div style="font-size: 1.3em; font-weight: 600;">{price:.2f}</div>
                <div style="font-size: 1.3em; font-weight: 600; color:{color};">{change_rate:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)


# --- 主逻辑 ---
trading_now = is_trading_time()
data_to_display = pd.DataFrame()

if trading_now:
    data_to_display = fetch_live_data()
    source_message = "当前显示为 **实时行情**"
    if data_to_display.empty:
        source_message = "实时行情获取失败，显示最近一次 **收盘数据**"
        data_to_display = load_cached_data()
else:
    source_message = "当前为非交易时段，显示最近一次 **收盘数据**"
    data_to_display = load_cached_data()

display_dashboard(data_to_display, source_message)

if trading_now:
    st.rerun()