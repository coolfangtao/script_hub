import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# 1. 定义您关注的基金列表
# 键是基金代码，值是基金名称
FUNDS = {
    "510300": "沪深300ETF",
    "518880": "黄金ETF",
    "159558": "半导体设备ETF易方达",
    "515980": "人工智能ETF",
    "159715": "稀土ETF易方达",
    "512560": "军工ETF易方达"
}


# 2. 根据基金代码获取完整的市场代码 (例如 510300 -> sh510300)
def get_full_code(code):
    """根据基金代码判断是上海(sh)还是深圳(sz)市场"""
    if code.startswith('51'):
        return f"sh{code}"
    elif code.startswith('15'):
        return f"sz{code}"
    else:
        return ""


# 3. 核心功能：通过HTTP请求从新浪财经获取数据并解析
def fetch_fund_data(fund_codes):
    """
    通过HTTP请求从新浪财经获取多个基金的实时数据。

    Args:
        fund_codes (list): 包含基金代码的列表, e.g., ["510300", "159558"]

    Returns:
        list: 一个包含每个基金数据的字典列表
    """
    if not fund_codes:
        return []

    full_codes = [get_full_code(code) for code in fund_codes if get_full_code(code)]
    url = f"http://hq.sinajs.cn/list={','.join(full_codes)}"
    headers = {
        'Referer': 'http://finance.sina.com.cn'  # 添加Referer头，模拟浏览器请求
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 如果请求失败则抛出异常
        response.encoding = 'gbk'  # 新浪财经接口使用GBK编码

        data_list = []
        raw_text = response.text
        # 使用正则表达式匹配每个基金的数据
        # var hq_str_sh510300="...";
        pattern = re.compile(r'var hq_str_(\w+)="([^"]+)";')
        matches = pattern.findall(raw_text)

        for match in matches:
            code_full, data_str = match
            code = code_full[2:]  # 去掉 sh/sz 前缀

            if not data_str:
                continue

            parts = data_str.split(',')

            # 解析数据 (根据新浪财经的ETF数据格式)
            # 0: 基金名称
            # 1: 今日开盘价
            # 2: 昨日收盘价
            # 3: 当前价格
            # 4: 今日最高价
            # 5: 今日最低价
            # ... 更多数据我们暂时不需要

            name = FUNDS.get(code, parts[0])  # 优先使用我们定义的名称
            yesterday_close = float(parts[2])
            current_price = float(parts[3])

            if yesterday_close == 0:
                change_percent = 0
            else:
                change = current_price - yesterday_close
                change_percent = (change / yesterday_close) * 100

            data_list.append({
                "基金代码": code,
                "基金名称": name,
                "最新价": f"{current_price:.3f}",
                "昨收": f"{yesterday_close:.3f}",
                "涨跌幅(%)": f"{change_percent:+.2f}%"
            })

        return data_list

    except requests.exceptions.RequestException as e:
        st.error(f"网络请求失败: {e}")
        return None
    except Exception as e:
        st.error(f"数据解析失败: {e}")
        return None


# 4. Streamlit 页面布局
st.set_page_config(page_title="基金涨跌观察面板", layout="wide")

st.title("📈 基金涨跌观察面板")
st.markdown(f"数据更新时间: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}** (数据源：新浪财经)")

# 创建一个占位符，用于后续更新数据
data_placeholder = st.empty()


# 5. 定义数据展示和样式
def display_data():
    fund_data = fetch_fund_data(list(FUNDS.keys()))

    if fund_data:
        df = pd.DataFrame(fund_data)

        # 定义涨跌颜色函数 (A股市场习惯：红涨绿跌)
        def color_change(val):
            if isinstance(val, str) and val.endswith('%'):
                num_val = float(val.strip('%'))
                if num_val > 0:
                    return 'color: red;'
                elif num_val < 0:
                    return 'color: green;'
            return 'color: black;'

        # 应用样式
        styled_df = df.style.apply(
            lambda col: col.map(color_change), subset=['涨跌幅(%)']
        ).format({
            "最新价": "{:}",
            "昨收": "{:}",
            "涨跌幅(%)": "{:}"
        })

        # 在占位符中显示数据表格
        data_placeholder.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        data_placeholder.warning("暂时无法获取基金数据，请稍后刷新。")


# 添加一个手动刷新按钮
if st.button('手动刷新'):
    st.toast("正在刷新数据...")
    display_data()

# 页面首次加载时自动执行一次
display_data()

st.info("ℹ️ 本页面数据仅供参考，不构成任何投资建议。")