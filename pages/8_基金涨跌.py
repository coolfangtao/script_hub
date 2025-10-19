import streamlit as st
import pandas as pd
import akshare as ak
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
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


# --- 数据处理函数 ---

def is_trading_time():
    """检查当前是否为A股交易时间"""
    now = datetime.now()
    # 检查是否为工作日 (Monday=0, Sunday=6)
    if now.weekday() >= 5:
        return False
    # 检查是否在交易时间段内
    now_time = now.time()
    is_morning = time(9, 30) <= now_time <= time(11, 30)
    is_afternoon = time(13, 0) <= now_time <= time(15, 0)
    return is_morning or is_afternoon


# @st.cache_data 的 ttl (time-to-live) 参数确保数据在60秒后会重新获取
@st.cache_data(ttl=60)
def fetch_data_during_trading():
    """仅在交易时间内从akshare获取实时数据和历史数据"""
    try:
        # 1. 获取所有板块的实时快照数据
        spot_df = ak.stock_board_concept_spot_em()
        required_cols = ['代码', '名称', '最新价', '涨跌幅']
        # 如果API返回的数据不含所需列，则返回空DataFrame
        if not all(col in spot_df.columns for col in required_cols):
            st.warning("数据源未返回有效的实时行情数据。")
            return pd.DataFrame()

        # 2. 筛选出我们关注的板块
        target_df = spot_df[spot_df['名称'].isin(TARGET_SECTOR_NAMES)].copy()

        # 3. 为每个板块获取最近60天的历史数据用于绘制迷你图
        history_list = []
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

        for code in target_df['代码']:
            try:
                hist_df = ak.stock_board_concept_hist_em(symbol=code, start_date=start_date, end_date=end_date)
                history_list.append(hist_df['收盘'].tolist())
            except Exception:
                history_list.append([])  # 如果获取失败，则为空列表

        target_df['history'] = history_list

        # 4. 数据清洗和重命名
        target_df = target_df[['名称', '代码', '最新价', '涨跌幅', 'history']].rename(columns={
            '名称': 'name', '代码': 'code', '最新价': 'price', '涨跌幅': 'change_rate'
        })

        return target_df

    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return pd.DataFrame()


# --- 界面渲染函数 ---

def create_sparkline(data, is_positive):
    """创建一个迷你的Plotly趋势图"""
    if not data or len(data) < 2:
        return go.Figure()

    color = "#d62728" if is_positive else "#2ca02c"  # 红涨绿跌
    fig = go.Figure(go.Scatter(
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
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


def display_dashboard(df):
    """根据给定的DataFrame渲染整个仪表盘"""
    st.title("📈 中国股市板块监控")

    # 动态显示标题信息
    if is_trading_time():
        st.caption(f"当前显示为 **实时行情** (最后更新: {datetime.now().strftime('%H:%M:%S')})")
    else:
        st.caption("当前为非交易时段，无实时数据。")

    if df.empty:
        st.info("请在A股交易时段 (工作日 9:30-11:30, 13:00-15:00) 查看实时数据。")
        return

    # 按照我们定义的顺序显示
    df['name'] = pd.Categorical(df['name'], categories=TARGET_SECTOR_NAMES, ordered=True)
    df = df.sort_values('name')

    for index, row in df.iterrows():
        name, code, price, change_rate, history = row['name'], row['code'], row['price'], row['change_rate'], row[
            'history']
        is_positive = change_rate >= 0
        color = "#d62728" if is_positive else "#2ca02c"

        st.markdown("---")
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
data_to_display = pd.DataFrame()
trading_now = is_trading_time()

if trading_now:
    # 只有在交易时间，才去获取数据
    data_to_display = fetch_data_during_trading()

# 渲染界面，无论是否有数据
display_dashboard(data_to_display)

# 自动刷新逻辑
if trading_now:
    st.rerun()