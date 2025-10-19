# 文件路径: streamlit_app.py

import streamlit as st
from shared.sidebar import create_common_sidebar, SCRIPTS_BY_GROUP # <-- 1. 导入函数

# --- 页面基础设置 (必须是第一个st命令) ---
st.set_page_config(layout="wide")

# --- 创建侧边栏 ---
create_common_sidebar() # <-- 2. 调用函数

# --- 页面主内容 ---
st.title("🚀 FT的脚本中心")
st.markdown("---")

# ... (你主页上所有的按钮和布局代码保持不变) ...
# 注意：主页按钮需要的数据源也应该从 sidebar.py 导入，以保证统一
# 为了简单起见，这里先省略，你可以自行优化
# 完整的代码应该从 shared.sidebar 导入 scripts_by_group 字典

NUM_COLUMNS = 3
for group_name, scripts_in_group in SCRIPTS_BY_GROUP.items():
    with st.expander(group_name, expanded=True):
        cols = st.columns(NUM_COLUMNS)
        for index, script in enumerate(scripts_in_group):
            col = cols[index % NUM_COLUMNS]
            with col:
                if st.button(script["label"], help=script.get("help", script["label"]), use_container_width=True, key=script["path"] + str(index)):
                    st.switch_page(script["path"])
st.markdown("---")
st.info("💡 提示：点击上方按钮或左侧导航栏，即可跳转到对应的工具页面。")