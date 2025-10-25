import streamlit as st
import json
import re
import requests
import io
import zipfile
from urllib.parse import urlparse
import os
from shared.sidebar import create_common_sidebar
create_common_sidebar()

# --- Helper Function ---
def convert_to_hd_url(thumbnail_url):
    """
    将亚马逊缩略图URL转换为高清图URL。
    例如: .../I/71HE2s0wqhL._SY88_.jpg -> .../I/71HE2s0wqhL.jpg
    """
    # 查找并移除URL中类似 '._SY88_' 的部分
    # 这种模式通常是最后一个点（扩展名）和倒数第二个点之间
    parts = thumbnail_url.split('.')
    if len(parts) > 2 and parts[-2].startswith('_') and parts[-2].endswith('_'):
        base_url = ".".join(parts[:-2])
        extension = parts[-1]
        return f"{base_url}.{extension}"

    # 作为备用方案，使用正则表达式处理其他可能的变体
    hd_url = re.sub(r'\._[A-Z0-9_]+_\.', '.', thumbnail_url)
    if hd_url == thumbnail_url:
        hd_url = re.sub(r'\._[A-Z0-9_]+\.', '.', thumbnail_url)

    return hd_url


# --- Streamlit App UI ---

st.set_page_config(page_title="亚马逊评论分析器", layout="wide")
st.title("📦 亚马逊评论图片查看与下载工具")
st.write("一个帮你从JSON文件中提取、展示并批量下载亚马逊评论图片的Streamlit小工具。")

# 初始化 Session State
if 'data' not in st.session_state:
    st.session_state.data = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None

# 创建两个标签页
tab1, tab2 = st.tabs(["📊 评论分析器", "📖 使用教程"])

