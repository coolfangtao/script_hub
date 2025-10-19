# 文件路径: streamlit_app.py

import streamlit as st
from shared.sidebar import create_common_sidebar  # 导入我们创建的侧边栏函数
from shared.changelog import show_changelog
# from shared.feedback import render_feedback_section # <-- 1. 导入新的反馈函数

# --- 页面基础设置 (必须是第一个st命令) ---
st.set_page_config(
    page_title="FT的脚本中心",
    page_icon="🚀",
    layout="wide"
)

# --- 渲染侧边栏 ---
# 这一行代码会负责搞定所有侧边栏的显示逻辑
create_common_sidebar()

# =====================================================================
# --- 新的主页内容 ---
# =====================================================================

# --- 1. 欢迎横幅 ---
st.title("🚀 欢迎来到 FT 的脚本中心")
st.markdown("一个集成了运营维护、文本处理和图像处理等多种高效工具的在线平台。")
st.markdown("---")

# --- 2. 核心功能 & 快速入口 ---
st.subheader("🌟 核心功能一览")
st.write("从左侧导航栏选择一个工具开始使用，或通过下方卡片快速进入核心功能。")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown("<h5>📊 关键词结果合并</h5>", unsafe_allow_html=True)
        st.write("一键将多个ASIN的关键词分析Excel文件合并成一个总表，方便后续分析。")
        if st.button("立即开始", key="merge_asin", use_container_width=True):
            st.switch_page(r"pages/2_关键词统计.py")

with col2:
    with st.container(border=True):
        st.markdown("<h5>🖼️ 智能替换背景</h5>", unsafe_allow_html=True)
        st.write("上传产品图，自动移除并替换为指定的纯色或场景背景，提升图片质量。")
        if st.button("立即开始", key="remove_bg", use_container_width=True):
            st.switch_page(r"pages/5_替换图片背景.py")

with col3:
    with st.container(border=True):
        st.markdown("<h5>🔊 文字转语音</h5>", unsafe_allow_html=True)
        st.write("输入任意文本，选择多种音色，快速生成高质量的语音文件，支持多语言。")
        if st.button("立即开始", key="tts", use_container_width=True):
            st.switch_page(r"pages/3_文字转语音.py")

with col4:
    with st.container(border=True):
        st.markdown("<h5>🤖 AI工具</h5>", unsafe_allow_html=True)
        # 将这里的描述加长，让它和其他的差不多
        st.write("与强大的 AI 模型进行对话，无需特殊网络环境即可体验 Gemini 2.5 Pro。")
        if st.button("立即开始", key="ai", use_container_width=True):
            st.switch_page(r"pages/7_AI_对话页面.py")

st.markdown("---")

# --- 3. 更新日志 ---
# 原来的 st.subheader 和 st.expander 代码块被下面这行简单的函数调用取代
show_changelog() # <-- 2. 在这里调用函数

st.markdown("---")

# --- 4. 联系与反馈 ---
# render_feedback_section() # <-- 2. 在这里调用函数