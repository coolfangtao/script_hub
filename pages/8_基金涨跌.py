import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import pytz  # 用于处理时区

# --- 页面基础设置 ---
st.set_page_config(
    page_title="动态基金看板",
    page_icon="🚀",
    layout="wide"
)

# --- 核心数据与功能 ---

# 1. 定义您关注的基金列表
FUNDS = {
    "510300": "沪深300ETF",       # 场内基金
    "518880": "黄金ETF",          # 场内基金
    "159995": "芯片ETF",          # 场内基金 (替换了008888)
    "515980": "人工智能ETF",      # 场内基金 (替换了012734)
    "516780": "稀土产业ETF",      # 场内基金 (替换了011036)
    "512660": "军工ETF"           # 场内基金 (替换了015945)
}


# 2. 根据基金代码获取完整的市场代码 (例如 510300 -> sh510300)
def get_full_code(code):
    """根据基金代码判断是上海(sh)还是深圳(sz)市场"""
    if code.startswith('51') or code.startswith('58'):
        return f"sh{code}"
    elif code.startswith('15'):
        return f"sz{code}"
    else:
        return ""


# 3. 核心功能：通过HTTP请求从新浪财经获取数据并解析 (增强版)
def fetch_fund_data(fund_codes):
    """
    通过HTTP请求从新浪财经获取多个基金的实时数据。
    返回更丰富的数据，包括日期和时间。
    """
    if not fund_codes:
        return []

    full_codes = [get_full_code(code) for code in fund_codes if get_full_code(code)]
    # 添加一个时间戳参数防止HTTP缓存
    url = f"http://hq.sinajs.cn/list={','.join(full_codes)}"
    headers = {
        'Referer': 'http://finance.sina.com.cn'
    }

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

            if not data_str:
                continue

            parts = data_str.split(',')

            # --- 新浪财经数据索引 ---
            # 0: 基金名称, 1: 开盘价, 2: 昨收, 3: 现价, 4: 最高, 5: 最低
            # ...
            # 30: 日期, 31: 时间

            yesterday_close = float(parts[2])
            current_price = float(parts[3])

            if yesterday_close == 0:
                change = 0
                change_percent = 0
            else:
                change = current_price - yesterday_close
                change_percent = (change / yesterday_close) * 100

            data_list.append({
                "基金代码": code,
                "基金名称": FUNDS.get(code, parts[0]),
                "最新价": current_price,
                "昨收": yesterday_close,
                "涨跌额": f"{change:+.3f}",
                "涨跌幅(%)": change_percent,
                "数据日期": parts[30],
                "数据时间": parts[31]
            })

        return data_list

    except requests.exceptions.RequestException as e:
        st.error(f"网络请求失败: {e}")
        return None
    except Exception as e:
        st.error(f"数据解析失败: {e}")
        return None


# --- Streamlit 页面渲染 ---

# 标题和副标题
st.title("🚀 动态基金看板")
st.caption("数据来源：新浪财经 | 本页面数据仅供参考，不构成投资建议。")

# 占位符和刷新按钮
placeholder = st.empty()
if st.button('🔄 手动刷新', key='refresh_button'):
    # 点击按钮时，会重新运行整个脚本
    pass

with placeholder.container():
    # 数据加载期间显示Spinner
    with st.spinner("正在抓取最新数据..."):
        fund_data = fetch_fund_data(list(FUNDS.keys()))

    if not fund_data:
        st.error("无法获取基金数据，请稍后再试或检查基金代码。")
    else:
        # --- 数据时间判断与展示 ---
        # 获取第一条数据的时间来判断整体数据的新鲜度
        first_fund_date_str = fund_data[0]['数据日期']

        # 使用pytz获取中国标准时间
        china_tz = pytz.timezone('Asia/Shanghai')
        today_str = datetime.now(china_tz).strftime('%Y-%m-%d')

        if first_fund_date_str == today_str:
            st.success(f"✅ **数据显示为今日（{today_str}）实时行情**", icon="📈")
        else:
            st.warning(f"⚠️ **市场已收盘，当前显示为 {first_fund_date_str} 的收盘数据**", icon="🌃")

        st.divider()

        # --- 基金信息卡片展示 ---
        cols = st.columns(3)  # 每行显示3个卡片

        for i, data in enumerate(fund_data):
            col = cols[i % 3]
            with col:
                # 使用 st.metric 创建指标卡片
                st.metric(
                    label=f"{data['基金名称']} ({data['基金代码']})",
                    value=f"{data['最新价']:.3f}",
                    delta=f"{data['涨跌幅(%)']:.2f}% ( {data['涨跌额']} )"
                )

        st.divider()

        # --- 详细数据表格展示 ---
        st.subheader("📊 详细数据一览")

        # 准备用于显示的DataFrame
        display_df = pd.DataFrame(fund_data)

        # 格式化涨跌幅列，使其变为字符串以便应用样式
        display_df['涨跌幅(%)'] = display_df['涨跌幅(%)'].map('{:+.2f}%'.format)


        # 定义涨跌颜色函数
        def color_change(val):
            if val.startswith('+'):
                return 'color: red;'
            elif val.startswith('-'):
                return 'color: green;'
            return 'color: black;'


        # 应用样式
        styled_df = display_df[['基金代码', '基金名称', '最新价', '昨收', '涨跌幅(%)', '数据日期', '数据时间']].style.apply(
            lambda col: col.map(color_change), subset=['涨跌幅(%)']
        ).format({
            "最新价": "{:.3f}",
            "昨收": "{:.3f}",
        })

        st.dataframe(styled_df, use_container_width=True, hide_index=True)