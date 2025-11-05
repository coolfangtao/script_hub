# 文件路径: streamlit_app.py

import streamlit as st
from shared.sidebar import create_common_sidebar
from shared.update_log import show_changelog
from shared.feedback import setup_database, show_feedback_module
from shared.usage_tracker import get_usage_stats
import pandas as pd
from shared.pages_render import SCRIPTS_BY_GROUP

# --- 页面基础设置 (保持不变) ---
st.set_page_config(
    page_title="TF 的脚本中心",
    page_icon="🚀",
    layout="wide"
)

# --- 静态常量定义 (保持不变) ---
FRIENDLY_LINKS = [
    {
        "title": "PDF24 Tools: 免费且易于使用的在线PDF工具",
        "url": "https://tools.pdf24.org/zh/"
    },
    {
        "title": "imagesTool: 在线图片处理工具集",
        "url": "https://imagestool.com/zh_CN/"
    },
    {
        "title": "AConvert: 免费在线文件格式转换",
        "url": "https://www.aconvert.com/cn/"
    },
    {
        "title": "菜鸟工具: 不止于工具",
        "url": "https://www.jyshare.com/"
    },
    {
        "title": "MikuTools: 一个轻量的工具集合",
        "url": "https://tools.miku.ac/"
    },
    {
        "title": "Waifu2x: 图像无损放大",
        "url": "https://www.waifu2x.net/"
    },
    {
        "title": "GD音乐台: GD Studio's Online Music Platform",
        "url": "https://music.gdstudio.org/"
    }
]


# --- 页面核心功能函数 ---

# --- 1. 修改 create_feature_card ---
def create_feature_card(title, button_key, target_page):
    """
    创建一个标准的功能展示卡片。
    (已移除 description, 采用自动高度)
    """
    # 移除固定的 height=180
    with st.container(border=True):
        # 标题 (包含 emoji)
        st.markdown(f"""
            <p style='
                text-align: center; 
                font-weight: 500; 
                font-size: 1.1em;
                height: 3.5em; /* 保持一个最小高度, 确保标题能对齐 */
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 5px; /* 减少和按钮的间距 */
            '>
                {title}
            </p>
        """, unsafe_allow_html=True)

        # 移除所有 description 和 占位符 相关的代码

        if st.button("立即开始", key=button_key, use_container_width=True):
            st.switch_page(target_page)


def display_welcome_banner():
    """
    显示页面的欢迎横幅。(保持不变)
    """
    st.title("🚀 TF 的脚本中心")
    # --- 座右铭 (保持不变) ---
    st.markdown(
        """
        <p style='
            text-align: center; 
            font-style: italic; 
            font-family: "Georgia", serif; 
            color: #777; 
            font-size: 1.1em;
            letter-spacing: 0.5px;
            margin-top: -10px;
        '>
            节约生命，在混乱中创造秩序。
        </p>
        """,
        unsafe_allow_html=True
    )
    # --- 座右铭结束 ---
    # st.markdown("⬅️ 请从左侧侧边栏选择一个工具开始使用。")


# --- 2. 修改 display_core_features ---
def display_core_features():
    """
    显示核心功能模块。
    (动态从 SCRIPTS_BY_GROUP 加载所有脚本, 按分组平铺)
    """

    for group_name, scripts_in_group in SCRIPTS_BY_GROUP.items():
        st.subheader(group_name, divider="rainbow")

        CARDS_PER_ROW = 4
        cols = st.columns(CARDS_PER_ROW)

        for i, script in enumerate(scripts_in_group):
            col_index = i % CARDS_PER_ROW
            with cols[col_index]:
                # --- 这里的调用已简化, 移除了 description ---
                create_feature_card(
                    title=script["label"],
                    button_key=script["path"],
                    target_page=script["path"]
                )



