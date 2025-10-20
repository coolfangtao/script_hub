# app.py
import streamlit as st
import requests

# 使用 vgy.me 作为免费的图片托管服务
UPLOAD_API_URL = "https://vgy.me/upload"


def upload_image_to_service(image_bytes, filename, mime_type):
    """
    将图片字节上传到图床服务并返回URL。

    Args:
        image_bytes (bytes): 图片的字节数据。
        filename (str): 原始文件名。
        mime_type (str): 文件的MIME类型 (e.g., 'image/png').

    Returns:
        str: 成功则返回图片URL，失败则返回错误信息。
    """
    try:
        # 构建请求所需的文件部分
        files = {'file': (filename, image_bytes, mime_type)}

        # 发送POST请求，设置一个超时以防网络问题
        response = requests.post(UPLOAD_API_URL, files=files, timeout=30)

        # 检查HTTP响应状态
        response.raise_for_status()

        data = response.json()

        # 检查API返回的业务逻辑错误
        if data.get('error'):
            return f"API错误: {data.get('message', '未知错误')}"
        else:
            return data.get('image')

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
st.title("🖼️ 图片转在线地址工具")
st.markdown("批量上传图片，轻松生成可分享的在线链接。")
st.info("⚠️ **重要提示**: 您上传的图片将被存储在公共图床服务上，任何人都可以通过链接访问。**请勿上传任何敏感或私人图片**。")

# 文件上传组件
uploaded_files = st.file_uploader(
    "请选择一张或多张图片...",
    type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
    accept_multiple_files=True,
    help="您可以按住`Ctrl`(Windows)或`Command`(Mac)键来选择多张图片。"
)

# “开始上传”按钮，仅当有文件被选择时才可点击
if st.button("生成在线链接", disabled=not uploaded_files, type="primary"):
    if uploaded_files:
        st.header("处理结果")

        # 创建进度条
        progress_bar = st.progress(0, text="正在准备上传...")
        total_files = len(uploaded_files)

        # 使用分栏来更好地展示结果
        num_columns = 3
        cols = st.columns(num_columns)

        for i, uploaded_file in enumerate(uploaded_files):
            # 更新进度条
            progress_text = f"正在上传第 {i + 1}/{total_files} 张图片: {uploaded_file.name}"
            progress_bar.progress((i + 1) / total_files, text=progress_text)

            # 获取图片数据
            image_bytes = uploaded_file.getvalue()

            # 在对应的列中显示内容
            col_index = i % num_columns
            with cols[col_index]:
                st.image(image_bytes, caption=f"预览: {uploaded_file.name}", use_column_width=True)

                with st.spinner("正在生成链接..."):
                    # 调用上传函数
                    image_url = upload_image_to_service(
                        image_bytes,
                        uploaded_file.name,
                        uploaded_file.type
                    )

                # 根据返回结果显示成功或失败信息
                if image_url and image_url.startswith("http"):
                    st.success("链接生成成功！")
                    # 使用st.code使其易于复制
                    st.code(image_url, language=None)
                else:
                    st.error(f"上传失败。错误信息: {image_url}")
                st.divider()  # 在同一列的图片之间添加分隔线

        # 上传完成后移除进度条
        progress_bar.empty()
        st.success("所有图片处理完毕！")
    else:
        # 理论上不会触发，因为按钮会被禁用，但作为保险
        st.warning("请先选择要上传的图片。")

# --- 使用说明 ---
with st.expander("点击查看使用说明"):
    st.markdown("""
    1.  点击上方的“Browse files”按钮，或直接将图片文件拖拽到上传区域。
    2.  选择您想要转换的所有图片文件。
    3.  选择完毕后，点击蓝色的“生成在线链接”按钮。
    4.  应用将自动处理每张图片，并在下方显示图片的预览和生成的在线URL。
    5.  您可以直接点击URL旁边的复制按钮，方便地将链接用于任何地方。
    """)