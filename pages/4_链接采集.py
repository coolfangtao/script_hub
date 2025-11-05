import streamlit as st
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from PIL import Image
import os
import time
from shared.sidebar import create_common_sidebar


# --- 1. 应用配置 (无变动) ---
class AppConfig:
    """
    存放所有应用的静态配置，例如文件路径、常量等。
    """
    ICON_1688 = "assets/e-commerce_platforms_icons/1688.png"
    ICON_AMAZON = "assets/e-commerce_platforms_icons/amazon.png"
    ICON_TAOBAO = "assets/e-commerce_platforms_icons/taobao.png"

    @staticmethod
    @st.cache_data
    def get_icon(icon_path):
        if os.path.exists(icon_path):
            try:
                return Image.open(icon_path)
            except Exception as e:
                # 隐藏日志，保持整洁
                # print(f"[Warning] 无法加载图标: {icon_path}. 错误: {e}")
                return None
        else:
            # print(f"[Info] 图标未找到: {icon_path}")
            return None


# --- 2. 核心解析器逻辑 (无变动) ---

class BasePlatformParser:
    """
    所有平台解析器的基类。
    """

    def __init__(self, base_url):
        self.base_url = base_url

    def _normalize_url(self, href):
        if not href or href.strip().startswith('#') or href.strip().lower().startswith('javascript:'):
            return None
        try:
            return urljoin(self.base_url, href.strip())
        except Exception:
            return None

    def _clean_url(self, url):
        try:
            parsed = urlparse(url)
            cleaned_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return cleaned_url
        except Exception:
            return url

    def generic_parse_links(self, html_content, link_pattern_regex):
        soup = BeautifulSoup(html_content, 'html.parser')
        found_links = set()
        for a_tag in soup.find_all('a', href=True):
            normalized_url = self._normalize_url(a_tag['href'])
            if not normalized_url:
                continue
            if re.search(link_pattern_regex, normalized_url):
                cleaned_url = self._clean_url(normalized_url)
                found_links.add(cleaned_url)
        return sorted(list(found_links))

