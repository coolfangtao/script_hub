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

# 定义我们感兴趣的板块及其对应的板块代码
TARGET_SECTORS = {
    "国防军工": "BK0548",
    "半导体产业": "BK1031",
    "人工智能": "BK0855",
    "稀土永磁": "BK0483"
}


# --- 数据处理函数 ---

def is_trading_time():
    """检查当前是否为A股交易时间"""
    now = datetime.now()
    if now.weekday() >= 5: return False
    now_time = now.time()
    is_morning = time(9, 30) <= now_time <= time(11, 30)
    is_afternoon = time(13, 0) <= now_time <= time(15, 0)
    return is_morning or is_afternoon


@st.cache_data(ttl=60)
def fetch_data():
    """智能数据获取函数"""
    if is_trading_time():
        return fetch_live_data()
    else:
        return fetch_latest_closing_data()


def fetch_live_data():
    """在交易时间内获取实时数据"""
    try:
        spot_df = ak.stock_board_concept_spot_em()
        target_df = spot_df[spot_df['代码'].isin(TARGET_SECTORS.values())].copy()

        history_list = []
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        for code in target_df['代码']:
            hist_df = ak.stock_board_concept_hist_em(symbol=code, start_date=start_date, end_date=end_date)
            # --- 【同样增加安全检查】 ---
            history_list.append(hist_df['收盘'].tolist() if not hist_df.empty else [])

        target_df['history'] = history_list
        target_df = target_df.rename(columns={'名称': 'name', '代码': 'code', '最新价': 'price', '涨跌幅': 'change_rate'})
        return target_df[['name', 'code', 'price', 'change_rate', 'history']]
    except Exception as e:
        st.error(f"获取实时数据失败: {e}. 将尝试获取收盘数据。")
        return fetch_latest_closing_data()


def fetch_latest_closing_data():
    """在非交易时间获取最近交易日的收盘数据"""
    all_data = []
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

    for name, code in TARGET_SECTORS.items():
        try:
            hist_df = ak.stock_board_concept_hist_em(symbol=code, start_date=start_date, end_date=end_date)

            # --- 【关键修改】在这里增加安全检查 ---
            # 只有当返回的hist_df不是空的时候，才执行后续操作
            if not hist_df.empty:
                latest_data = hist_df.iloc[-1]
                all_data.append({
                    "name": name,
                    "code": code,
                    "price": latest_data['收盘'],
                    "change_rate": latest_data['涨跌幅'],
                    "history": hist_df['收盘'].tail(60).tolist()
                })
            else:
                # 如果是空的，就打印一个警告，然后继续处理下一个板块
                st.warning(f"未能获取板块 '{name}' 的历史数据，数据源可能暂时不可用。")

        except Exception as e:
            st.warning(f"处理板块 '{name}' 时发生错误: {e}")

    return pd.DataFrame(all_data)


# --- 界面渲染函数 (此部分无变化) ---
def create_sparkline(data, is_positive):
    if not data or len(data) < 2: return go.Figure()
    color = "#d62728" if is_positive else "#2ca02c"
    fig = go.Figure(go.Scatter(
        y=data, mode='lines', line=dict(color=color, width=2), fill='tozeroy',
        fillcolor='rgba(214, 39, 40, 0.1)' if is_positive else 'rgba(44, 160, 44, 0.1)'
    ))
    fig.update_layout(
        showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0), height=60,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def display_dashboard(df):
    st.title("📈 中国股市板块监控")
    if is_trading_time():
        st.caption(f"当前显示为 **实时行情** (自动刷新中, 最后更新: {datetime.now().strftime('%H:%M:%S')})")
    else:
        st.caption(f"当前为非交易时段，显示 **最近交易日收盘数据**")
    if df.empty:
        st.warning("未能获取到任何板块数据，请稍后刷新或检查网络。")
        return
    df['name'] = pd.Categorical(df['name'], categories=TARGET_SECTORS.keys(), ordered=True)
    df = df.sort_values('name')
    for _, row in df.iterrows():
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
            st.plotly_chart(create_sparkline(history, is_positive), use_container_width=True,
                            config={'displayModeBar': False})
        with col3:
            st.markdown(f"""
            <div style="text-align: right; font-family: 'Helvetica Neue', sans-serif;">
                <div style="font-size: 1.3em; font-weight: 600;">{price:.2f}</div>
                <div style="font-size: 1.3em; font-weight: 600; color:{color};">{change_rate:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)


# --- 主逻辑 ---
data_to_display = fetch_data()
display_dashboard(data_to_display)
if is_trading_time():
    st.rerun()