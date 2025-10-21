# app.py
import streamlit as st
import requests
import base64
from shared.config import Config
from shared.sidebar import create_common_sidebar # 导入公共侧边栏函数
cfg = Config()
create_common_sidebar()  # 调用函数创建侧边栏

# --- 从 Streamlit Secrets 中安全地获取 API Key ---
try:
    IMGBB_API_KEY = st.secrets[cfg.IMGBB_API_KEY]
except KeyError:
    # 如果在secrets中找不到key，则设置为None，以便后续处理
    IMGBB_API_KEY = None

UPLOAD_API_URL = "https://api.imgbb.com/1/upload"


def upload_image_to_imgbb(image_bytes, filename):
    """
    将图片字节上传到 imgbb 服务并返回URL。

    Args:
        image_bytes (bytes): 图片的字节数据。
        filename (str): 原始文件名。

    Returns:
        str: 成功则返回图片URL，失败则返回错误信息。
    """
    # 检查API Key是否存在或是否正确配置
    if not IMGBB_API_KEY:
        return "错误：未能从 Streamlit Secrets 中加载 IMGBB_API_KEY。请检查您的 .streamlit/secrets.toml 配置文件。"

    try:
        # imgbb API 需要 base64 编码的图片字符串
        b64_image = base64.b64encode(image_bytes).decode('utf-8')

        payload = {
            "key": IMGBB_API_KEY,
            "image": b64_image,
            "name": filename
        }

        # 发送POST请求
        response = requests.post(UPLOAD_API_URL, data=payload, timeout=60)
        response.raise_for_status()

        data = response.json()

        if data.get('success'):
            return data['data']['url']
        else:
            return f"API返回错误: {data.get('error', {}).get('message', '未知错误')}"

    except requests.exceptions.RequestException as e:
        return f"网络请求失败: {e}"
    except Exception as e:
        return f"发生未知错误: {e}"


# --- Streamlit 页面配置 ---
st.set_page_config(
    page_title="图片转在线地址工具",
    page_icon="🖼️",
    layout="wide"
)

# --- 页面UI ---
st.title("🖼️ 图片转在线地址工具 (安全版)")
st.markdown("批量上传图片，轻松生成可分享的在线链接。")
st.info("⚠️ **重要提示**: 您上传的图片将被存储在图床服务上。请遵守服务条款，**请勿上传任何敏感或私人图片**。")

# 文件上传组件
uploaded_files = st.file_uploader(
    "请选择一张或多张图片...",
    type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
    accept_multiple_files=True,
    help="您可以按住`Ctrl`(Windows)或`Command`(Mac)键来选择多张图片。"
)

# 检查API Key是否已配置，如果没有配置，则显示警告并禁用按钮
api_key_configured = bool(IMGBB_API_KEY)
if not api_key_configured:
    st.error("**配置错误**：未找到 imgbb 的 API Key。请确保您已在项目的 `.streamlit/secrets.toml` 文件中正确设置了 `IMGBB_API_KEY`。")

if st.button("生成在线链接", disabled=not uploaded_files or not api_key_configured, type="primary"):
    if uploaded_files:
        st.header("处理结果")
        progress_bar = st.progress(0, text="正在准备上传...")
        total_files = len(uploaded_files)
        num_columns = 3
        cols = st.columns(num_columns)

        for i, uploaded_file in enumerate(uploaded_files):
            progress_text = f"正在上传第 {i + 1}/{total_files} 张图片: {uploaded_file.name}"
            progress_bar.progress((i + 1) / total_files, text=progress_text)

            image_bytes = uploaded_file.getvalue()
            col_index = i % num_columns
            with cols[col_index]:
                st.image(image_bytes, caption=f"预览: {uploaded_file.name}", use_column_width=True)

                with st.spinner("正在生成链接..."):
                    image_url = upload_image_to_imgbb(image_bytes, uploaded_file.name)

                if image_url and image_url.startswith("http"):
                    st.success("链接生成成功！")
                    st.code(image_url, language=None)
                else:
                    st.error(f"上传失败。错误信息: {image_url}")
                st.divider()

        progress_bar.empty()
        st.success("所有图片处理完毕！")

# --- 使用说明 ---
with st.expander("点击查看使用说明", expanded=True):
    st.markdown("""
    1.  **(首次使用)** 请确保您已经在项目文件夹下创建了 `.streamlit/secrets.toml` 文件，并正确配置了您的 `IMGBB_API_KEY`。
    2.  点击上方的“Browse files”按钮，或直接将图片文件拖拽到上传区域。
    3.  选择您想要转换的所有图片文件 (imgbb免费版有大小限制, 通常为32MB)。
    4.  选择完毕后，点击蓝色的“生成在线链接”按钮（https://coolfangtao.imgbb.com/）。
    5.  应用将自动处理每张图片，并在下方显示图片的预览和生成的在线URL。
    """)