class Parser1688(BasePlatformParser):
    """
    专门用于 1688.com 的解析器。
    """

    def __init__(self):
        super().__init__(base_url="https://detail.1688.com/")
        self.product_link_pattern = r"detail\.1688\.com/offer/(\d+)\.html"
        self.offer_url_template = "https://detail.1688.com/offer/{offer_id}.html"

        # 格式 (榜单粘贴): offerId@844634586387^
        self.re_offer_id_at = re.compile(r"offerId@(\d+)")

        # 格式 (类目文件): offerId=980010203849...
        self.re_offer_id_equals = re.compile(r"offerId=(\d+)")

        # 格式 (类目文件备用): object_id@635461774648
        self.re_object_id_at = re.compile(r"object_id@(\d+)")

        # 格式 (类目文件备用): data-renderkey="..._635461774648"
        self.re_render_key = re.compile(r"_(\d+)$")

    def _find_ids_by_attr_regex(self, soup, attr_name, id_regex_compiled):
        """
        (无变动) 查找所有具有特定属性、且属性值匹配正则的ID。
        """
        found_ids = set()
        tags = soup.find_all(attrs={attr_name: id_regex_compiled})

        for tag in tags:
            attr_value = str(tag[attr_name])
            matches = id_regex_compiled.finditer(attr_value)
            for match in matches:
                found_ids.add(match.group(1))
        return found_ids

    def parse_beauty_ranking_list(self, html_content):
        """
        榜单粘贴 Tab - 专门查找 `offerId@...` 格式
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        found_ids = set()

        # 策略1: 查找 data-aplus-report 属性中的 offerId@...
        ids_from_aplus = self._find_ids_by_attr_regex(
            soup,
            attr_name="data-aplus-report",
            id_regex_compiled=self.re_offer_id_at
        )
        found_ids.update(ids_from_aplus)

        # 策略2: 查找 data-offerid 属性
        tags_with_offerid = soup.find_all(attrs={'data-offerid': True})
        for tag in tags_with_offerid:
            offer_id = tag['data-offerid'].strip()
            if offer_id.isdigit():
                found_ids.add(offer_id)

        # 策略3: (兜底) 查找 <a> 标签 (用于标准 offer/xxx.html 链接)
        links_from_generic_parser = self.generic_parse_links(html_content, self.product_link_pattern)
        for link in links_from_generic_parser:
            match = re.search(self.product_link_pattern, link)
            if match:
                found_ids.add(match.group(1))

        final_links = {self.offer_url_template.format(offer_id=offer_id) for offer_id in found_ids}
        return sorted(list(final_links))

    def parse_category_list(self, html_content):
        """
        (已优化 V7) 类目文件 Tab -
        首选策略: (极快) 纯文本搜索 `offerId=...`
        备用策略: (较慢) 仅在首选失败时，才启动BeautifulSoup查找其他模式
        """
        found_ids = set()

        # 策略 1: (首选 - 速度极快) 直接在原始 HTML 文本中查找 'offerId=...'
        try:
            ids_from_raw_text = set(self.re_offer_id_equals.findall(html_content))
            if ids_from_raw_text:
                found_ids.update(ids_from_raw_text)
        except Exception:
            # 即使正则失败，也继续执行策略2
            pass

        # 只有当快速策略找不到任何ID时，才启动昂贵的BeautifulSoup解析
        if not found_ids:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')

                # 策略 2a: 查找 data-renderkey="..._123456"
                tags_renderkey = soup.find_all(attrs={"data-renderkey": self.re_render_key})
                for tag in tags_renderkey:
                    match = self.re_render_key.search(str(tag['data-renderkey']))
                    if match:
                        found_ids.add(match.group(1))

                # 策略 2b: 查找 'data-aplus-report' 属性中的 'object_id@...'
                ids_from_aplus_obj = self._find_ids_by_attr_regex(
                    soup,
                    attr_name="data-aplus-report",
                    id_regex_compiled=self.re_object_id_at
                )
                found_ids.update(ids_from_aplus_obj)

                # 策略 2c: (兜底) 查找 <a> 标签
                links_from_generic_parser = self.generic_parse_links(html_content, self.product_link_pattern)
                for link in links_from_generic_parser:
                    match = re.search(self.product_link_pattern, link)
                    if match:
                        found_ids.add(match.group(1))
            except Exception:
                # 即使BeautifulSoup解析失败，也继续
                pass

        final_links = {self.offer_url_template.format(offer_id=offer_id) for offer_id in found_ids}
        return sorted(list(final_links))


class ParserAmazon(BasePlatformParser):
    def __init__(self):
        super().__init__(base_url="https://www.amazon.com/")
        self.product_link_pattern = r"amazon\.com/(gp/product|dp)/\w+"

    def parse_search_results(self, html_content):
        return self.generic_parse_links(html_content, self.product_link_pattern)


class ParserTaobao(BasePlatformParser):
    def __init__(self):
        super().__init__(base_url="https://item.taobao.com/")
        self.product_link_pattern = r"item\.taobao\.com/item\.htm"

    def parse_search_results(self, html_content):
        return self.generic_parse_links(html_content, self.product_link_pattern)


# --- 3. 界面UI封装类 ---

class AppUI:
    def __init__(self, parsers: dict, config: AppConfig):
        self.parsers = parsers
        self.config = config
        self.parser_1688 = self.parsers.get("1688")
        self.parser_amazon = self.parsers.get("Amazon")
        self.parser_taobao = self.parsers.get("Taobao")

    def _display_results(self, links_list):
        if not links_list:
            st.warning("在您上传的HTML文件中没有找到匹配的商品链接。请检查：\n1. 文件是否正确？\n2. 解析器是否为最新？")
            return
        st.success(f"🎉 成功解析出 {len(links_list)} 个不重复的商品链接！")
        markdown_links = "\n".join(links_list)
        st.markdown("### 采集结果 (可一键复制)")
        st.code(markdown_links, language="markdown")
        st.toast("解析完成!")

    def _build_1688_tab(self):
        """
        (私有) 构建1688平台的主Tab内容。
        """

        # --- 创建二级Tab (模块) ---
        tab_rank_list, tab_category_list = st.tabs([
            "榜单粘贴",
            "类目文件上传"
        ])

        # --- 模块: 美容化妆榜单 (已改名) ---
        with tab_rank_list:
            st.subheader("采集模块：榜单粘贴")
            st.markdown("""
            **使用方法:**
            1.  在1688的“xx榜单”等**单页**页面上，找到包裹**所有**商品卡片的最外层HTML容器。
            2.  右键点击该容器 -> **检查 (Inspect)**。
            3.  在弹出的开发者工具中，右键点击高亮的HTML代码 -> **Copy** -> **Copy Element**。
            4.  将复制的HTML内容粘贴到下方的文本框中。
            """)

            html_input_1688_rank = st.text_area(
                "在此处粘贴 'Copy Element' 的HTML内容",
                height=300,
                key="1688_ranking_html",
                placeholder="<div class='...'> ... (包含多个商品卡片) ... </div>"
            )

            if st.button("开始解析 (榜单粘贴)", type="primary", key="btn_1688_rank"):
                if html_input_1688_rank and self.parser_1688:
                    with st.spinner("正在解析HTML..."):
                        links = self.parser_1688.parse_beauty_ranking_list(html_input_1688_rank)
                        self._display_results(links)
                else:
                    st.error("请输入HTML内容。")

        # --- 模块: 类目列表 (已更新) ---
        with tab_category_list:
            st.subheader("采集模块：通用类目列表 (文件上传)")
            st.markdown("""
            **使用方法:**
            1.  使用配套的浏览器插件采集1688类目页。
            2.  插件将自动下载一个 `.html` 文件 (例如: `1688-scrape-....html`)。
            3.  将该文件上传到下方，即可开始解析。
            """)

            uploaded_file = st.file_uploader(
                "上传由浏览器插件下载的HTML文件",
                type=["html", "htm"],
                key="1688_category_file"
            )

            if st.button("开始解析 (类目文件)", type="primary", key="btn_1688_cat"):
                if uploaded_file is not None and self.parser_1688:
                    with st.spinner(f"正在解析文件: {uploaded_file.name} ... (可能需要几十秒)"):
                        # 从上传的文件中读取HTML内容
                        # 大文件必须用 getvalue()
                        html_content = uploaded_file.getvalue().decode("utf-8")

                        # 调用更新后的、专用的解析函数
                        links = self.parser_1688.parse_category_list(html_content)
                        self._display_results(links)
                else:
                    st.error("请先上传一个HTML文件。")

    def _build_amazon_tab(self):
        # (无变动)
        pass

    def _build_taobao_tab(self):
        # (无变动)
        pass

    def render(self):
        create_common_sidebar(current_label="️🛍️ 妙手链接采集")
        st.title("商品链接采集器")
        st.caption("粘贴HTML元素或上传HTML文件，快速提取商品链接以便导入“妙手”等工具。")

        # --- 创建一级Tab (平台) ---
        tab1688, tab_amazon, tab_taobao = st.tabs([
            " [ 1688 ] ",
            " [ 亚马逊 Amazon ] (占位) ",
            " [ 淘宝 Taobao ] (占位) "
        ])
        with tab1688:
            self._build_1688_tab()
        with tab_amazon:
            self._build_amazon_tab()
        with tab_taobao:
            self._build_taobao_tab()


# --- 4. (新) 应用主入口 ---
@st.cache_resource
def get_all_parsers():
    return {
        "1688": Parser1688(),
        "Amazon": ParserAmazon(),
        "Taobao": ParserTaobao()
    }


def main():
    st.set_page_config(page_title="链接采集器", layout="wide")
    config = AppConfig()
    parsers = get_all_parsers()
    ui = AppUI(parsers, config)
    ui.render()


if __name__ == "__main__":
    main()