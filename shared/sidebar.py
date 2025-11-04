# 文件路径: shared/sidebar.py
import streamlit as st
from shared.elements import shin_chan_animation
from shared.usage_tracker import track_page_visit
from shared.pages_render import SCRIPTS_BY_GROUP

def create_common_sidebar(current_label=None):
    """
    在Streamlit应用的侧边栏中创建一个可折叠的公共分组导航。

    :param current_label: (str, 可选) 当前页面的标签。
                          如果提供了，将触发页面访问跟踪。
    """

    if current_label == "🏠 主页":
        # 1. 如果是主页，只设置一个待办标记
        # 我们假设这可能是个机器人，暂不记录
        st.sidebar.caption(f"当前页面: {current_label}")
        st.session_state["pending_home_visit"] = True

    elif current_label:
        # 2. 如果是任何其他子页面 (证明是人类)
        st.sidebar.caption(f"当前页面: {current_label}")
        # 我们调用跟踪函数，它会智能处理“待办”的主页访问
        track_page_visit(current_label)

    else:
        st.sidebar.caption("未跟踪当前页面")

    # 1. 注入CSS以隐藏默认的Streamlit导航 (保持不变)
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. 创建自定义的侧边栏头部 (保持不变)
    st.sidebar.page_link("streamlit_app.py", label="🏠 返回主页")
    st.sidebar.title("🛠️ 功能导航")
    st.sidebar.divider()

    # --- 主要修改部分 ---
    # 3. 使用 st.expander 创建可折叠的导航菜单
    for group_name, scripts_in_group in SCRIPTS_BY_GROUP.items():
        # 为每个分组创建一个可折叠的容器
        # expanded=False 表示默认是折叠的, 你可以根据需要设置为 True 让某个分组默认展开
        with st.sidebar.expander(group_name, expanded=True):
            # 在折叠容器内部，为每个脚本创建页面链接
            for script in scripts_in_group:
                st.page_link(script["path"], label=script["label"])


    # 5. 小新动画
    shin_chan_animation()