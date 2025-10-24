import streamlit as st
from bs4 import BeautifulSoup
import re


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

        if review:  # 只添加有内容的评论
            reviews.append(review)

    return reviews


# --- 用于Streamlit的新函数 ---

def display_streamlit_results(results):
    """
    在Streamlit页面上格式化显示提取结果
    """
    st.header("提取结果")
    st.markdown("---")

    # 显示标题
    if results['title']:
        st.subheader("📦 商品标题")
        st.write(results['title'])
    else:
        st.warning("未找到商品标题。")

    # 显示价格
    if results['price']:
        st.subheader("💰 价格")
        # 价格可能包含货币符号，也可能不包含
        st.write(f"{results['price']}")
    else:
        st.warning("未找到价格。")

    # 显示评分
    if results['rating']:
        st.subheader("⭐ 评分")
        rating = results['rating']
        if 'score' in rating:
            st.write(f"**评分:** {rating['score']}/5")
        if 'full_text' in rating:
            st.write(f"**详情:** {rating['full_text']}")
        if 'review_count' in rating:
            st.write(f"**评价数量:** {rating['review_count']}")
    else:
        st.warning("未找到评分信息。")

    # 显示特性列表
    if results['features']:
        st.subheader("📋 商品特性")
        md_list = ""
        for i, feature in enumerate(results['features'], 1):
            md_list += f" {i}. {feature}\n"
        st.markdown(md_list)
    else:
        st.warning("未找到商品特性。")

    # 5. 显示评论 (新增)
    if results.get('reviews'):
        st.subheader(f"💬 用户评论 (找到 {len(results['reviews'])} 条)")
        for i, review in enumerate(results['reviews']):
            expander_title = f"**{review.get('title', '无标题')}** - (评分: {review.get('rating', '?')}/5) - by {review.get('username', '匿名')}"
            with st.expander(expander_title):
                cols = st.columns(3)
                with cols[0]:
                    st.text(f"👤 用户: {review.get('username', 'N/A')}")
                with cols[1]:
                    st.text(f"📅 日期: {review.get('date', 'N/A')}")
                with cols[2]:
                    verified_text = "是" if review.get('verified', False) else "否"
                    st.text(f"✅ 已验证购买: {verified_text}")

                if review.get('helpful_count'):
                    st.text(f"👍 有帮助: {review.get('helpful_count')}")

                st.markdown("---")
                st.markdown(review.get('content', '无内容'))

    else:
        st.info("未找到用户评论。")


def format_results_for_copy(results):
    """
    将结果格式化为单个字符串以便复制
    """
    lines = []
    lines.append("=" * 50)
    lines.append("商品信息提取结果")
    lines.append("=" * 50)
    lines.append("\n")

    if results['title']:
        lines.append(f"📦 商品标题: {results['title']}")
        lines.append("-" * 50)
        lines.append("\n")

    if results['price']:
        lines.append(f"💰 价格: {results['price']}")
        lines.append("-" * 50)
        lines.append("\n")

    if results['rating']:
        rating = results['rating']
        lines.append("⭐ 评分:")
        if 'score' in rating:
            lines.append(f"   - 评分: {rating['score']}/5")
        if 'full_text' in rating:
            lines.append(f"   - 详情: {rating['full_text']}")
        if 'review_count' in rating:
            lines.append(f"   - 评价数量: {rating['review_count']}")
        lines.append("-" * 50)
        lines.append("\n")

    if results['features']:
        lines.append("📋 商品特性:")
        for i, feature in enumerate(results['features'], 1):
            lines.append(f"  {i}. {feature}")
        lines.append("-" * 50)

    # 5. 添加评论到复制文本 (新增)
    if results.get('reviews'):
        lines.append("\n")
        lines.append("=" * 50)
        lines.append(f"💬 用户评论 (找到 {len(results['reviews'])} 条)")
        lines.append("=" * 50)
        lines.append("\n")

        for i, review in enumerate(results['reviews'], 1):
            lines.append(f"--- 评论 {i} ---")
            lines.append(f"👤 用户名: {review.get('username', 'N/A')}")
            lines.append(f"⭐ 评分: {review.get('rating', '?')}/5")
            lines.append(f"📅 日期: {review.get('date', 'N/A')}")
            lines.append(f"✍️ 标题: {review.get('title', '无标题')}")

            verified_text = "是" if review.get('verified', False) else "否"
            lines.append(f"✅ 已验证购买: {verified_text}")

            if review.get('helpful_count'):
                lines.append(f"👍 有帮助: {review.get('helpful_count')}")

            lines.append("---")
            lines.append(f"内容:\n{review.get('content', '无内容')}")
            lines.append("\n")

    return "\n".join(lines)


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
        with st.spinner("正在解析中，请稍候..."):
            try:
                # 提取所有信息
                results = extract_all_product_info(html_content)

                # 在页面上显示结果
                display_streamlit_results(results)

                st.markdown("\n\n---\n")
                st.header("一键复制结果")

                # 格式化用于复制的文本
                copy_text = format_results_for_copy(results)

                # 使用 st.code() 来显示文本，它自带一个复制按钮
                st.code(copy_text, language="text")

                st.success("提取完成！")

            except Exception as e:
                st.error(f"解析时发生错误: {e}")
                st.exception(e)
    else:
        st.warning("警告：文本框为空，请输入网页源代码。")

