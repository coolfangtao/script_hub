import streamlit as st
import json
import re
import requests
import io
import zipfile
from urllib.parse import urlparse
import os


# --- Helper Function ---
def convert_to_hd_url(thumbnail_url):
    """
    将亚马逊缩略图URL转换为高清图URL。
    例如: .../I/71HE2s0wqhL._SY88_.jpg -> .../I/71HE2s0wqhL.jpg
    """
    # 正则表达式匹配URL末尾的 "._..._" 部分
    # \.   -> 匹配点 .
    # _    -> 匹配下划线 _
    # [A-Z0-9]+ -> 匹配一个或多个大写字母或数字 (如 SY88, AC_SL1500)
    # _?   -> 匹配一个可选的下划线 (有些链接末尾是 ._SY88.jpg 而不是 ._SY88_.jpg)
    # (?=\.) -> 正向先行断言，确保后面跟着一个点（文件扩展名的点）
    pattern = r'\._[A-Z0-9_]+_\.'

    # 简单的替换方法，更符合描述
    # 找到最后一个点（扩展名前）和它之前的点
    parts = thumbnail_url.split('.')
    if len(parts) > 2 and parts[-2].startswith('_') and parts[-2].endswith('_'):
        # 移除 `_SY88_` 这样的部分
        base_url = ".".join(parts[:-2])
        extension = parts[-1]
        return f"{base_url}.{extension}"

    # 如果上面的简单方法不奏效，使用正则表达式作为备用
    hd_url = re.sub(r'\._.*?_\.', '.', thumbnail_url)
    if hd_url == thumbnail_url:  # 如果正则没替换成功，尝试另一种模式
        hd_url = re.sub(r'\._[A-Z0-9_]+\.', '.', thumbnail_url)

    return hd_url


# --- Streamlit App ---

st.set_page_config(page_title="亚马逊评论分析器", layout="wide")

st.title("📦 亚马逊评论图片查看与下载工具")
st.write("上传从爬虫工具导出的JSON文件，即可查看评论详情并一键下载所有高清图片。")

uploaded_file = st.file_uploader("请在这里上传您的 JSON 文件", type="json")

if uploaded_file is not None:
    try:
        # 读取并解析JSON文件
        data = json.load(uploaded_file)

        # --- 1. 展示产品总览信息 ---
        st.header("📊 产品总览")
        product_info = data.get("product", {})
        title = product_info.get("title", "N/A")
        price = product_info.get("price", "N/A")
        url = product_info.get("url", "#")
        total_reviews = data.get("totalReviewsExtracted", "N/A")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**产品标题:** [{title}]({url})")
            st.markdown(f"**产品价格:** `{price}`")
            st.markdown(f"**已提取评论数:** `{total_reviews}`")
        with col2:
            # 可以在这里放产品主图，如果JSON里有的话
            st.info("这里是产品的基本信息。")

        # --- 2. 循环展示评论和图片 ---
        st.header("💬 评论详情")

        all_images_to_download = []  # 存储所有高清图信息 (url, filename)

        reviews = data.get("reviews", [])
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
                    cols = st.columns(len(image_urls))  # 为每张图片创建一个列
                    for i, thumbnail_url in enumerate(image_urls):
                        hd_url = convert_to_hd_url(thumbnail_url)

                        # 为下载功能准备数据
                        # 从URL中提取文件名，例如: 71HE2s0wqhL.jpg
                        try:
                            path = urlparse(hd_url).path
                            original_filename = os.path.basename(path)
                            # 创建一个唯一的文件名
                            filename = f"{review_id}_{i}_{original_filename}"
                            all_images_to_download.append({"url": hd_url, "filename": filename})
                        except Exception:
                            # 如果解析失败，给一个默认名字
                            filename = f"{review_id}_{i}.jpg"
                            all_images_to_download.append({"url": hd_url, "filename": filename})

                        with cols[i]:
                            st.image(hd_url, caption=f"高清图片 (点击放大)", use_column_width=True)

        # --- 3. 提供一键下载所有图片的功能 ---
        st.header("📥 下载所有图片")
        if all_images_to_download:
            st.info(f"在所有评论中总共找到了 **{len(all_images_to_download)}** 张图片。")

            if st.button("打包下载所有高清图片 (ZIP)"):
                # 创建一个内存中的二进制流
                zip_buffer = io.BytesIO()

                # 创建一个ZipFile对象
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total_images = len(all_images_to_download)

                    for i, img_data in enumerate(all_images_to_download):
                        try:
                            # 下载图片
                            response = requests.get(img_data["url"], timeout=10)
                            response.raise_for_status()  # 如果下载失败，会抛出异常

                            # 将图片数据写入zip文件
                            zip_file.writestr(img_data["filename"], response.content)

                            # 更新进度条
                            progress_percentage = (i + 1) / total_images
                            progress_bar.progress(progress_percentage)
                            status_text.text(f"正在下载并压缩图片: {i + 1}/{total_images} ({img_data['filename']})")

                        except requests.exceptions.RequestException as e:
                            st.warning(f"下载图片 {img_data['url']} 失败: {e}")

                # 准备下载按钮
                zip_buffer.seek(0)
                st.download_button(
                    label="✅ 点击这里下载ZIP文件",
                    data=zip_buffer,
                    file_name=f"{title[:30]}_review_images.zip",  # 使用产品标题做文件名
                    mime="application/zip"
                )
                status_text.success("图片已打包完成！")

        else:
            st.warning("在评论中没有找到任何图片可供下载。")

    except json.JSONDecodeError:
        st.error("上传的文件不是有效的JSON格式，请检查文件内容。")
    except Exception as e:
        st.error(f"处理文件时发生错误: {e}")