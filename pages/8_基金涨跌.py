import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import pytz
import json
from shared.sidebar import create_common_sidebar


# --- 1. 配置类 ---
class Config:
    """统一存放所有配置和硬编码值"""
    PAGE_TITLE = "动态基金看板"
    PAGE_ICON = "🚀"

    # 关注的基金列表 {代码: 名称}
    FUNDS = {
        "518880": "黄金ETF",
        "510300": "沪深300ETF",
        "159995": "半导体芯片ETF",
        "515980": "人工智能ETF",
        "516780": "稀土产业ETF",
        "512660": "军工ETF"
    }

    # API 配置
    SINA_API_URL = "http://hq.sinajs.cn/list={}"
    TENCENT_API_URL = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={},day,,,365,qfq"
    SINA_HEADERS = {'Referer': 'http://finance.sina.com.cn'}
    TENCENT_HEADERS = {'Referer': 'http://gu.qq.com'}

    # UI 默认配置
    DEFAULT_CHART_SELECTION = ['510300', '159995']  # 图表默认显示沪深300和芯片ETF

    # 其他配置
    TIMEZONE = pytz.timezone('Asia/Shanghai')


# --- 2. 数据处理 ---

def get_full_code(code):
    """根据基金代码判断是上海(sh)还是深圳(sz)市场"""
    if code.startswith('51') or code.startswith('58'):
        return f"sh{code}"
    elif code.startswith('15'):
        return f"sz{code}"
    return ""


# 使用缓存，减少频繁请求。TTL(time-to-live)设为60秒，避免刷新过快。
@st.cache_data(ttl=60)
def fetch_realtime_data(fund_codes):
    """通过HTTP请求从新浪财经获取多个基金的实时数据。"""
    if not fund_codes:
        return []

    full_codes = [get_full_code(code) for code in fund_codes if get_full_code(code)]
    url = Config.SINA_API_URL.format(','.join(full_codes))

    try:
        response = requests.get(url, headers=Config.SINA_HEADERS)
        response.raise_for_status()
        response.encoding = 'gbk'
        data_list = []
        pattern = re.compile(r'var hq_str_(\w+)="([^"]+)";')
        matches = pattern.findall(response.text)

        for code_full, data_str in matches:
            code = code_full[2:]
            if not data_str: continue
            parts = data_str.split(',')
            yesterday_close = float(parts[2])
            current_price = float(parts[3])
            change = current_price - yesterday_close if yesterday_close != 0 else 0
            change_percent = (change / yesterday_close) * 100 if yesterday_close != 0 else 0

            data_list.append({
                "基金代码": code, "基金名称": Config.FUNDS.get(code, parts[0]),
                "最新价": current_price, "昨收": yesterday_close,
                "涨跌额": f"{change:+.3f}", "涨跌幅(%)": change_percent,
                "数据日期": parts[30], "数据时间": parts[31]
            })
        return data_list
    except requests.exceptions.RequestException as e:
        st.error(f"网络请求失败: {e}")
    except Exception as e:
        st.error(f"数据解析失败: {e}")
    return None


@st.cache_data(ttl=3600)  # 缓存1小时
def fetch_historical_data(fund_code):
    """获取单只基金近一年的日K线数据"""
    full_code = get_full_code(fund_code)
    if not full_code: return None

    url = Config.TENCENT_API_URL.format(full_code)
    try:
        response = requests.get(url, headers=Config.TENCENT_HEADERS)
        response.raise_for_status()
        json_data = response.json()

        data_key = "qfqday"
        fund_data_list = json_data.get('data', {}).get(full_code, {}).get(data_key)
        if not fund_data_list:
            data_key = "day"
            fund_data_list = json_data.get('data', {}).get(full_code, {}).get(data_key, [])
        if not fund_data_list: return None

        df = pd.DataFrame(fund_data_list, columns=['日期', '开盘', '收盘', '最高', '最低', '成交量', 'c1', 'c2'])
        df = df[['日期', '收盘']]
        df['日期'] = pd.to_datetime(df['日期'])
        df['收盘'] = pd.to_numeric(df['收盘'])
        return df
    except Exception:
        return None


