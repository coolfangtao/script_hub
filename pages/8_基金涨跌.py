import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import pytz
import json
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 页面基础设置 ---
st.set_page_config(
    page_title="动态基金看板",
    page_icon="🚀",
    layout="wide"
)

# --- 核心数据与功能 ---

# 1. 定义您关注的基金列表
FUNDS = {
    "510300": "沪深300ETF",
    "518880": "黄金ETF",
    "159995": "芯片ETF",
    "515980": "人工智能ETF",
    "516780": "稀土产业ETF",
    "512660": "军工ETF"
}


# 2. 根据基金代码获取完整的市场代码
def get_full_code(code):
    """根据基金代码判断是上海(sh)还是深圳(sz)市场"""
    if code.startswith('51') or code.startswith('58'):
        return f"sh{code}"
    elif code.startswith('15'):
        return f"sz{code}"
    else:
        return ""


# 3. 获取实时数据 (Sina API)
def fetch_fund_data(fund_codes):
    """通过HTTP请求从新浪财经获取多个基金的实时数据。"""
    if not fund_codes:
        return []
    full_codes = [get_full_code(code) for code in fund_codes if get_full_code(code)]
    url = f"http://hq.sinajs.cn/list={','.join(full_codes)}"
    headers = {'Referer': 'http://finance.sina.com.cn'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = 'gbk'
        data_list = []
        raw_text = response.text
        pattern = re.compile(r'var hq_str_(\w+)="([^"]+)";')
        matches = pattern.findall(raw_text)
        for match in matches:
            code_full, data_str = match
            code = code_full[2:]
            if not data_str: continue
            parts = data_str.split(',')
            yesterday_close = float(parts[2])
            current_price = float(parts[3])
            change = current_price - yesterday_close if yesterday_close != 0 else 0
            change_percent = (change / yesterday_close) * 100 if yesterday_close != 0 else 0
            data_list.append({
                "基金代码": code, "基金名称": FUNDS.get(code, parts[0]),
                "最新价": current_price, "昨收": yesterday_close,
                "涨跌额": f"{change:+.3f}", "涨跌幅(%)": change_percent,
                "数据日期": parts[30], "数据时间": parts[31]
            })
        return data_list
    except requests.exceptions.RequestException as e:
        st.error(f"网络请求失败: {e}")
        return None
    except Exception as e:
        st.error(f"数据解析失败: {e}")
        return None


# 4. 新增：获取历史数据 (Tencent API) 并添加缓存
@st.cache_data(ttl=3600)  # 缓存1小时
def fetch_historical_data(fund_code):
    """获取单只基金近一年的日K线数据"""
    full_code = get_full_code(fund_code)
    if not full_code:
        return None

    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={full_code},day,,,365,qfq"
    headers = {'Referer': 'http://gu.qq.com'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = json.loads(response.text)

        # 数据通常在 'data' -> 'sh510300' -> 'qfqday' (复权日线)
        data_key = f"qfqday"
        fund_data_list = json_data.get('data', {}).get(full_code, {}).get(data_key, [])

        if not fund_data_list:
            # 如果没有复权数据，尝试获取未复权数据
            data_key = "day"
            fund_data_list = json_data.get('data', {}).get(full_code, {}).get(data_key, [])

        if not fund_data_list:
            return None

        df = pd.DataFrame(fund_data_list, columns=['日期', '开盘', '收盘', '最高', '最低', '成交量', 'c1', 'c2'])
        df = df[['日期', '收盘']]
        df['日期'] = pd.to_datetime(df['日期'])
        df['收盘'] = pd.to_numeric(df['收盘'])
        return df
    except Exception as e:
        # st.error(f"获取 {fund_code} 历史数据失败: {e}") # 调试时可打开
        return None


# --- Streamlit 页面渲染 ---

# 标题和副标题
st.title("🚀 动态基金看板")
st.caption("数据来源：新浪财经、腾讯财经 | 本页面数据仅供参考，不构成投资建议。")

# 占位符和刷新按钮
placeholder = st.empty()
if st.button('🔄 手动刷新', key='refresh_button'):
    st.cache_data.clear()  # 点击刷新时清除缓存

with placeholder.container():
    with st.spinner("正在抓取最新数据..."):
        fund_data = fetch_fund_data(list(FUNDS.keys()))

    if not fund_data:
        st.error("无法获取基金数据，请稍后再试或检查基金代码。")
    else:
        # --- 数据时间判断与展示 ---
        first_fund_date_str = fund_data[0]['数据日期']
        china_tz = pytz.timezone('Asia/Shanghai')
        today_str = datetime.now(china_tz).strftime('%Y-%m-%d')

        if first_fund_date_str == today_str:
            st.success(f"✅ **数据显示为今日（{today_str}）实时行情**", icon="📈")
        else:
            st.warning(f"⚠️ **市场已收盘，当前显示为 {first_fund_date_str} 的收盘数据**", icon="🌃")

        st.divider()

        # --- 基金信息卡片展示 ---
        cols = st.columns(3)
        for i, data in enumerate(fund_data):
            col = cols[i % 3]
            with col:
                st.metric(
                    label=f"{data['基金名称']} ({data['基金代码']})",
                    value=f"{data['最新价']:.3f}",
                    delta=f"{data['涨跌幅(%)']:.2f}% ( {data['涨跌额']} )"
                )

        st.divider()

        # --- 新增：折线图展示 ---
        st.subheader("📈 近期走势对比")

        # 多选框，让用户选择要显示的基金
        selected_funds = st.multiselect(
            '选择要对比的基金（建议不超过4个）:',
            options=list(FUNDS.keys()),
            format_func=lambda code: f"{FUNDS[code]} ({code})",  # 显示名称而非代码
            default=['510300', '159995']  # 默认显示沪深300和芯片ETF
        )

        if selected_funds:
            chart_data_frames = []
            for code in selected_funds:
                hist_df = fetch_historical_data(code)
                if hist_df is not None:
                    # 将收盘价列重命名为基金名称，并设置日期为索引
                    hist_df = hist_df.rename(columns={'收盘': FUNDS[code]})
                    hist_df = hist_df.set_index('日期')
                    chart_data_frames.append(hist_df)

            if chart_data_frames:
                # 合并所有选择的基金数据
                combined_df = pd.concat(chart_data_frames, axis=1)
                # 填充缺失值（例如停牌日），使用前一天的收盘价
                combined_df = combined_df.ffill()

                st.line_chart(combined_df)
            else:
                st.warning("未能获取所选基金的历史数据用于绘图。")
        else:
            st.info("请在上方选择至少一只基金以显示走势图。")

        st.divider()

        # --- 详细数据表格展示 ---
        st.subheader("📊 详细数据一览")
        display_df = pd.DataFrame(fund_data)
        display_df['涨跌幅(%)'] = display_df['涨跌幅(%)'].map('{:+.2f}%'.format)


        def color_change(val):
            if val.startswith('+'):
                return 'color: red;'
            elif val.startswith('-'):
                return 'color: green;'
            return 'color: black;'


        styled_df = display_df[['基金代码', '基金名称', '最新价', '昨收', '涨跌幅(%)', '数据日期', '数据时间']].style.apply(
            lambda col: col.map(color_change), subset=['涨跌幅(%)']
        ).format({"最新价": "{:.3f}", "昨收": "{:.3f}"})
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
