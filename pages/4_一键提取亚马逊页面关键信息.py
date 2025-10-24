import streamlit as st
from bs4 import BeautifulSoup
import re
import pandas as pd
import requests
import io
import zipfile
# from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar


# --- 1. 配置类 ---
# 将所有硬编码的字符串和配置项放入这里
class AppConfig:
    """存储所有应用配置，例如UI文本、文件名等。"""
    PAGE_TITLE = "亚马逊信息提取器"
    PAGE_ICON = "📦"
    APP_TITLE = "📦 亚马逊商品信息提取工具"
    INSTRUCTION_TEXT = "请在商品页面右键 → '查看网页源代码' → 全选 (Ctrl+A) → 复制 (Ctrl+C) → 粘贴到下方文本框中。"
    HTML_INPUT_PLACEHOLDER = "将HTML源代码粘贴到这里..."
    EXTRACT_BUTTON_LABEL = "提取信息"
    SPINNER_TEXT = "正在解析中，请稍候..."
    SUCCESS_MESSAGE = "提取完成！"
    EMPTY_INPUT_WARNING = "警告：文本框为空，请输入网页源代码。"

    # 结果展示部分的文本
    RESULTS_HEADER = "📊 提取结果"
    BASIC_INFO_HEADER = "📦 商品基本信息"
    REVIEWS_HEADER = "💬 用户评论"

    # 文件名和列配置
    CSV_FILENAME = "amazon_reviews.csv"
    ZIP_FILENAME = "amazon_review_images.zip"
    REVIEW_DF_COLUMNS = ['username', 'rating', 'date', 'title', 'content', 'verified', 'helpful_count', 'images']


# --- 2. 数据处理/逻辑函数 (保持不变) ---
# (为了简洁，这里省略了您提供的所有 extract_* 函数的内部实现)
# (假设 extract_all_product_info, extract_features, 等函数都存在于此)