def display_usage_stats():
    """
    显示脚本使用统计数据。(使用 st.metric)
    """

    # 从 tracker 获取缓存的数据
    usage_data = get_usage_stats()

    if not usage_data:
        st.info("暂无使用数据。")
        return

    try:
        # --- 1. 计算关键指标 ---

        # 指标1: 总访问次数
        total_views = sum(d.get("count", 0) for d in usage_data.values())

        # 指标2: 最受欢迎的脚本
        # (确保 usage_data 不为空)
        most_popular_item = max(
            usage_data.items(),
            key=lambda item: item[1].get("count", 0),
            default=(None, {})
        )
        most_popular_label = most_popular_item[0] if most_popular_item[0] else "N/A"
        most_popular_count = most_popular_item[1].get("count", 0)

        # 指标3: 已跟踪脚本数
        unique_scripts = len(usage_data)

        # --- 2. 使用 st.metric 在列中显示指标 ---
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(label="总访问次数", value=total_views)

        with col2:
            # 我们用 value 显示脚本名, 用 delta 显示它的次数
            st.metric(label="最受欢迎的脚本",
                      value=most_popular_label,
                      delta=f"{most_popular_count} 次访问")

        with col3:
            st.metric(label="已跟踪脚本数", value=unique_scripts)

        # --- 3. 显示详细数据表格 (保持不变) ---
        st.subheader("详细统计")
        df_data = [
            {
                "脚本名称": label,
                "访问次数": d.get("count", 0),
                "最近访问": d.get("last_visited", "N/A")
            }
            for label, d in usage_data.items()
        ]

        df = pd.DataFrame(df_data)

        # --- (START) 新增的美化步骤 ---

        # 步骤 1: (时间格式化) 将 "最近访问" 列转换为 datetime 对象
        # errors='coerce' 会将 "N/A" 或其他无效日期转为 NaT (Not a Time)
        df["最近访问"] = pd.to_datetime(df["最近访问"], errors='coerce')

        # 步骤 2: (排序) 必须在将 "访问次数" 转为字符串之前进行排序
        df = df.sort_values(by="访问次数", ascending=False).reset_index(drop=True)

        # 步骤 3: (时间格式化) 将 datetime 对象格式化为指定的中文Sring
        # NaT (源自 "N/A") 会在这一步变成 NaN
        df["最近访问"] = df["最近访问"].dt.strftime("%Y年%m月%d日 %H:%M:%S")

        # 步骤 4: (时间格式化) 将 NaN 值填充回 "N/A"，保持显示一致
        df["最近访问"] = df["最近访问"].fillna("N/A")

        # 步骤 5: (左对齐) 将 "访问次数" 列转换为字符串类型。
        # st.dataframe 会自动左对齐字符串类型的列。
        df["访问次数"] = df["访问次数"].astype(str)

        # --- (END) 新增的美化步骤 ---

        st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        # 捕获新的未知错误
        st.error(f"渲染统计数据时出错: {e}")
        st.error("原始数据：")
        st.json(usage_data)  # 调试用：显示原始数据


def display_friendly_links():
    """显示友情链接模块。"""

    for link in FRIENDLY_LINKS:
        with st.container(border=True):
            st.markdown(f"##### {link['title']}")
            st.link_button("前往查看 →", link['url'])
    st.divider()


def display_footer():
    """显示页脚信息。"""
    st.markdown(
        """
        <p style='text-align: center; color: grey;'>
            © 2025 TF的脚本中心 | ✉️ 邮箱：19210860039@fudan.edu.cn
        </p>
        """,
        unsafe_allow_html=True
    )


# --- main() 函数保持不变 ---
def main():
    """
    应用主函数，负责渲染整个页面。
    """
    # --- 1. 渲染侧边栏和初始化 ---
    create_common_sidebar(current_label="🏠 主页")
    setup_database()

    # --- 2. 页面主体内容渲染 ---
    # 欢迎横幅保留在Tabs的上方，作为全局标题
    display_welcome_banner()

    # --- 3. 创建Tabs来组织页面内容 ---
    # 定义Tab的名称，使用Emoji增加可读性
    tab_labels = [
        "🌟 功能中心",  # 核心功能 -> 改名为 功能中心
        "📊 脚本使用统计",
        "🔄 最近更新",
        "✉️ 用户反馈",
        "🔗 友情链接"
    ]

    # 创建Tabs
    tab_core, tab_stats, tab_changelog, tab_feedback, tab_links = st.tabs(tab_labels)

    # --- 填充每个Tab的内容 ---

    # Tab 1: 功能中心 (默认显示)
    with tab_core:
        display_core_features()

        # Tab 2: 脚本使用统计
    with tab_stats:
        display_usage_stats()

    # Tab 3: 最近更新
    with tab_changelog:
        show_changelog()

    # Tab 4: 用户反馈
    with tab_feedback:
        show_feedback_module()

    # Tab 5: 友情链接
    with tab_links:
        display_friendly_links()

    # --- 4. 页脚 ---
    display_footer()


# --- 程序入口 ---
if __name__ == "__main__":
    main()