# --- Tab 1: 评论分析器 ---
with tab1:
    st.header("1. 上传评论JSON文件")
    uploaded_file = st.file_uploader(
        "请将通过浏览器插件导出的 JSON 文件拖拽到此处",
        type="json",
        key="file_uploader"
    )

    # 如果有新文件上传，则处理并存入 session state
    if uploaded_file is not None:
        # 检查是否是同一个文件，避免重复加载
        if uploaded_file.name != st.session_state.uploaded_file_name:
            try:
                data = json.load(uploaded_file)
                st.session_state.data = data
                st.session_state.uploaded_file_name = uploaded_file.name
                st.success(f"文件 '{uploaded_file.name}' 上传并解析成功！")
            except json.JSONDecodeError:
                st.error("上传的文件不是有效的JSON格式，请检查文件内容。")
                st.session_state.data = None
            except Exception as e:
                st.error(f"处理文件时发生错误: {e}")
                st.session_state.data = None

    # 如果 session state 中有数据，则显示内容
    if st.session_state.data is not None:

        # 提供一个清除按钮
        if st.button("清除当前数据并上传新文件"):
            st.session_state.data = None
            st.session_state.uploaded_file_name = None
            # 使用 st.experimental_rerun() or st.rerun() 来刷新页面状态
            st.rerun()

        st.header("2. 产品总览")
        product_info = st.session_state.data.get("product", {})
        title = product_info.get("title", "N/A")
        price = product_info.get("price", "N/A")
        url = product_info.get("url", "#")
        total_reviews = st.session_state.data.get("totalReviewsExtracted", "N/A")

        st.markdown(f"**产品标题:** [{title}]({url})")
        st.markdown(f"**产品价格:** `{price}`")
        st.markdown(f"**已提取评论数:** `{total_reviews}`")

        st.header("3. 评论详情与图片")
        all_images_to_download = []

        reviews = st.session_state.data.get("reviews", [])
        if not reviews:
            st.warning("JSON文件中没有找到'reviews'列表。")
        else:
            for review in reviews:
                st.markdown("---")
                reviewer_name = review.get('reviewerName', '匿名用户')
                rating = review.get('rating', '无评分')
                review_text = review.get('text', '无评论内容')
                review_id = review.get('reviewId', 'no_id')

                st.markdown(f"#### 评论者: **{reviewer_name}** | 评分: **{rating}**")
                st.markdown(f"> {review_text}")

                image_urls = review.get('imageUrls', [])
                if image_urls:
                    cols = st.columns(len(image_urls))
                    for i, thumbnail_url in enumerate(image_urls):
                        hd_url = convert_to_hd_url(thumbnail_url)
                        try:
                            path = urlparse(hd_url).path
                            original_filename = os.path.basename(path)
                            filename = f"{review_id}_{i}_{original_filename}"
                            all_images_to_download.append({"url": hd_url, "filename": filename})
                        except Exception:
                            filename = f"{review_id}_{i}.jpg"
                            all_images_to_download.append({"url": hd_url, "filename": filename})

                        with cols[i]:
                            st.image(hd_url, caption=f"高清图片", use_column_width=True)

        st.header("4. 下载所有图片")
        if all_images_to_download:
            st.info(f"在所有评论中总共找到了 **{len(all_images_to_download)}** 张图片。")

            if st.button("打包下载所有高清图片 (ZIP)"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total_images = len(all_images_to_download)

                    for i, img_data in enumerate(all_images_to_download):
                        try:
                            response = requests.get(img_data["url"], timeout=10)
                            response.raise_for_status()
                            zip_file.writestr(img_data["filename"], response.content)
                            progress_percentage = (i + 1) / total_images
                            progress_bar.progress(progress_percentage)
                            status_text.text(f"正在下载并压缩图片: {i + 1}/{total_images}...")
                        except requests.exceptions.RequestException as e:
                            st.warning(f"下载图片 {img_data['url']} 失败: {e}")

                zip_buffer.seek(0)
                st.download_button(
                    label="✅ 图片打包完成！点击这里下载",
                    data=zip_buffer,
                    file_name=f"{title[:30]}_review_images.zip",
                    mime="application/zip"
                )
                status_text.success("打包成功！")

        else:
            st.warning("在评论中没有找到任何图片可供下载。")

# --- Tab 2: 使用教程 ---
with tab2:
    st.header("🚀 浏览器插件使用指南")
    st.info("本工具需要配合特定的浏览器插件使用，以下是如何获取评论数据JSON文件的步骤。")
    st.markdown("""
        ---
        ### **第一步：安装并固定插件**

        1.  打开你的浏览器（以Chrome为例），进入 **扩展程序** 管理页面。
            * 可以直接在地址栏输入 `chrome://extensions`并回车
            * 或者通过 `菜单 -> 更多工具 -> 扩展程序` 进入
        3.  在页面右上角，打开 **“开发者模式”** 的开关。
        4.  点击左上角的 **“加载已解压的扩展程序”** 按钮。
        5.  在弹出的窗口中，选择你本地的 `AmazonScraper` 文件夹（或者直接拖进去），然后点击“确定”。
        6.  插件安装成功后，默认会隐藏在扩展程序列表中。
        7.  点击浏览器右上角的 **扩展程序图标**（通常是一个拼图形状 🧩），在列表中找到“AmazonScraper”插件，然后点击旁边的 **图钉** 📌 图标，将其固定到工具栏，方便快速访问。
    """)
    # 新增的图片，指导用户如何固定插件
    st.image("assets/Amazonscraper0.png", caption="图0：点击拼图图标，再点击图钉，将插件固定到工具栏")

    st.markdown("""
        ---
        ### **第二步：抓取商品基本信息**

        1.  用浏览器打开任意一个亚马逊**商品主页**（必须是具体的商品详情页，而不是列表页）。
        2.  点击浏览器工具栏上刚刚固定的 **插件图标**，打开插件面板。
        3.  在“选择导出格式”中，确保选择的是 **JSON (完整数据结构)**。
        4.  点击橙色的 **“开始抓取”** 按钮。

        _插件会自动抓取当前页面的商品标题、价格等基本信息。_
    """)
    st.image("assets/Amazonscraper1.png", caption="图1：在商品主页，选择JSON格式后点击“开始抓取”")

    st.markdown("""
        ---
        ### **第三步：抓取评论信息**

        1.  在插件面板上，按钮会变为 **“再次点击启动抓取”**。
        2.  评论页面加载完毕后，**再次点击插件上的“再次点击启动抓取”按钮**。
        3.  插件会开始自动翻页并抓取所有评论。完成后，浏览器会自动下载一个JSON文件。

    """)
    st.image("assets/Amazonscraper2.png", caption="图2：点击“查看所有评论”后，再点击插件中的按钮开始抓取评论")

    st.markdown("""
        ---
        ### **第四步：在本页面分析并下载图片**

        1.  切换回本 **“评论分析器”** 标签页。
        2.  将刚刚下载的JSON文件，拖拽到文件上传框中。
        3.  程序会自动解析文件，展示商品信息、所有评论以及评论中的高清图片。
        4.  滚动到页面底部，点击 **“打包下载所有高清图片 (ZIP)”** 按钮，即可一键保存所有图片。
    """)
    st.image("assets/Amazonscraper3.png", caption="图3：点击下载箭头，选择生成的json文件直接拖进来")