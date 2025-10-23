import streamlit as st

def get_app_mode():
    """
    通过检查st.secrets来确定应用是运行在本地开发者模式还是云端模式。

    如果在 .streamlit/secrets.toml 文件中设置了 APP_MODE = "local_dev"，
    则返回 "local"。否则，返回 "cloud"。

    Returns:
        str: "local" 或 "cloud"
    """
    # st.secrets.get() 是一个安全的方法，如果密钥不存在，它会返回None
    if st.secrets.get("APP_MODE") == "local_dev":
        return "local"
    else:
        return "cloud"

# 在应用启动时获取运行模式
# 我们可以将其存储在 st.session_state 中，以便在应用的任何地方都能方便地访问
if "app_mode" not in st.session_state:
    st.session_state.app_mode = get_app_mode()


# --- 使用示例 ---

st.title("运行模式检测示例")

# 根据检测到的模式显示不同的信息
if st.session_state.app_mode == "local":
    st.success("✅ 当前为【本地开发者模式】。")
    st.info("将启用数据自动保存等本地专属功能。")
else: # cloud mode
    st.info("☁️ 当前为【云端模式】。")
    st.warning("数据仅在会话期间保留，请注意手动导出。")

# 你可以在代码的任何地方使用 st.session_state.app_mode 来控制逻辑
if st.button("显示界面"):
    if st.session_state.app_mode == "local":
        st.write("为本地开发者展示特殊面板...")
        # 在这里放置你的本地模式UI代码
    else:
        st.write("为云端用户展示通用面板...")
        # 在这里放置你的云端模式UI代码