import streamlit as st
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from shared.sidebar import create_common_sidebar
create_common_sidebar()


def extract_names_from_html(html_content: str) -> list[str]:
    """
    从完整的HTML源代码中解析并提取所有群成员的网名。

    它专门查找 <span class="name">...</span> 标签，
    并提取该标签下的第一个直接文本节点。
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 根据您提供的示例，网名在 <span class="name">...</span> 标签中
        name_spans = soup.find_all('span', class_='name')

        names = []
        for span in name_spans:
            # 目标网名是span标签的第一个子节点，且必须是文本节点(NavigableString)
            # 这样可以排除掉 "@校内员工" 这样的嵌套span
            if span.contents and isinstance(span.contents[0], NavigableString):
                name = str(span.contents[0]).strip()

                # 确保提取到的不是空字符串
                if name:
                    names.append(name)

        return names

    except Exception as e:
        st.error(f"HTML解析出错: {e}")
        return []


class NameExtractorApp:
    """
    用于提取网名的Streamlit应用UI类
    """

    def __init__(self):
        # 页面配置
        st.set_page_config(
            page_title="掌上大学群成员提取器",
            page_icon="🎓",
            layout="wide"
        )

    def _render_app_tab(self):
        """渲染核心功能页"""
        st.subheader("1. 粘贴HTML源代码")
        html_input = st.text_area(
            "请将从“掌上大学”复制的完整网页源代码粘贴到此处：",
            height=350,
            placeholder="在这里粘贴 (Ctrl+V)..."
        )

        if st.button("🚀 提取姓名", type="primary"):
            if html_input:
                with st.spinner("正在解析HTML并提取姓名..."):
                    names_list = extract_names_from_html(html_input)

                if names_list:
                    st.success(f"成功提取 {len(names_list)} 个姓名！")
                    st.subheader("2. 提取结果（可一键复制）")

                    # 将姓名列表转换为每行一个的字符串
                    output_text = "\n".join(names_list)

                    st.text_area(
                        "提取的姓名列表：",
                        value=output_text,
                        height=400,
                        key="output_names"
                    )
                else:
                    st.warning("未找到任何姓名。请检查：\n1. 是否粘贴了**完整**的“网页源代码”？\n2. 是否在复制前已加载所有群成员？\n3. 网页版结构是否已变更？")
            else:
                st.warning("请输入HTML源代码。")

    def _get_tutorial_content(self) -> str:
        """返回教程页的Markdown内容"""
        return """
        ## 📚 如何使用本工具

        本工具用于从“掌上大学”网页版的群聊成员列表中快速提取所有成员的网名。

        ---

        ### 步骤一：加载所有群成员

        1.  在电脑浏览器（推荐Chrome或Edge）上登录“掌上大学”网页版。
        2.  进入您想提取成员的群聊。
        3.  点击查看群成员列表（通常在聊天窗口的右侧）。
        4.  **[！] 非常重要：** 鼠标在成员列表上，**滚动鼠标滚轮**，一直滚动到底部，直到所有群成员都已加载显示在页面上。

        > **提示：** 如果群成员很多，您可能需要滚动几次，直到滚动条到达最下方。

        ---

        ### 步骤二：复制网页源代码

        1.  在加载完所有成员的页面**空白处**点击鼠标右键。
        2.  在弹出的菜单中选择 **“查看网页源代码”** (View Page Source)。 (快捷键: `Ctrl+U` 或 `Cmd+Option+U`)

            > **[!] 注意：** *不要*选择“检查”或“检查元素”(Inspect)。你需要的是**整个页面**的源代码，它会一个新标签页中打开。

        3.  在新打开的源代码标签页中，全选 (快捷键: `Ctrl+A` 或 `Cmd+A`)。
        4.  复制 (快捷键: `Ctrl+C` 或 `Cmd+C`) 所有的代码。

        ---

        ### 步骤三：粘贴并提取

        1.  回到本工具的 **"[ 功能页 ]"** 标签。
        2.  将您刚刚复制的所有代码粘贴到“1. 粘贴HTML源代码”下方的文本框中。
        3.  点击 **"🚀 提取姓名"** 按钮。
        4.  提取的姓名列表会出现在下方的“2. 提取结果”文本框中，您可以直接全选并复制走。

        ---

        ### ⚠️ 常见问题与注意事项

        * **提取不全？**
            大概率是您在“步骤一”中没有将群成员列表滚动到底部，导致部分成员没有被加载到HTML中。请重复步骤一，确保加载完全。
        * **提取为零？**
            请确认您在“步骤二”中选择的是“查看网页源代码”，而不是“检查”或“复制元素”。本工具需要完整的HTML文档才能正常工作。
        * **工具失效？**
            “掌上大学”网页版如果未来更新了页面结构（例如将 `class="name"` 改为其他名字），本工具可能会失效。
        """

    def _render_tutorial_tab(self):
        """渲染教程页"""
        st.markdown(self._get_tutorial_content())

    def run(self):
        """启动应用的主函数"""
        st.title("🎓 掌上大学群成员提取器")

        # 创建两个Tab
        tab_app, tab_tutorial = st.tabs(["[ 🚀 功能页 ]", "[ 📚 教程页 ]"])

        with tab_app:
            self._render_app_tab()

        with tab_tutorial:
            self._render_tutorial_tab()


# --- 运行应用 ---
if __name__ == "__main__":
    app = NameExtractorApp()
    app.run()