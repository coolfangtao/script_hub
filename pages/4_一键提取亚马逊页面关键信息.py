import streamlit as st
from bs4 import BeautifulSoup
import re
import pandas as pd  # 导入 pandas 用于表格
import requests  # (新增) 用于下载图片
import io  # (新增) 用于内存中创建zip
import zipfile  # (新增) 用于创建zip


# --- 您提供的原始解析函数 ---
# (为了保持代码整洁，这里省略了函数的内部实现，但它们与您提供的一致)

def extract_all_product_info(html_content):
    """
    从网页源代码中提取商品的所有关键信息
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = {}

    # 1. 提取商品特性列表
    features = extract_features(soup)
    results['features'] = features

    # 2. 提取商品标题
    title = extract_title(soup)
    results['title'] = title

    # 3. 提取价格信息
    price = extract_price(soup)
    results['price'] = price

    # 4. 提取评分信息
    rating_info = extract_rating(soup)
    results['rating'] = rating_info

    # 5. 提取所有用户评论 (新增)
    reviews = extract_reviews(soup)
    results['reviews'] = reviews

    # 6. 提取商品详细信息 (新增)
    product_details = extract_product_details(soup)
    results['product_details'] = product_details

    return results


def extract_features(soup):
    """
    提取商品特性列表
    """
    features = []
    feature_section = soup.find('div', id='feature-bullets')

    if feature_section:
        list_items = feature_section.find_all('li', class_='a-spacing-mini')
        for item in list_items:
            span = item.find('span', class_='a-list-item')
            if span:
                text = span.get_text(strip=True)
                features.append(text)

    return features


def extract_title(soup):
    """
    提取商品标题
    """
    title_span = soup.find('span', id='productTitle')
    if title_span:
        return title_span.get_text(strip=True)
    return None


def extract_price(soup):
    """
    提取价格信息
    """
    # 方法1：通过特定class定位
    # 尝试查找 'a-price' 结构
    price_span = soup.find('span', class_='a-price')
    if price_span:
        price_text = price_span.find('span', class_='a-offscreen')
        if price_text:
            return price_text.get_text(strip=True).replace('$', '').replace('￥', '')  # 移除货币符号

    # 方法2：组合 'a-price-symbol', 'a-price-whole', 'a-price-fraction'
    price_symbol = soup.find('span', class_='a-price-symbol')
    if price_symbol:
        whole_price = soup.find('span', class_='a-price-whole')
        fraction_price = soup.find('span', class_='a-price-fraction')

        if whole_price and fraction_price:
            whole_text = whole_price.get_text(strip=True).replace('.', '').replace(',', '')
            fraction_text = fraction_price.get_text(strip=True)
            return f"{whole_text}.{fraction_text}"

    # 方法3：备选方案，搜索价格模式 (作为最后的尝试)
    price_pattern = r'[\$￥]\d+[\.,]\d{2}'  # 匹配 $19.99 或 ￥19,99
    text_content = soup.get_text()
    price_matches = re.findall(price_pattern, text_content)
    if price_matches:
        # 清理找到的第一个匹配项
        return price_matches[0].replace('$', '').replace('￥', '').replace(',', '.')

    return None


def extract_rating(soup):
    """
    提取评分信息
    """
    rating_info = {}

    # 提取评分描述（例如 "4.3 out of 5 stars"）
    rating_alt = soup.find('span', class_='a-icon-alt')
    if rating_alt:
        rating_text = rating_alt.get_text(strip=True)
        rating_info['full_text'] = rating_text
        # 尝试从中提取分数
        score_match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', rating_text)
        if score_match:
            rating_info['score'] = score_match.group(1)

    # 如果上述方法失败，尝试查找评分数字（例如 "4.3"）
    if 'score' not in rating_info:
        rating_span = soup.find('span', class_='a-size-base', string=re.compile(r'^\d+\.\d$'))
        if rating_span:
            rating_info['score'] = rating_span.get_text(strip=True)

    # 提取评价数量
    review_count = soup.find('span', id='acrCustomerReviewText')
    if review_count:
        rating_info['review_count'] = review_count.get_text(strip=True)

    return rating_info


# --- (新增) 提取评论函数 ---

def extract_reviews(soup):
    """
    提取所有用户评论信息 (已集成)
    """
    reviews = []

    # 使用模糊匹配找到所有评论容器
    # (已增强：添加备用选择器)
    review_containers = soup.find_all('div', id=re.compile(r'(customer_review-|review-)'))

    if not review_containers:
        review_containers = soup.find_all('div', attrs={'data-hook': 'review'})

    for container in review_containers:
        review = {}

        # 1. 提取用户名
        profile_name = container.find('span', class_='a-profile-name')
        if profile_name:
            review['username'] = profile_name.get_text(strip=True)

        # 2. 提取评论标题/概要
        review_title = container.find('span', class_='review-title-content')
        if review_title:
            review['title'] = review_title.get_text(strip=True)
        else:
            # 备选方法：通过data-hook属性
            title_element = container.find('span', attrs={'data-hook': 'review-title'})
            if title_element:
                # 获取标题文本，跳过星级部分
                title_text = title_element.get_text(strip=True)
                # 移除星级文本，只保留标题
                # (这个逻辑可能不总是准确，但保留原样)
                if 'out of 5 stars' in title_text:
                    # 尝试更准确地分割
                    parts = re.split(r'\d+\.\d out of 5 stars', title_text)
                    if len(parts) > 1:
                        title_text = parts[1].strip()
                    else:
                        # 备用方案
                        title_text = title_text.split('out of 5 stars')[-1].strip()
                review['title'] = title_text

        # 3. 提取星级评分
        star_rating_icon = container.find('i', attrs={'data-hook': 'review-star-rating'})
        if star_rating_icon:
            # 尝试从 'a-icon-alt' 中获取
            star_text = star_rating_icon.find('span', class_='a-icon-alt')
            if star_text:
                match = re.search(r'(\d+\.?\d*) out of 5 stars', star_text.get_text())
                if match:
                    review['rating'] = match.group(1)

        # 备选方案 (来自您的代码)
        if 'rating' not in review:
            star_rating = container.find('i', class_=re.compile(r'a-star-\d'))
            if star_rating:
                # 从class名中提取星级数字
                class_names = star_rating.get('class', [])
                for class_name in class_names:
                    if class_name.startswith('a-star-'):
                        # 提取数字，如 "a-star-4" -> "4"
                        review['rating'] = class_name.split('-')[-1].replace('-', '.')  # 兼容 a-star-4-5
                        break

        # 4. 提取评论日期
        review_date = container.find('span', attrs={'data-hook': 'review-date'})
        if review_date:
            review['date'] = review_date.get_text(strip=True)

        # 5. 提取评论正文
        review_body = container.find('span', attrs={'data-hook': 'review-body'})
        if review_body:
            # 获取评论文本，包括可能被折叠的内容
            review_text = review_body.get_text(strip=True)
            review['content'] = review_text

        # 6. 提取是否有Verified Purchase
        verified_badge = container.find('span', attrs={'data-hook': 'avp-badge-linkless'})
        if verified_badge and 'Verified Purchase' in verified_badge.get_text():
            review['verified'] = True
        else:
            # 备选
            verified_badge_alt = container.find('span', class_='a-size-mini', string=re.compile('Verified Purchase'))
            if verified_badge_alt:
                review['verified'] = True
            else:
                review['verified'] = False

        # 7. 提取有帮助的数量
        helpful_text = container.find('span', attrs={'data-hook': 'helpful-vote-statement'})
        if helpful_text:
            helpful_count = helpful_text.get_text(strip=True)
            review['helpful_count'] = helpful_count

        # 8. 提取图片链接 (新增)
        image_urls = []
        image_tags = container.find_all('img', attrs={'data-hook': 'review-image-tile'})
        for img in image_tags:
            # 优先使用 data-src (懒加载)
            url = img.get('data-src') or img.get('src')
            if url:
                # 尝试移除缩略图后缀 (例如 ._SY88.jpg) 来获取高清图
                # \._[A-Z0-9_]+_\.jpg$ 匹配像 ._SY88.jpg 或 ._AC_UF100_..._.jpg 这样的后缀
                cleaned_url = re.sub(r'\._[A-Z0-9_]+_\.jpg$', '.jpg', url)
                image_urls.append(cleaned_url)

        review['images'] = image_urls

        if review:  # 只添加有内容的评论
            reviews.append(review)

    return reviews


# --- (新增) 提取商品详细信息函数 ---
def extract_product_details(soup):
    """
    提取 "Product details" 部分的信息 (例如 ASIN, 制造商等)
    (已更新，可处理 div 和 table 两种结构)
    """
    details = {}
    # 查找 "Product Details" 容器 (div > ul > li 结构)
    details_div = soup.find('div', id='detailBullets_feature_div')

    if details_div:
        list_items = details_div.find_all('li')
        for item in list_items:
            key_element = item.find('span', class_='a-text-bold')

            if key_element:
                # 1. 获取键 (Key)
                key_text_full = key_element.get_text(strip=True)  # e.g., "ASIN:"
                key_clean = key_text_full.replace(':', '').strip()  # e.g., "ASIN"

                # 2. 获取值 (Value)
                # 使用 separator=' ' 来正确处理 "Best Sellers Rank" 中的嵌套列表
                full_item_text = item.get_text(separator=' ', strip=True)
                # 替换掉键的全名，然后去除前导的冒号和空格
                value_text = full_item_text.replace(key_text_full, '', 1).lstrip(' :').strip()

                # 清理多余的空格
                value_text = re.sub(r'\s+', ' ', value_text)

                if value_text and key_clean:
                    # (新增) 特别清理 "Best Sellers Rank"
                    if key_clean == 'Best Sellers Rank':
                        value_text = value_text.split('(See Top 100')[0].strip()
                    details[key_clean] = value_text
    else:
        # 备选方案: 查找 (table > tr > th/td 结构)
        details_table = soup.find('table', id='productDetails_detailBullets_sections1')
        if details_table:
            rows = details_table.find_all('tr')
            for row in rows:
                key_element = row.find('th')
                value_element = row.find('td')
                if key_element and value_element:
                    key_clean = key_element.get_text(strip=True)

                    # (新增) 跳过 "Customer Reviews"，因为它由 extract_rating 单独处理
                    if key_clean == 'Customer Reviews':
                        continue

                    value_text_raw = value_element.get_text(separator=' ', strip=True)
                    value_text = re.sub(r'\s+', ' ', value_text_raw).strip()

                    # (新增) 特别清理 "Best Sellers Rank"
                    if key_clean == 'Best Sellers Rank':
                        value_text = value_text.split('(See Top 100')[0].strip()

                    details[key_clean] = value_text

    return details


# --- (新增) Streamlit 缓存函数 ---
@st.cache_data
def convert_df_to_csv(df):
    """
    将 DataFrame 转换为 CSV 格式 (用于下载)
    使用 utf-8-sig 编码确保 Excel 正确打开
    """
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')


# --- (新增) 下载并压缩图片的函数 ---
@st.cache_data  # 缓存下载结果
def download_and_zip_images(image_urls):
    """
    Downloads images from a list of URLs and returns them in a zipped BytesIO buffer.
    """
    zip_buffer = io.BytesIO()
    # 使用 with 语句确保 zip 文件被正确关闭
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        progress_bar = st.progress(0, text="开始下载...")
        total_images = len(image_urls)

        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url, timeout=10)  # 10 秒超时
                if response.status_code == 200:
                    # 从URL获取一个基本的文件名
                    filename = url.split('/')[-1].split('?')[0]
                    # 确保文件名有意义，如果太短或没有扩展名
                    if not filename or not '.' in filename[-5:]:
                        filename = f"image_{i + 1}.jpg"

                    zip_file.writestr(filename, response.content)
                else:
                    st.warning(f"无法下载图片 (状态码 {response.status_code}): {url}", icon="⚠️")
            except requests.RequestException as e:
                st.error(f"下载图片时出错: {url} (错误: {e})", icon="🔥")

            # 更新进度条
            progress_bar.progress((i + 1) / total_images, text=f"正在下载第 {i + 1}/{total_images} 张图片...")

        progress_bar.progress(1.0, text="压缩完成！")

    zip_buffer.seek(0)
    return zip_buffer


# --- (新增) 格式化基本信息 ---
def format_other_info_for_display(results):
    """
    将基本信息格式化为单个字符串以便复制
    """
    lines = []

    # 标题
    if results['title']:
        lines.append(f"商品标题: {results['title']}")
    else:
        lines.append("商品标题: 未找到")

    lines.append("-" * 40)

    # 价格
    if results['price']:
        lines.append(f"商品价格: {results['price']}")
    else:
        lines.append("商品价格: 未找到")

    lines.append("-" * 40)

    # 评分
    if results['rating']:
        rating = results['rating']
        lines.append("评分信息:")
        if 'score' in rating:
            lines.append(f"  - 评分: {rating['score']}/5")
        if 'full_text' in rating:
            lines.append(f"  - 详情: {rating['full_text']}")
        if 'review_count' in rating:
            lines.append(f"  - 评价数量: {rating['review_count']}")
    else:
        lines.append("评分信息: 未找到")

    lines.append("-" * 40)

    # 特性
    if results['features']:
        lines.append("商品特性:")
        for i, feature in enumerate(results['features'], 1):
            lines.append(f"  {i}. {feature}")
    else:
        lines.append("商品特性: 未找到")

    lines.append("-" * 40)

    # 商品详情 (新增)
    if results.get('product_details'):
        lines.append("商品详情:")
        details = results['product_details']
        if details:
            for key, value in details.items():
                lines.append(f"  - {key}: {value}")
        else:
            lines.append("  未找到商品详情。")
    else:
        lines.append("商品详情: 未找到")

    return "\n".join(lines)


# --- (新增) 格式化评论为简洁文本 ---
def format_reviews_simple_text(reviews):
    """
    将评论列表格式化为简洁的文本字符串
    """
    lines = []
    if not reviews:
        return "未找到评论。"

    for i, review in enumerate(reviews, 1):
        lines.append(f"【评论 {i}】")
        lines.append(f"用户名: {review.get('username', 'N/A')}")
        lines.append(f"评分: {review.get('rating', '?')}/5")
        lines.append(f"日期: {review.get('date', 'N/A')}")
        lines.append(f"标题: {review.get('title', '无标题')}")
        verified_text = "是" if review.get('verified', False) else "否"
        lines.append(f"已验证购买: {verified_text}")
        if review.get('helpful_count'):
            lines.append(f"有帮助: {review.get('helpful_count')}")
        lines.append(f"内容: {review.get('content', '无内容')}")

        # (新增) 添加图片链接
        if review.get('images'):
            lines.append("图片链接:")
            for img_url in review.get('images'):
                lines.append(f"  - {img_url}")

        lines.append("\n" + "-" * 30 + "\n")

    return "\n".join(lines)


# --- 用于Streamlit的新函数 ---

def display_streamlit_results(results):
    """
    在Streamlit页面上格式化显示提取结果 (已修改)
    """
    st.header("提取结果")
    st.markdown("---")

    # --- 1. 显示基本信息 (文本框) ---
    st.subheader("📦 商品基本信息")
    other_info_text = format_other_info_for_display(results)
    # 使用 disabled=True 使其只读，但用户仍可复制
    st.text_area("基本信息 (可复制):", value=other_info_text, height=350, disabled=True, key="other_info_area")  # 增加了高度

    st.markdown("\n\n---\n")

    # --- 2. 显示评论 (表格) ---
    st.subheader("💬 用户评论")
    if results.get('reviews'):
        reviews_list = results['reviews']
        st.write(f"共找到 {len(reviews_list)} 条评论")

        try:
            # --- 2a. 创建 DataFrame ---
            df = pd.DataFrame(reviews_list)

            # 调整列顺序以便查看 (新增 'images')
            cols_order = ['username', 'rating', 'date', 'title', 'content', 'verified', 'helpful_count', 'images']
            # 过滤掉数据中不存在的列 (以防万一)
            existing_cols = [col for col in cols_order if col in df.columns]
            df_display = df[existing_cols]

            st.dataframe(df_display, use_container_width=True)

            # --- 2b. 下载按钮 (CSV) ---
            csv_data = convert_df_to_csv(df_display)
            st.download_button(
                label="下载评论 (CSV 文件)",
                data=csv_data,
                file_name="amazon_reviews.csv",
                mime="text/csv",
                key="download_csv"
            )

            # --- 2c. (新增) 图片下载 ---
            # 提取所有唯一的图片URL
            all_image_urls = sorted(list(set(
                url for review in reviews_list if review.get('images') for url in review['images']
            )))

            if all_image_urls:
                st.markdown("---")
                st.subheader(f"📷 评论图片下载 (共 {len(all_image_urls)} 张)")

                # 使用 session state 来存储 zip 文件的状态
                if 'zip_buffer' not in st.session_state:
                    st.session_state.zip_buffer = None

                if st.button("准备图片下载 (ZIP)", key="prep_download"):
                    # 调用函数并存储结果
                    # (使用 tuple 是因为 list 不可哈希，无法被 @st.cache_data 缓存)
                    st.session_state.zip_buffer = download_and_zip_images(tuple(all_image_urls))

                # 如果 zip 文件已经生成，显示最终的下载按钮
                if st.session_state.zip_buffer:
                    st.download_button(
                        label="✅ 点击下载 ZIP 文件",
                        data=st.session_state.zip_buffer,
                        file_name="amazon_review_images.zip",
                        mime="application/zip",
                        key="download_zip_final"
                    )

            # --- 2d. 简洁文本格式 ---
            st.markdown("---")
            st.subheader("简洁文本版评论 (可复制)")
            simple_reviews_text = format_reviews_simple_text(reviews_list)
            st.text_area("评论文本:", value=simple_reviews_text, height=400, disabled=True, key="reviews_text_area")

        except Exception as e:
            st.error(f"处理评论表格时出错: {e}")
            st.write("无法生成表格，显示原始评论数据：")
            st.json(reviews_list)  # 作为后备，直接打印JSON

    else:
        st.info("未找到用户评论。")


# (此函数已被移除，功能被 format_other_info_for_display 和 format_reviews_simple_text 替代)
# def format_results_for_copy(results):
#     ...

# --- Streamlit 应用程序界面 ---

# 设置页面标题
st.set_page_config(page_title="亚马逊信息提取器", page_icon="📦")

st.title("📦 亚马逊商品信息提取工具")

st.info("请在商品页面右键 → '查看网页源代码' → 全选 (Ctrl+A) → 复制 (Ctrl+C) → 粘贴到下方文本框中。")

# 用于粘贴HTML的文本区域
html_content = st.text_area("在此处粘贴网页源代码:", height=300, key="html_input", placeholder="将HTML源代码粘贴到这里...")

# 提取按钮
if st.button("提取信息", key="extract_button", type="primary"):
    if html_content:
        # (新增) 清理上一次的下载状态
        if 'zip_buffer' in st.session_state:
            st.session_state.zip_buffer = None

        with st.spinner("正在解析中，请稍候..."):
            try:
                # 提取所有信息
                results = extract_all_product_info(html_content)

                # 在页面上显示结果 (使用修改后的函数)
                display_streamlit_results(results)

                # (旧的复制部分已移除)

                st.success("提取完成！")

            except Exception as e:
                st.error(f"解析时发生错误: {e}")
                st.exception(e)
    else:
        st.warning("警告：文本框为空，请输入网页源代码。")