def extract_all_product_info(html_content):
    """
    从网页源代码中提取商品的所有关键信息
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = {}
    results['features'] = extract_features(soup)
    results['title'] = extract_title(soup)
    results['price'] = extract_price(soup)
    results['rating'] = extract_rating(soup)
    results['reviews'] = extract_reviews(soup)
    results['product_details'] = extract_product_details(soup)
    return results


def extract_features(soup):
    features = []
    feature_section = soup.find('div', id='feature-bullets')
    if feature_section:
        list_items = feature_section.find_all('li', class_='a-spacing-mini')
        for item in list_items:
            span = item.find('span', class_='a-list-item')
            if span:
                features.append(span.get_text(strip=True))
    return features


def extract_title(soup):
    title_span = soup.find('span', id='productTitle')
    return title_span.get_text(strip=True) if title_span else None


def extract_price(soup):
    price_span = soup.find('span', class_='a-price')
    if price_span:
        price_text = price_span.find('span', class_='a-offscreen')
        if price_text:
            return price_text.get_text(strip=True).replace('$', '').replace('￥', '')
    price_symbol = soup.find('span', class_='a-price-symbol')
    if price_symbol:
        whole_price = soup.find('span', class_='a-price-whole')
        fraction_price = soup.find('span', class_='a-price-fraction')
        if whole_price and fraction_price:
            whole_text = whole_price.get_text(strip=True).replace('.', '').replace(',', '')
            fraction_text = fraction_price.get_text(strip=True)
            return f"{whole_text}.{fraction_text}"
    price_pattern = r'[\$￥]\d+[\.,]\d{2}'
    text_content = soup.get_text()
    price_matches = re.findall(price_pattern, text_content)
    if price_matches:
        return price_matches[0].replace('$', '').replace('￥', '').replace(',', '.')
    return None


def extract_rating(soup):
    rating_info = {}
    rating_alt = soup.find('span', class_='a-icon-alt')
    if rating_alt:
        rating_text = rating_alt.get_text(strip=True)
        rating_info['full_text'] = rating_text
        score_match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', rating_text)
        if score_match:
            rating_info['score'] = score_match.group(1)
    if 'score' not in rating_info:
        rating_span = soup.find('span', class_='a-size-base', string=re.compile(r'^\d+\.\d$'))
        if rating_span:
            rating_info['score'] = rating_span.get_text(strip=True)
    review_count = soup.find('span', id='acrCustomerReviewText')
    if review_count:
        rating_info['review_count'] = review_count.get_text(strip=True)
    return rating_info


def extract_reviews(soup):
    reviews = []
    review_containers = soup.find_all('div', id=re.compile(r'(customer_review-|review-)'))
    if not review_containers:
        review_containers = soup.find_all('div', attrs={'data-hook': 'review'})
    for container in review_containers:
        review = {}
        profile_name = container.find('span', class_='a-profile-name')
        if profile_name: review['username'] = profile_name.get_text(strip=True)
        review_title = container.find('span', class_='review-title-content')
        if review_title:
            review['title'] = review_title.get_text(strip=True)
        else:
            title_element = container.find('span', attrs={'data-hook': 'review-title'})
            if title_element:
                title_text = title_element.get_text(strip=True)
                if 'out of 5 stars' in title_text:
                    parts = re.split(r'\d+\.\d out of 5 stars', title_text)
                    title_text = parts[1].strip() if len(parts) > 1 else title_text.split('out of 5 stars')[-1].strip()
                review['title'] = title_text
        star_rating_icon = container.find('i', attrs={'data-hook': 'review-star-rating'})
        if star_rating_icon:
            star_text = star_rating_icon.find('span', class_='a-icon-alt')
            if star_text:
                match = re.search(r'(\d+\.?\d*) out of 5 stars', star_text.get_text())
                if match: review['rating'] = match.group(1)
        if 'rating' not in review:
            star_rating = container.find('i', class_=re.compile(r'a-star-\d'))
            if star_rating:
                for class_name in star_rating.get('class', []):
                    if class_name.startswith('a-star-'):
                        review['rating'] = class_name.split('-')[-1].replace('-', '.')
                        break
        review_date = container.find('span', attrs={'data-hook': 'review-date'})
        if review_date: review['date'] = review_date.get_text(strip=True)
        review_body = container.find('span', attrs={'data-hook': 'review-body'})
        if review_body: review['content'] = review_body.get_text(strip=True)
        verified_badge = container.find('span', attrs={'data-hook': 'avp-badge-linkless'})
        review['verified'] = bool(verified_badge and 'Verified Purchase' in verified_badge.get_text())
        if not review['verified']:
            verified_badge_alt = container.find('span', class_='a-size-mini', string=re.compile('Verified Purchase'))
            if verified_badge_alt: review['verified'] = True
        helpful_text = container.find('span', attrs={'data-hook': 'helpful-vote-statement'})
        if helpful_text: review['helpful_count'] = helpful_text.get_text(strip=True)
        image_urls = []
        image_tags = container.find_all('img', attrs={'data-hook': 'review-image-tile'})
        for img in image_tags:
            url = img.get('data-src') or img.get('src')
            if url:
                cleaned_url = re.sub(r'\._[A-Z09_]+_\.jpg$', '.jpg', url)
                image_urls.append(cleaned_url)
        review['images'] = image_urls
        if review: reviews.append(review)
    return reviews


def extract_product_details(soup):
    details = {}
    details_div = soup.find('div', id='detailBullets_feature_div')
    if details_div:
        list_items = details_div.find_all('li')
        for item in list_items:
            key_element = item.find('span', class_='a-text-bold')
            if key_element:
                key_text_full = key_element.get_text(strip=True)
                key_clean = key_text_full.replace(':', '').strip()
                full_item_text = item.get_text(separator=' ', strip=True)
                value_text = full_item_text.replace(key_text_full, '', 1).lstrip(' :').strip()
                value_text = re.sub(r'\s+', ' ', value_text)
                if value_text and key_clean:
                    if key_clean == 'Best Sellers Rank': value_text = value_text.split('(See Top 100')[0].strip()
                    details[key_clean] = value_text
    else:
        details_table = soup.find('table', id='productDetails_detailBullets_sections1')
        if details_table:
            rows = details_table.find_all('tr')
            for row in rows:
                key_element = row.find('th')
                value_element = row.find('td')
                if key_element and value_element:
                    key_clean = key_element.get_text(strip=True)
                    if key_clean == 'Customer Reviews': continue
                    value_text = re.sub(r'\s+', ' ', value_element.get_text(separator=' ', strip=True)).strip()
                    if key_clean == 'Best Sellers Rank': value_text = value_text.split('(See Top 100')[0].strip()
                    details[key_clean] = value_text
    return details


# --- 辅助函数 (缓存结果) ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')


@st.cache_data
def download_and_zip_images(_image_urls_tuple):  # _ is a convention for cached func args
    image_urls = list(_image_urls_tuple)  # Convert back to list
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        progress_bar = st.progress(0, text="开始下载...")
        total_images = len(image_urls)
        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    filename = url.split('/')[-1].split('?')[0]
                    if not filename or '.' not in filename[-5:]: filename = f"image_{i + 1}.jpg"
                    zip_file.writestr(filename, response.content)
                else:
                    st.warning(f"无法下载图片 (状态码 {response.status_code}): {url}", icon="⚠️")
            except requests.RequestException as e:
                st.error(f"下载图片时出错: {url} (错误: {e})", icon="🔥")
            progress_bar.progress((i + 1) / total_images, text=f"正在下载第 {i + 1}/{total_images} 张图片...")
        progress_bar.progress(1.0, text="压缩完成！")
    zip_buffer.seek(0)
    return zip_buffer


# --- 3. UI类 ---
# 管理所有Streamlit的UI组件
class AppUI:
    def __init__(self, config: AppConfig):
        self.config = config
        st.set_page_config(page_title=self.config.PAGE_TITLE, page_icon=self.config.PAGE_ICON)

    def render_header(self):
        st.title(self.config.APP_TITLE)
        st.info(self.config.INSTRUCTION_TEXT)

    def render_input_area(self):
        html_content = st.text_area("在此处粘贴网页源代码:", height=300, key="html_input",
                                    placeholder=self.config.HTML_INPUT_PLACEHOLDER)
        extract_button = st.button(self.config.EXTRACT_BUTTON_LABEL, key="extract_button", type="primary",
                                   use_container_width=True)
        return html_content, extract_button

    def render_results(self, results):
        st.header(self.config.RESULTS_HEADER)
        st.divider()

        self._display_main_metrics(results)
        self._display_details_and_features(results)
        self._display_reviews(results)

    def _display_main_metrics(self, results):
        """美化输出：使用 st.metric 展示核心指标"""
        col1, col2, col3 = st.columns(3)

        price = results.get('price', 'N/A')
        rating_score = results.get('rating', {}).get('score', 'N/A')
        review_count = results.get('rating', {}).get('review_count', 'N/A')

        with col1:
            st.metric(label="💲 商品价格", value=price)
        with col2:
            st.metric(label="⭐ 综合评分", value=f"{rating_score} / 5")
        with col3:
            st.metric(label="👥 评价总数", value=review_count)

        st.markdown(f"##### **商品标题:** {results.get('title', '未找到')}")
        st.divider()

    def _display_details_and_features(self, results):
        """美化输出：使用 st.expander 隐藏次要信息"""
        with st.expander("📌 商品特性 (Features)"):
            features = results.get('features')
            if features:
                for feature in features:
                    st.markdown(f"- {feature}")
            else:
                st.write("未找到商品特性。")

        with st.expander("📋 商品详情 (Product Details)"):
            details = results.get('product_details')
            if details:
                st.table(pd.DataFrame(list(details.items()), columns=['属性', '值']))
            else:
                st.write("未找到商品详情。")
        st.divider()

    def _display_reviews(self, results):
        """美化输出：使用 st.tabs 组织评论信息"""
        st.subheader(self.config.REVIEWS_HEADER)
        reviews_list = results.get('reviews', [])

        if not reviews_list:
            st.info("未找到用户评论。")
            return

        st.write(f"共找到 {len(reviews_list)} 条评论")

        tab1, tab2, tab3 = st.tabs(["📊 表格视图", "🖼️ 图片下载", "📝 纯文本视图"])

        with tab1:
            self._display_reviews_dataframe(reviews_list)

        with tab2:
            self._display_image_downloader(reviews_list)

        with tab3:
            self._display_reviews_simple_text(reviews_list)

    def _display_reviews_dataframe(self, reviews_list):
        try:
            df = pd.DataFrame(reviews_list)
            existing_cols = [col for col in self.config.REVIEW_DF_COLUMNS if col in df.columns]
            df_display = df[existing_cols]
            st.dataframe(df_display, use_container_width=True)

            csv_data = convert_df_to_csv(df_display)
            st.download_button(
                label="下载评论 (CSV 文件)",
                data=csv_data,
                file_name=self.config.CSV_FILENAME,
                mime="text/csv",
                key="download_csv"
            )
        except Exception as e:
            st.error(f"处理评论表格时出错: {e}")
            st.json(reviews_list)

    def _display_image_downloader(self, reviews_list):
        all_image_urls = sorted(list(set(
            url for review in reviews_list if review.get('images') for url in review['images']
        )))

        if not all_image_urls:
            st.info("评论中未找到任何图片。")
            return

        st.write(f"在所有评论中总共找到 {len(all_image_urls)} 张独特的图片。")

        if st.button("打包下载所有图片 (ZIP)", key="prep_download"):
            # 使用元组 tuple 是因为 @st.cache_data 的参数必须是可哈希的
            st.session_state.zip_buffer = download_and_zip_images(tuple(all_image_urls))

        if 'zip_buffer' in st.session_state and st.session_state.zip_buffer:
            st.download_button(
                label="✅ 点击下载 ZIP 文件",
                data=st.session_state.zip_buffer,
                file_name=self.config.ZIP_FILENAME,
                mime="application/zip",
                key="download_zip_final"
            )

    def _display_reviews_simple_text(self, reviews_list):
        lines = []
        for i, review in enumerate(reviews_list, 1):
            lines.append(f"【评论 {i}】")
            lines.append(f"  - 用户名: {review.get('username', 'N/A')}")
            lines.append(f"  - 评分: {review.get('rating', '?')}/5")
            lines.append(f"  - 日期: {review.get('date', 'N/A')}")
            lines.append(f"  - 标题: {review.get('title', '无标题')}")
            lines.append(f"  - 已验证购买: {'是' if review.get('verified', False) else '否'}")
            if review.get('helpful_count'):
                lines.append(f"  - 有帮助: {review.get('helpful_count')}")
            lines.append(f"  - 内容: {review.get('content', '无内容')}")
            if review.get('images'):
                lines.append("  - 图片链接:")
                for img_url in review.get('images'): lines.append(f"    - {img_url}")
            lines.append("-" * 30)

        simple_reviews_text = "\n".join(lines)
        st.text_area("评论文本 (可复制):", value=simple_reviews_text, height=400, key="reviews_text_area")


# --- 4. 主程序逻辑 ---
def main():
    # 初始化配置和UI
    # track_script_usage("🔍 关键词统计")
    create_common_sidebar()
    config = AppConfig()
    ui = AppUI(config)

    # 初始化 session_state
    if 'extraction_results' not in st.session_state:
        st.session_state.extraction_results = None
    if 'zip_buffer' not in st.session_state:
        st.session_state.zip_buffer = None

    # 渲染头部和输入区
    ui.render_header()
    html_content, extract_button_clicked = ui.render_input_area()

    # 处理按钮点击事件
    if extract_button_clicked:
        if html_content:
            # 重置状态
            st.session_state.extraction_results = None
            st.session_state.zip_buffer = None

            with st.spinner(config.SPINNER_TEXT):
                try:
                    results = extract_all_product_info(html_content)
                    st.session_state.extraction_results = results  # 缓存结果
                    st.success(config.SUCCESS_MESSAGE)
                except Exception as e:
                    st.error(f"解析时发生错误: {e}")
                    st.exception(e)
        else:
            st.warning(config.EMPTY_INPUT_WARNING)

    # 如果 session_state 中有结果，则渲染它们
    if st.session_state.extraction_results:
        ui.render_results(st.session_state.extraction_results)


if __name__ == "__main__":
    main()