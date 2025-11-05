import streamlit as st
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from PIL import Image
import os
# 假设您有这个文件
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


# --- 2. 核心解析器逻辑 (已修改) ---

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
    (已新增 parse_titles 函数)
    """

    def __init__(self):
        super().__init__(base_url="https://detail.1688.com/")
        self.product_link_pattern = r"detail\.1688\.com/offer/(\d+)\.html"
        self.offer_url_template = "https://detail.1688.com/offer/{offer_id}.html"

        # (无变动)
        self.re_offer_id_at = re.compile(r"offerId@(\d+)")
        self.re_offer_id_equals = re.compile(r"offerId=(\d+)")
        self.re_object_id_at = re.compile(r"object_id@(\d+)")
        self.re_render_key = re.compile(r"_(\d+)$")

    def _find_ids_by_attr_regex(self, soup, attr_name, id_regex_compiled):
        # (无变动)
        found_ids = set()
        tags = soup.find_all(attrs={attr_name: id_regex_compiled})

        for tag in tags:
            attr_value = str(tag[attr_name])
            matches = id_regex_compiled.finditer(attr_value)
            for match in matches:
                found_ids.add(match.group(1))
        return found_ids

    # --- (已新增) ---
    def parse_titles(self, html_content):
        """
        (新增) 解析商品标题。
        此方法必须使用 BeautifulSoup，因为它需要正确处理 <font> 等嵌套标签。
        """
        titles = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 查找所有 class="title-text" 的 div
            # (CSS选择器 `div.title-text` 也可以，但 `find_all` 更直观)
            title_divs = soup.find_all("div", class_="title-text")

            for div in title_divs:
                # .get_text(strip=True) 会自动处理所有子标签 (如<font>)
                # 并将文本拼接起来，然后去除首尾空白
                title = div.get_text(strip=True)
                if title:
                    titles.append(title)
        except Exception as e:
            # 即使解析标题失败，也不应阻止链接解析
            print(f"Error parsing titles: {e}")

            # 使用字典保持顺序并去重，以匹配链接解析器的去重行为
        ordered_titles = list(dict.fromkeys(titles))
        return ordered_titles

    # --- (新增结束) ---

    def parse_beauty_ranking_list(self, html_content):
        # (无变动)
        found_ids = set()

        try:
            ids_from_offer_at = set(self.re_offer_id_at.findall(html_content))
            found_ids.update(ids_from_offer_at)
            ids_from_object_at = set(self.re_object_id_at.findall(html_content))
            found_ids.update(ids_from_object_at)
        except Exception:
            pass

        if not found_ids:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                tags_with_offerid = soup.find_all(attrs={'data-offerid': True})
                for tag in tags_with_offerid:
                    offer_id = tag['data-offerid'].strip()
                    if offer_id.isdigit():
                        found_ids.add(offer_id)
                links_from_generic_parser = self.generic_parse_links(html_content, self.product_link_pattern)
                for link in links_from_generic_parser:
                    match = re.search(self.product_link_pattern, link)
                    if match:
                        found_ids.add(match.group(1))
            except Exception:
                pass

        final_links = {self.offer_url_template.format(offer_id=offer_id) for offer_id in found_ids}
        return sorted(list(final_links))

    def parse_category_list(self, html_content):
        # (无变动)
        found_ids = set()
        try:
            ids_from_equals = set(self.re_offer_id_equals.findall(html_content))
            found_ids.update(ids_from_equals)
            ids_from_offer_at = set(self.re_offer_id_at.findall(html_content))
            found_ids.update(ids_from_offer_at)
            ids_from_object_at = set(self.re_object_id_at.findall(html_content))
            found_ids.update(ids_from_object_at)
        except Exception:
            pass
        if not found_ids:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                tags_renderkey = soup.find_all(attrs={"data-renderkey": self.re_render_key})
                for tag in tags_renderkey:
                    match = self.re_render_key.search(str(tag['data-renderkey']))
                    if match:
                        found_ids.add(match.group(1))
                ids_from_aplus_obj = self._find_ids_by_attr_regex(
                    soup,
                    attr_name="data-aplus-report",
                    id_regex_compiled=self.re_object_id_at
                )
                found_ids.update(ids_from_aplus_obj)
                links_from_generic_parser = self.generic_parse_links(html_content, self.product_link_pattern)
                for link in links_from_generic_parser:
                    match = re.search(self.product_link_pattern, link)
                    if match:
                        found_ids.add(match.group(1))
            except Exception:
                pass
        final_links = {self.offer_url_template.format(offer_id=offer_id) for offer_id in found_ids}
        return sorted(list(final_links))


class ParserAmazon(BasePlatformParser):
    # (无变动)
    def __init__(self):
        super().__init__(base_url="https://www.amazon.com/")
        self.product_link_pattern = r"amazon\.com/(gp/product|dp)/\w+"

    def parse_search_results(self, html_content):
        return self.generic_parse_links(html_content, self.product_link_pattern)


class ParserTaobao(BasePlatformParser):
    # (无变动)
    def __init__(self):
        super().__init__(base_url="https://item.taobao.com/")
        self.product_link_pattern = r"item\.taobao\.com/item\.htm"

    def parse_search_results(self, html_content):
        return self.generic_parse_links(html_content, self.product_link_pattern)


# --- 3. 界面UI封装类 (已修改) ---

class AppUI:
    def __init__(self, parsers: dict, config: AppConfig):
        self.parsers = parsers
        self.config = config
        self.parser_1688 = self.parsers.get("1688")
        self.parser_amazon = self.parsers.get("Amazon")
        self.parser_taobao = self.parsers.get("Taobao")

    # --- (已修改) ---
    def _display_results(self, links_list, titles_list):
        """
        (已更新) 同时显示链接和标题
        """
        if not links_list and not titles_list:
            st.warning("在您上传的HTML文件中没有找到匹配的商品链接或标题。请检查：\n1. 文件是否正确？\n2. 解析器是否为最新？")
            return

        st.success(f"🎉 成功解析出 {len(links_list)} 个链接 和 {len(titles_list)} 个标题！")

        # 增加一个智能告警
        if len(links_list) != len(titles_list) and links_list and titles_list:
            st.warning(f"注意：链接数量 ({len(links_list)}) 与标题数量 ({len(titles_list)}) 不匹配。请核对。")

        # 使用列布局并排显示
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 采集结果 (链接)")
            if links_list:
                links_text = "\n".join(links_list)
                st.code(links_text, language="markdown")
            else:
                st.info("未找到链接。")

        with col2:
            st.markdown("### 采集结果 (标题)")
            if titles_list:
                titles_text = "\n".join(titles_list)
                st.code(titles_text, language="markdown")  # 使用code以便复制
            else:
                st.info("未找到标题。")

        st.toast("解析完成!")

    def _build_1688_tab(self):
        """
        (私有) 构建1688平台的主Tab内容。
        (已修改: button点击逻辑)
        """

        tab_rank_list, tab_category_list = st.tabs([
            "榜单文件上传",
            "类目文件上传"
        ])

        # --- 模块: 榜单文件 (已修改) ---
        with tab_rank_list:
            st.subheader("采集模块：榜单文件上传")
            st.markdown("""
            **使用方法:**
            1.  使用配套的浏览器插件，选择 **"榜单采集"** 模式。
            2.  插件将自动下载一个 `.html` 文件 (例如: `1688-ranking-....html`)。
            3.  将该文件上传到下方，即可开始解析。
            """)
            uploaded_file_rank = st.file_uploader(
                "上传由浏览器插件下载的 (ranking) HTML文件",
                type=["html", "htm"],
                key="1688_ranking_file"
            )

            if st.button("开始解析 (榜单文件)", type="primary", key="btn_1688_rank"):
                if uploaded_file_rank is not None and self.parser_1688:
                    with st.spinner(f"正在解析文件: {uploaded_file_rank.name} ..."):
                        html_content = uploaded_file_rank.getvalue().decode("utf-8")

                        # --- (已修改) ---
                        links = self.parser_1688.parse_beauty_ranking_list(html_content)
                        titles = self.parser_1688.parse_titles(html_content)
                        self._display_results(links, titles)
                        # --- (修改结束) ---
                else:
                    st.error("请先上传一个HTML文件。")

        # --- 模块: 类目列表 (已修改) ---
        with tab_category_list:
            st.subheader("采集模块：通用类目列表 (文件上传)")
            st.markdown("""
            **使用方法:**
            1.  使用配套的浏览器插件，选择 **"类目采集"** 模式。
            2.  插件将自动下载一个 `.html` 文件 (例如: `1688-category-....html`)。
            3.  将该文件上传到下方，即可开始解析。
            """)
            uploaded_file_cat = st.file_uploader(
                "上传由浏览器插件下载的 (category) HTML文件",
                type=["html", "htm"],
                key="1688_category_file"
            )

            if st.button("开始解析 (类目文件)", type="primary", key="btn_1688_cat"):
                if uploaded_file_cat is not None and self.parser_1688:
                    with st.spinner(f"正在解析文件: {uploaded_file_cat.name} ... (可能需要几十秒)"):
                        html_content = uploaded_file_cat.getvalue().decode("utf-8")

                        # --- (已修改) ---
                        links = self.parser_1688.parse_category_list(html_content)
                        titles = self.parser_1688.parse_titles(html_content)
                        self._display_results(links, titles)
                        # --- (修改结束) ---
                else:
                    st.error("请先上传一个HTML文件。")

    def _build_amazon_tab(self):
        # (无变动)
        pass

    def _build_taobao_tab(self):
        # (无变动)
        pass

    def render(self):
        # (无变动)
        create_common_sidebar(current_label="️🛍️ 妙手链接采集")
        st.title("商品链接采集器")
        st.caption("粘贴HTML元素或上传HTML文件，快速提取商品链接以便导入“妙手”等工具。")

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


# --- 4. (新) 应用主入口 (无变动) ---
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