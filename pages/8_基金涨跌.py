# fund_dashboard.py

import streamlit as st
import pandas as pd
import akshare as ak
import time

# ----------------- 页面配置 -----------------
st.set_page_config(
    page_title="基金实时看板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------- 样式注入（可选） -----------------
st.markdown("""
<style>
/* 调整指标卡边框和阴影 */
[data-testid="stMetric"] {
    background-color: #f0f2f6;
    border: 1px solid #e6e6e6;
    border-radius: 10px;
    padding: 15px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
/* 调整指标卡的标签字体大小 */
[data-testid="stMetricLabel"] {
    font-size: 18px;
    font-weight: 500;
}
/* 调整指标卡的值字体大小 */
[data-testid="stMetricValue"] {
    font-size: 28px;
    font-weight: 700;
}
/* 调整指标卡的Delta（变化量）字体大小 */
[data-testid="stMetricDelta"] {
    font-size: 16px;
}
</style>
""", unsafe_allow_html=True)


# ----------------- 数据获取与缓存 -----------------
@st.cache_data(ttl=60)
def get_etf_data():
    """获取所有ETF基金的实时行情数据"""
    try:
        etf_spot_df = ak.fund_etf_spot_em()
        numeric_cols = [
            '最新价', 'IOPV实时估值', '基金折价率', '涨跌额', '涨跌幅', '成交量',
            '成交额', '开盘价', '最高价', '最低价', '昨收', '振幅', '换手率', '量比',
            '委比', '外盘', '内盘', '主力净流入-净额', '主力净流入-净占比'
        ]
        for col in numeric_cols:
            etf_spot_df[col] = pd.to_numeric(etf_spot_df[col], errors='coerce')
        etf_spot_df = etf_spot_df.fillna(0)
        return etf_spot_df
    except Exception as e:
        st.error(f"数据加载失败，可能是网络问题或接口暂时不可用。错误信息: {e}")
        return pd.DataFrame()


# ----------------- 页面主体 -----------------

# --- 标题和刷新控件的容器 ---
header_cols = st.columns([0.8, 0.2])
with header_cols[0]:
    st.title("📈 基金实时看板")

# --- 获取数据 ---
all_etf_df = get_etf_data()

if not all_etf_df.empty:
    # --- 基金选择器 ---
    fund_options = all_etf_df[['代码', '名称']].drop_duplicates()
    fund_options_list = fund_options.apply(lambda x: f"{x['名称']} ({x['代码']})", axis=1).tolist()

    default_selections = [
        "沪深300ETF （510300）", "黃金ETF（518880）", "半导体设备ETF易方达（159558）",
        "人工智能ETF （515980）", "稀土ETF易方达（159715）", "军工ETF易方达（512560）"
    ]
    valid_defaults = [item for item in default_selections if item in fund_options_list]

    selected_funds_str = st.multiselect(
        label="🔍 请选择或搜索您关注的基金:",
        options=fund_options_list,
        default=valid_defaults,
        placeholder="输入基金名称或代码进行搜索..."
    )

    selected_fund_names = [item.split(" (")[0] for item in selected_funds_str]

    # --- 筛选数据 ---
    filtered_df = all_etf_df[all_etf_df['名称'].isin(selected_fund_names)]

    st.divider()

    # --- 指标卡展示 ---
    if not filtered_df.empty:
        st.subheader("📊 核心指标速览")
        num_funds = len(filtered_df)
        cols = st.columns(num_funds)

        for i, (index, row) in enumerate(filtered_df.iterrows()):
            with cols[i]:
                delta_value = f"{row['涨跌额']:.2f}"
                percent_change = row['涨跌幅']

                st.metric(
                    label=f"{row['名称']} ({row['代码']})",
                    value=f"¥ {row['最新价']:.3f}",
                    delta=f"{delta_value} ({percent_change:.2f}%)",
                )
    else:
        st.warning("请至少选择一只基金进行展示。")

    st.divider()

    # --- 详细数据表格 ---
    with st.expander("詳細數據一覽", expanded=True):
        if not filtered_df.empty:
            display_cols = [
                '代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交额',
                '换手率', '基金折价率', '主力净流入-净额', '更新时间'
            ]

            styled_df = filtered_df[display_cols].copy()
            styled_df['涨跌幅'] = styled_df['涨跌幅'].map('{:.2f}%'.format)
            styled_df['换手率'] = styled_df['换手率'].map('{:.2f}%'.format)
            styled_df['基金折价率'] = styled_df['基金折价率'].map('{:.2f}%'.format)
            styled_df['成交额'] = (styled_df['成交额'] / 100000000).map('{:,.2f} 亿'.format)
            styled_df['主力净流入-净额'] = (styled_df['主力净流入-净额'] / 100000000).map('{:,.2f} 亿'.format)

            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无选中基金的详细数据。")
else:
    st.error("无法获取数据，页面无法加载。请检查网络连接或稍后重试。")

# --- 自动刷新逻辑 (已修正) ---
# 1. 在循环外部，预先定义好布局和按钮
with header_cols[1]:  # 使用页面顶部已经创建好的列
    col1, col2 = st.columns([0.6, 0.4], gap="small")

    # 按钮只在这里创建一次
    if col2.button("刷新", key="manual_refresh"):
        st.cache_data.clear()
        st.rerun()

    # 为倒计时文本创建一个专用的占位符
    countdown_placeholder = col1.empty()

# 2. 循环只负责更新占位符的文本和执行延时
REFRESH_INTERVAL_SECONDS = 120
for i in range(REFRESH_INTERVAL_SECONDS, 0, -1):
    # 更新占位符中的倒计时
    countdown_placeholder.markdown(f"🕒 `自动刷新: {i}s`")
    time.sleep(1)

# 3. 倒计时结束后，清除缓存并重新运行以实现自动刷新
st.cache_data.clear()
st.rerun()