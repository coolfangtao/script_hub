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
    增加了对非交易时间数据返回格式的处理。
    """
    try:
        # 获取所有概念板块的实时行情数据
        all_sectors_df = ak.stock_board_concept_spot_em()

        # --- 【关键修改】健壮性检查 ---
        # 检查API返回的数据中是否包含我们需要的列
        required_cols = ['名称', '涨跌幅']
        if not all(col in all_sectors_df.columns for col in required_cols):
            # 如果在非交易时间，API可能不返回实时数据列，导致原始代码出错
            # 我们在这里进行判断，如果缺少关键列，则返回一个空的数据表
            st.warning("未能获取到实时行情数据，当前可能为非交易时间。")
            return pd.DataFrame()

        # 根据我们定义的目标板块名称列表，筛选出相应的数据
        all_sectors_df = all_sectors_df[required_cols]  # 选取我们需要的列
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
st.markdown(f"**数据更新于: {last_update_time}** (交易时间内每分钟自动刷新)")

# 获取数据
sector_data = get_sector_data()

# 只有在成功获取并处理数据后才显示图表
if not sector_data.empty:
    # --- 指标卡片展示 ---
    st.header("核心板块表现")

    # 创建列来展示指标
    cols = st.columns(len(TARGET_SECTORS))

    # 为了能按我们定义的顺序显示
    display_order = list(TARGET_SECTORS.values())
    sorted_data = sector_data.set_index('display_name').reindex(display_order).reset_index()

    for i, row in sorted_data.iterrows():
        # 确保索引在 cols 范围内
        if i < len(cols):
            col = cols[i]
            change_rate = row['change_rate']

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
        text_auto='.2f',
        labels={'display_name': '板块名称', 'change_rate': '涨跌幅 (%)'}
    )

    fig.update_traces(
        marker_color=colors,
        textposition='outside'
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title="涨跌幅 (%)",
        font=dict(size=14),
        title_font_size=22,
        title_x=0.5
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    # 如果sector_data为空（因为非交易时间或错误），则显示此提示
    st.info("当前无实时数据，请在A股交易时段 (工作日 9:30-11:30, 13:00-15:00) 查看。")

# --- 自动刷新机制 ---
now_time = datetime.now().time()
is_trading_time = (time(9, 30) <= now_time <= time(11, 30)) or \
                  (time(13, 0) <= now_time <= time(15, 00))

# 只有在交易时间，才执行页面刷新指令
if is_trading_time:
    try:
        # st.rerun() 在较新版本中可用，用于强制重新运行脚本
        st.rerun()
    except AttributeError:
        # 对于老版本streamlit，可以使用实验性功能
        st.experimental_rerun()