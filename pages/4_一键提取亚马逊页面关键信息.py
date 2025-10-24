import streamlit as st
from bs4 import BeautifulSoup
import re


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