# --- 3. UI界面类 ---
class FundDashboardUI:
    """管理所有Streamlit UI组件的渲染"""

    def __init__(self):
        self.config = Config()

    def setup_page(self):
        """设置页面基础配置"""
        st.set_page_config(
            page_title=self.config.PAGE_TITLE,
            page_icon=self.config.PAGE_ICON,
            layout="wide"
        )

    def render_header(self):
        """渲染页面标题和说明"""
        st.title(f"{self.config.PAGE_ICON} {self.config.PAGE_TITLE}")
        st.caption("数据来源：新浪财经、腾讯财经 | 本页面数据仅供参考，不构成投资建议。")

    def render_status_message(self, fund_data):
        """根据数据日期显示当前是实时行情还是收盘数据"""
        if not fund_data: return

        first_fund_date_str = fund_data[0]['数据日期']
        today_str = datetime.now(self.config.TIMEZONE).strftime('%Y-%m-%d')

        if first_fund_date_str == today_str:
            st.success(f"✅ **数据显示为今日（{today_str}）实时行情**", icon="📈")
        else:
            st.warning(f"⚠️ **市场已收盘，当前显示为 {first_fund_date_str} 的收盘数据**", icon="🌃")

    def render_metric_cards(self, fund_data):
        """以卡片形式展示各基金的核心指标（自定义布局）"""
        if not fund_data: return

        cols = st.columns(3)
        for i, data in enumerate(fund_data):
            with cols[i % 3], st.container(border=True):
                # 1. 准备数据和样式
                change_percent = data['涨跌幅(%)']
                color = "green" if change_percent >= 0 else "red"
                arrow = "↑" if change_percent >= 0 else "↓"
                delta_text = f"{arrow} {change_percent:.2f}% ( {data['涨跌额']} )"

                # 2. 渲染基金名称和代码
                st.markdown(f"**{data['基金名称']} ({data['基金代码']})**")

                # 3. 渲染自定义的涨跌幅（使用大号字体）
                st.markdown(f'<p style="color:{color}; font-size: 2.5rem; font-weight: bold;">{delta_text}</p>',
                            unsafe_allow_html=True)

                # 4. 渲染最新价格（使用小号字体）
                st.markdown(f'<p style="font-size: 1.25rem;">{data["最新价"]:.3f}</p>',
                            unsafe_allow_html=True)

    def render_historical_chart(self):
        """渲染历史走势对比的折线图"""
        st.subheader("📈 近期走势对比")
        selected_funds = st.multiselect(  # <-- 已修正拼写错误
            '选择要对比的基金（建议不超过4个）:',
            options=list(self.config.FUNDS.keys()),
            format_func=lambda code: f"{self.config.FUNDS[code]} ({code})",
            default=self.config.DEFAULT_CHART_SELECTION
        )

        if not selected_funds:
            st.info("请在上方选择至少一只基金以显示走势图。")
            return

        chart_data_frames = []
        for code in selected_funds:
            hist_df = fetch_historical_data(code)
            if hist_df is not None:
                hist_df = hist_df.rename(columns={'收盘': self.config.FUNDS[code]}).set_index('日期')
                chart_data_frames.append(hist_df)

        if chart_data_frames:
            combined_df = pd.concat(chart_data_frames, axis=1).ffill()
            st.line_chart(combined_df)
        else:
            st.warning("未能获取所选基金的历史数据用于绘图。")

    def _color_change(self, val):
        """根据涨跌幅字符串的正负返回不同颜色"""
        if val.startswith('+'):
            return 'color: green;'
        elif val.startswith('-'):
            return 'color: red;'
        return 'color: black;'

    def render_data_table(self, fund_data):
        """渲染详细数据的表格"""
        if not fund_data: return

        st.subheader("📊 详细数据一览")
        display_df = pd.DataFrame(fund_data)
        display_df['涨跌幅(%)'] = display_df['涨跌幅(%)'].map('{:+.2f}%'.format)

        styled_df = display_df[['基金代码', '基金名称', '涨跌幅(%)', '最新价', '昨收', '数据日期', '数据时间']].style.apply(
            lambda col: col.map(self._color_change), subset=['涨跌幅(%)']
        ).format({"最新价": "{:.3f}", "昨收": "{:.3f}"})

        st.dataframe(styled_df, use_container_width=True, hide_index=True)


# --- 4. 主程序入口 ---
def main():
    """主函数，组织页面逻辑"""
    ui = FundDashboardUI()
    ui.setup_page()
    create_common_sidebar()
    ui.render_header()

    # 手动刷新按钮
    if st.button('🔄 手动刷新', key='refresh_button'):
        # 清除所有缓存，并从 session_state 中移除数据标记
        st.cache_data.clear()
        if 'fund_data' in st.session_state:
            del st.session_state['fund_data']
        st.rerun()

    # 如果session中没有数据，则从API获取
    if 'fund_data' not in st.session_state:
        with st.spinner("正在抓取最新数据..."):
            st.session_state['fund_data'] = fetch_realtime_data(list(Config.FUNDS.keys()))

    # 从session中获取数据用于显示
    fund_data = st.session_state.get('fund_data')

    if not fund_data:
        st.error("无法获取基金数据，请稍后再试或检查基金代码。")
    else:
        # 依次渲染UI组件
        ui.render_status_message(fund_data)
        st.divider()
        ui.render_metric_cards(fund_data)
        st.divider()
        ui.render_historical_chart()
        st.divider()
        ui.render_data_table(fund_data)


if __name__ == "__main__":
    main()