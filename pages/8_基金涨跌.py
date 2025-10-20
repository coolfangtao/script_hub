import streamlit as st
import akshare as ak
import pandas as pd

# --- 页面基础设置 ---
# st.set_page_config 是 Streamlit 的一个命令，用于设置页面的基本属性，比如标题、图标和布局。
# page_title: 设置浏览器选项卡上显示的标题。
# layout="wide": 让页面内容占满整个屏幕宽度，提供更宽敞的显示空间。
st.set_page_config(page_title="基金涨跌看板", layout="wide")

# --- 应用标题和描述 ---
st.title("📈 基金涨跌看板")
st.caption("在这里跟踪您关注的场内基金的最新表现。数据来源于天天基金网。")


# --- 数据获取与缓存 ---
# @st.cache_data 是一个装饰器，它可以缓存函数返回的数据。
# 当函数以相同的参数再次被调用时，Streamlit 会直接返回缓存的结果，而不是重新执行函数。
# 这对于耗时的数据获取操作（如API请求）非常有用，可以显著提升应用性能。
# ttl=3600 设置缓存的存活时间为3600秒（1小时），之后缓存会失效，数据将重新获取。
@st.cache_data(ttl=3600)
def get_fund_data():
    """
    使用 akshare 获取所有场内交易基金的排名数据，并进行初步处理。
    """
    try:
        # 从 akshare 获取数据
        df = ak.fund_exchange_rank_em()

        # --- 数据清洗和预处理 ---
        # 确保'代码'列为字符串类型，以便进行准确的匹配和筛选
        df['代码'] = df['代码'].astype(str)

        # 将日期相关列转换为统一的 'YYYY-MM-DD' 格式的字符串
        date_columns = ['日期', '成立日期']
        for col in date_columns:
            # pd.to_datetime 将文本转换为日期对象，errors='coerce' 会将无法转换的值设为 NaT（非时间）
            # .dt.strftime('%Y-%m-%d') 将日期对象格式化为字符串
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

        # 将所有列中的空值 (NaN) 填充为 '--'，使表格显示更友好
        df = df.fillna('--')
        return df
    except Exception as e:
        # 如果数据获取过程中发生任何错误，则在页面上显示错误提示，并返回一个空的DataFrame
        st.error(f"数据加载失败，请稍后重试。错误信息: {e}")
        return pd.DataFrame()


def style_change_rate(val):
    """
    根据单元格数值的正负，返回对应的CSS颜色样式。
    用于高亮显示涨跌幅数据。
    """
    # 检查值是否为数字类型
    if isinstance(val, (int, float)):
        # 小于0显示红色，大于0显示绿色，等于0显示黑色
        color = 'red' if val < 0 else 'green' if val > 0 else 'black'
        return f'color: {color}'
    # 如果不是数字，则不应用任何样式
    return ''


# --- 主应用逻辑 ---
# 加载数据
all_funds_df = get_fund_data()

# 只有在数据成功加载后才显示主要内容
if not all_funds_df.empty:

    # --- 侧边栏交互 ---
    st.sidebar.header("筛选设置")

    # 创建一个包含基金代码和名称的列表，用于多选框的选项
    fund_options = all_funds_df['代码'] + " - " + all_funds_df['名称']

    # 设置一些默认关注的基金，作为应用启动时的示例
    default_funds_codes = ['510300', '513100', '159949', '512170']  # 示例: 沪深300, 纳指ETF, 创业板50, 医疗ETF
    # 根据默认代码列表，在 fund_options 中找到对应的完整选项
    default_selections = [opt for opt in fund_options if any(code in opt for code in default_funds_codes)]

    # 创建一个多选框，让用户可以选择自己关注的基金
    selected_funds = st.sidebar.multiselect(
        "选择您关注的基金 (可搜索):",
        options=fund_options,
        default=default_selections
    )

    # 从用户选择的 "代码 - 名称" 字符串中提取出基金代码
    selected_codes = [fund.split(" - ")[0] for fund in selected_funds]

    # --- 内容展示 ---
    st.subheader("⭐ 我关注的基金")
    if selected_codes:
        # 根据用户选择的代码筛选出对应的基金数据
        watched_df = all_funds_df[all_funds_df['代码'].isin(selected_codes)].copy()

        # 定义需要应用颜色样式的涨跌幅列
        rate_columns = ['日增长率', '今年来', '近1周', '近1月', '近3月', '近6月', '近1年', '近2年', '近3年']

        # 将这些列的数值转换为数字类型，以便进行样式判断。无法转换的将变为NaN。
        for col in rate_columns:
            if col in watched_df.columns:
                watched_df[col] = pd.to_numeric(watched_df[col], errors='coerce')

        # 使用 st.dataframe 展示数据，并应用样式
        # .style.map() 应用颜色函数
        # .format() 将数字格式化为带两位小数和百分号的字符串，并将NaN值显示为'--'
        st.dataframe(
            watched_df.style.map(style_change_rate, subset=rate_columns).format("{:.2f}%", subset=rate_columns,
                                                                                na_rep='--'),
            use_container_width=True # 让表格宽度自适应容器
        )
    else:
        # 如果用户没有选择任何基金，则显示提示信息
        st.info("请在左侧边栏选择您关注的基金，以便在此处快速查看。")

    # --- 显示所有基金的排名 ---
    st.divider() # 添加一条分割线
    st.subheader("📊 所有场内基金排名")

    # 为了性能，对完整的列表数据进行同样的处理和展示
    full_df_styled = all_funds_df.copy()
    for col in rate_columns:
        if col in full_df_styled.columns:
            full_df_styled[col] = pd.to_numeric(full_df_styled[col], errors='coerce')

    st.dataframe(
        full_df_styled.style.map(style_change_rate, subset=rate_columns).format("{:.2f}%", subset=rate_columns,
                                                                                na_rep='--'),
        height=600, # 设置一个固定高度，使表格可以滚动
        use_container_width=True
    )
