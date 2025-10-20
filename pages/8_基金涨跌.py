# import streamlit as st
# import pandas as pd
# import akshare as ak
# import time
# from shared.sidebar import create_common_sidebar
#
# # ----------------- 初始化侧边栏 -----------------
# create_common_sidebar()
#
# # ----------------- 页面配置 -----------------
# st.set_page_config(
#     page_title="基金实时看板",
#     page_icon="📈",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )
#
# # ----------------- 样式注入 -----------------
# st.markdown("""
# <style>
# [data-testid="stMetric"] {
#     background-color: #f0f2f6;
#     border: 1px solid #e6e6e6;
#     border-radius: 10px;
#     padding: 15px;
#     box-shadow: 0 4px 8px rgba(0,0,0,0.1);
# }
# [data-testid="stMetricLabel"] {
#     font-size: 18px;
#     font-weight: 500;
# }
# [data-testid="stMetricValue"] {
#     font-size: 28px;
#     font-weight: 700;
# }
# [data-testid="stMetricDelta"] {
#     font-size: 16px;
# }
# </style>
# """, unsafe_allow_html=True)
#
#
# # ----------------- 数据获取与缓存 -----------------
# @st.cache_data(ttl=60)
# def get_fund_data(fund_codes):
#     """获取指定基金代码的实时行情数据（带重试机制）"""
#     max_retries = 3
#     retry_delay = 5
#
#     for attempt in range(max_retries):
#         try:
#             with st.spinner('正在获取基金数据...'):
#                 etf_spot_df = ak.fund_etf_spot_em()
#                 filtered_df = etf_spot_df[etf_spot_df['代码'].isin(fund_codes)]
#
#                 numeric_cols = [
#                     '最新价', 'IOPV实时估值', '基金折价率', '涨跌额', '涨跌幅', '成交量',
#                     '成交额', '开盘价', '最高价', '最低价', '昨收', '振幅', '换手率', '量比',
#                     '委比', '外盘', '内盘', '主力净流入-净额', '主力净流入-净占比'
#                 ]
#                 for col in numeric_cols:
#                     filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce')
#                 return filtered_df.fillna(0)
#
#         except Exception as e:
#             if attempt < max_retries - 1:
#                 time.sleep(retry_delay)
#                 continue
#             st.error(f"数据加载失败，可能是网络问题或接口暂时不可用。错误信息: {e}")
#             return pd.DataFrame()
#
#
# # ----------------- 页面主体 -----------------
#
# # --- 标题和刷新控件的容器 ---
# header_cols = st.columns([0.8, 0.2])
# with header_cols[0]:
#     st.title("📈 基金实时看板")
#
# # 我们关注的几只关键基金
# key_funds = {
#     "510300": "沪深300ETF",
#     "518880": "黃金ETF",
#     "159558": "半导体设备ETF易方达",
#     "515980": "人工智能ETF",
#     "159715": "稀土ETF易方达",
#     "512560": "军工ETF易方达"
# }
#
# # --- 获取数据 ---
# fund_codes = list(key_funds.keys())
# all_etf_df = get_fund_data(fund_codes)
#
# if not all_etf_df.empty:
#     # --- 基金选择器 ---
#     fund_options_list = [f"{key_funds[code]} ({code})" for code in fund_codes]
#
#     selected_funds_str = st.multiselect(
#         label="🔍 请选择您关注的基金:",
#         options=fund_options_list,
#         default=fund_options_list,
#         placeholder="选择要显示的基金..."
#     )
#
#     selected_fund_codes = [item.split(" (")[1].replace(")", "") for item in selected_funds_str]
#     selected_fund_names = [key_funds[code] for code in selected_fund_codes]
#
#     # --- 筛选数据 ---
#     filtered_df = all_etf_df[all_etf_df['代码'].isin(selected_fund_codes)]
#     st.divider()
#
#     # --- 指标卡展示 ---
#     if not filtered_df.empty:
#         st.subheader("📊 核心指标速览")
#         num_funds = len(filtered_df)
#         cols = st.columns(num_funds)
#
#         for i, (index, row) in enumerate(filtered_df.iterrows()):
#             with cols[i]:
#                 delta_value = f"{row['涨跌额']:.2f}"
#                 percent_change = row['涨跌幅']
#
#                 st.metric(
#                     label=f"{key_funds[row['代码']]} ({row['代码']})",
#                     value=f"¥ {row['最新价']:.3f}",
#                     delta=f"{delta_value} ({percent_change:.2f}%)",
#                 )
#     else:
#         st.warning("请至少选择一只基金进行展示。")
#
#     st.divider()
#
#     # --- 详细数据表格 ---
#     with st.expander("詳細數據一覽", expanded=True):
#         if not filtered_df.empty:
#             display_cols = [
#                 '代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交额',
#                 '换手率', '基金折价率', '主力净流入-净额', '更新时间'
#             ]
#
#             styled_df = filtered_df[display_cols].copy()
#             styled_df['涨跌幅'] = styled_df['涨跌幅'].map('{:.2f}%'.format)
#             styled_df['换手率'] = styled_df['换手率'].map('{:.2f}%'.format)
#             styled_df['基金折价率'] = styled_df['基金折价率'].map('{:.2f}%'.format)
#             styled_df['成交额'] = (styled_df['成交额'] / 100000000).map('{:,.2f} 亿'.format)
#             styled_df['主力净流入-净额'] = (styled_df['主力净流入-净额'] / 100000000).map('{:,.2f} 亿'.format)
#
#             st.dataframe(styled_df, use_container_width=True, hide_index=True)
#         else:
#             st.info("暂无选中基金的详细数据。")
# else:
#     st.error("无法获取数据，页面无法加载。请检查网络连接或稍后重试。")
#
# # ----------------- 自动刷新逻辑 -----------------
# with header_cols[1]:
#     col1, col2 = st.columns([0.6, 0.4], gap="small")
#
#     # 手动刷新按钮
#     if col2.button("刷新", key="manual_refresh"):
#         st.cache_data.clear()
#         st.rerun()
#
#     # 倒计时显示
#     countdown_placeholder = col1.empty()
#
# # 初始化或更新倒计时状态
# if 'countdown' not in st.session_state:
#     st.session_state.countdown = 120  # 2分钟刷新间隔
#
# # 显示当前倒计时
# countdown_placeholder.markdown(f"🕒 `自动刷新: {st.session_state.countdown}s`")
#
# # 倒计时逻辑
# if st.session_state.countdown > 0:
#     st.session_state.countdown -= 1
#     time.sleep(1)
#     st.rerun()
# else:
#     # 倒计时结束，清除缓存并刷新
#     st.cache_data.clear()
#     st.rerun()