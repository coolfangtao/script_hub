import streamlit as st
import pandas as pd
import json
import uuid
from typing import Dict, List, Any, Optional
from shared.sidebar import create_common_sidebar
create_common_sidebar()


# --- 1. 配置管理类 (ConfigManager) ---
# 这个类的核心职责是：
# - 管理应用的所有状态数据（页面、元素、流程等）。
# - 从 Streamlit 的 session_state 中加载数据。
# - 将更改后的数据保存回 session_state。
# - 提供统一的接口来读取、添加、修改和删除数据。
# 这样做的好处是，将数据逻辑与界面逻辑（UIManager）分离开，让代码更清晰、更易于维护。
class ConfigManager:
    """负责所有数据的状态管理、加载、保存和修改。"""

    # 定义一套默认的模拟数据，作为类的一个静态属性。
    # 当用户第一次运行应用，session_state 中没有任何数据时，会使用这套数据作为初始状态。
    # 这样用户一打开就能看到一个完整可用的例子，方便理解应用的功能。
    _MOCK_DATA = {
        "actions": ["点击", "采集文本", "采集图像", "输入文本"],
        "pages": [
            {"id": "page_1", "name": "商城主页"},
            {"id": "page_2", "name": "榜单页面"},
            {"id": "page_3", "name": "商品主页"},
            {"id": "page_4", "name": "搜索结果页"},
            {"id": "page_5", "name": "顾客评论页"}
        ],
        "elements": [
            {"id": "elem_2", "page_id": "page_1", "name": "榜单Tab", "selector": ".ranking-tab",
             "description": "主页上进入榜单页面的Tab"},
            {"id": "elem_3", "page_id": "page_1", "name": "搜索框", "selector": "input#search-bar",
             "description": "主页的搜索输入框"},
            {"id": "elem_4", "page_id": "page_1", "name": "搜索提交按钮", "selector": "button.search-submit",
             "description": "点击后执行搜索"},
            {"id": "elem_5", "page_id": "page_2", "name": "榜单商品链接", "selector": ".ranking-item > a",
             "description": "榜单页的单个商品链接"},
            {"id": "elem_6", "page_id": "page_4", "name": "搜索结果商品链接", "selector": ".s-result-item .s-link",
             "description": "搜索结果列表中的商品链接"},
            {"id": "elem_7", "page_id": "page_4", "name": "搜索结果下一页", "selector": ".pagination .next-page",
             "description": "搜索结果列表的翻页按钮"},
            {"id": "elem_8", "page_id": "page_3", "name": "商品标题", "selector": "h1#productTitle",
             "description": "商品详情页的主标题"},
            {"id": "elem_9", "page_id": "page_3", "name": "商品价格", "selector": ".price .a-offscreen",
             "description": "商品详情页的价格"},
            {"id": "elem_11", "page_id": "page_3", "name": "品牌名称", "selector": "a#bylineInfo",
             "description": "商品的品牌链接或名称"},
            {"id": "elem_13", "page_id": "page_3", "name": "查看全部评论按钮",
             "selector": "a[data-hook='see-all-reviews-link-foot']", "description": "跳转到顾客评论页的链接"},
            {"id": "elem_15", "page_id": "page_5", "name": "评论者名称", "selector": ".a-profile-name",
             "description": "评论发布者的用户名"},
            {"id": "elem_16", "page_id": "page_5", "name": "评论内容", "selector": "span[data-hook='review-body']",
             "description": "评论的正文部分"},
            {"id": "elem_17", "page_id": "page_5", "name": "评论页下一页", "selector": "li.a-last > a",
             "description": "评论列表的翻页按钮"}
        ],
        "flows": [
            {
                "id": "flow_1", "name": "按榜单采集",
                "steps": [
                    {"element_id": "elem_2", "action": "点击", "description": "进入新品榜或热销榜页面", "indent_level": 0},
                    {"element_id": "elem_5", "action": "点击", "description": "这是一个循环步骤，需要遍历页面上所有商品", "indent_level": 0},
                    {"element_id": "elem_8", "action": "采集文本", "description": "", "indent_level": 1},
                    {"element_id": "elem_9", "action": "采集文本", "description": "注意价格可能存在多种格式", "indent_level": 1},
                    {"element_id": "elem_11", "action": "采集文本", "description": "", "indent_level": 1}
                ]
            },
            {
                "id": "flow_2", "name": "采集指定商品所有评论（带循环）",
                "steps": [
                    {"element_id": "elem_13", "action": "点击", "description": "从商品主页跳转到评论页", "indent_level": 0},
                    {"element_id": "elem_17", "action": "点击", "description": "循环点击，直到'下一页'按钮不可点击为止", "indent_level": 0},
                    {"element_id": "elem_15", "action": "采集文本", "description": "在每次点击下一页前，采集本页所有评论者",
                     "indent_level": 1},
                    {"element_id": "elem_16", "action": "采集文本", "description": "在每次点击下一页前，采集本页所有评论内容",
                     "indent_level": 1}
                ]
            }
        ]
    }

    def __init__(self, state):
        """
        构造函数，在创建 ConfigManager 实例时调用。
        :param state: 传入 Streamlit 的 session_state 对象，用于持久化存储数据。
        """
        self._state = state
        # 检查 session_state 中是否已经有 'data' 这个键。
        if 'data' not in self._state:
            # 如果没有，说明是第一次运行，就把预设的模拟数据存入 session_state。
            self._state.data = self._MOCK_DATA
        # 每次初始化时，都调用数据迁移函数，确保数据结构始终是最新的，以兼容旧版本。
        self._migrate_data()

    def _migrate_data(self):
        """
        确保数据结构是最新的，用于向后兼容。
        例如，如果新版本代码给 'step' 字典增加了一个 'indent_level' 键，
        这个函数会检查旧的数据，如果发现某个 'step' 没有这个键，就给它补上一个默认值。
        这样可以防止因为数据结构不一致导致的程序错误。
        """
        data = self._state.data
        # 检查 'actions' 列表是否存在，不存在则创建
        if 'actions' not in data:
            data['actions'] = ["点击", "采集文本", "采集图像", "输入文本"]
        # 检查 'flows'，并遍历其中的所有 'steps'
        if 'flows' in data:
            for flow in data['flows']:
                if 'steps' in flow:
                    for step in flow['steps']:
                        # 检查 'indent_level' 是否存在，不存在则添加默认值 0
                        if 'indent_level' not in step:
                            step['indent_level'] = 0
        # 将修复后的数据存回 state
        self._state.data = data

    def get_data(self) -> Dict[str, List[Dict]]:
        """获取所有配置数据。"""
        return self._state.data

    def import_data(self, new_data: Dict):
        """
        从一个字典对象（通常来自上传的JSON文件）中加载数据。
        :param new_data: 包含页面、元素和流程等信息的字典。
        :return: 如果数据格式正确且导入成功，返回 True，否则返回 False。
        """
        # 简单校验一下导入的数据是否包含了必要的顶级键
        if 'pages' in new_data and 'elements' in new_data and 'flows' in new_data:
            self._state.data = new_data
            self._migrate_data()  # 导入数据后，也需要运行一次迁移，确保其结构兼容
            return True
        return False

    # --- Getters (获取器) ---
    # 下面这一系列函数提供了安全的、只读的方式来访问配置数据的各个部分。
    def get_actions(self) -> List[str]:
        """获取所有可用的动作列表。"""
        return self._state.data.get('actions', [])

    def get_pages(self) -> List[Dict]:
        """获取所有页面的列表。"""
        return self._state.data.get('pages', [])

    def get_elements(self) -> List[Dict]:
        """获取所有元素的列表。"""
        return self._state.data.get('elements', [])

    def get_flows(self) -> List[Dict]:
        """获取所有流程的列表。"""
        return self._state.data.get('flows', [])

    def get_item_by_id(self, item_type: str, item_id: str) -> Optional[Dict]:
        """
        根据类型和ID查找并返回单个项目（如页面、元素或流程）。
        :param item_type: 项目类型，如 'pages', 'elements', 'flows'。
        :param item_id: 项目的唯一ID。
        :return: 如果找到，返回该项目的字典；否则返回 None。
        """
        if item_type in self._state.data:
            for item in self._state.data[item_type]:
                if item['id'] == item_id:
                    return item
        return None

    # --- Mutators (修改器) ---
    # 下面这一系列函数用于修改数据，如添加或删除。
    def add_action(self, action_name: str):
        """添加一个新的动作类型。"""
        # 确保动作名称不为空，并且不存在于当前列表中
        if action_name and action_name not in self.get_actions():
            self._state.data['actions'].append(action_name)

    def remove_action(self, action_name: str):
        """删除一个已有的动作类型。"""
        if action_name in self.get_actions():
            self._state.data['actions'].remove(action_name)

    def add_page(self, page_name: str):
        """添加一个新页面。"""
        if page_name:
            # 使用 uuid 生成一个随机的、唯一的ID
            new_page = {"id": f"page_{uuid.uuid4().hex[:6]}", "name": page_name}
            self._state.data['pages'].append(new_page)

    def add_element(self, name: str, page_id: str, selector: str, description: str):
        """添加一个新元素。"""
        new_element = {
            "id": f"elem_{uuid.uuid4().hex[:6]}",
            "page_id": page_id,
            "name": name,
            "selector": selector,
            "description": description
        }
        self._state.data['elements'].append(new_element)

    def add_flow(self, flow_name: str):
        """添加一个新流程。"""
        # 确保流程名不为空，并且不存在同名流程
        if flow_name and not any(f['name'] == flow_name for f in self.get_flows()):
            new_flow = {"id": f"flow_{uuid.uuid4().hex[:6]}", "name": flow_name, "steps": []}
            self._state.data['flows'].append(new_flow)

    def add_step_to_flow(self, flow_id: str, element_id: str, action: str, description: str):
        """向指定的流程中添加一个新步骤。"""
        flow = self.get_item_by_id('flows', flow_id)
        if flow:
            new_step = {'element_id': element_id, 'action': action, 'description': description, 'indent_level': 0}
            # 健壮性检查：如果 'steps' 列表不存在，则创建一个
            if 'steps' not in flow:
                flow['steps'] = []
            flow['steps'].append(new_step)

    def update_flow_steps(self, flow_id: str, new_steps: List[Dict]):
        """
        用一个新的步骤列表完全替换掉某个流程的所有步骤。
        这在对步骤进行排序、删除等操作后非常有用，可以直接保存整个修改后的列表。
        """
        flow = self.get_item_by_id('flows', flow_id)
        if flow:
            flow['steps'] = new_steps


# --- 2. 界面渲染类 (UIManager) ---
# 这个类专门负责所有与 Streamlit 相关的界面渲染和布局。
# 它接收一个 ConfigManager 实例，通过该实例来获取数据和修改数据。
# 这样做的好处是，所有的 st.write, st.button, st.selectbox 等界面代码都集中在这里，
# 而不与数据处理逻辑混在一起。
class UIManager:
    """处理所有 Streamlit 界面的渲染和交互。"""

    def __init__(self, config_manager: ConfigManager):
        """
        构造函数。
        :param config_manager: 传入一个 ConfigManager 实例，用于数据交互。
        """
        self.config = config_manager
        # 初始化 session_state 中的 'generated_prompt'，用于存储生成的提示词
        if 'generated_prompt' not in st.session_state:
            st.session_state.generated_prompt = ""

    @staticmethod
    def renumber_steps(steps: List[Dict]) -> List[Dict]:
        """
        一个静态方法，根据步骤的缩进级别动态生成层级编号（如 1, 1.1, 1.2, 2）。
        :param steps: 步骤列表。
        :return: 带有 'display_order' 键的步骤列表。
        """
        counters = [0]  # 计数器列表，索引代表缩进层级
        for step in steps:
            indent = step.get('indent_level', 0)

            # 如果当前缩进层级比计数器列表还深，说明进入了新的子层级
            if indent >= len(counters):
                counters.append(1)  # 添加一个新的计数器，从1开始
            else:
                # 否则，回到当前层级，并将更深层级的计数器全部丢弃
                counters = counters[:indent + 1]
                counters[indent] += 1  # 当前层级计数器加1

            # 将计数器列表转换为 "1.1.2" 这样的字符串格式
            step['display_order'] = '.'.join(map(str, counters))
        return steps

    def render_overview_tab(self):
        """渲染“总览”选项卡的内容。"""
        st.subheader("🔎 流程与元素总览")
        flows = self.config.get_flows()
        if not flows:
            st.warning("当前没有配置任何流程。");
            return

        # 创建一个多选框，让用户可以筛选想要查看的流程
        flow_names = [flow['name'] for flow in flows]
        selected_flows = st.multiselect("筛选流程:", options=flow_names, default=flow_names)

        overview_data = []
        # 遍历所有被选中的流程
        for flow in [f for f in flows if f['name'] in selected_flows]:
            if not flow.get('steps'): continue  # 如果流程没有步骤，则跳过
            renumbered_steps = self.renumber_steps(flow['steps'])
            # 遍历流程中的每一步，提取信息并组合成一个扁平化的列表
            for step in renumbered_steps:
                element = self.config.get_item_by_id('elements', step['element_id'])
                if element:
                    page = self.config.get_item_by_id('pages', element['page_id'])
                    overview_data.append({
                        "流程名称": flow['name'], "步骤": step['display_order'],
                        "页面": page['name'] if page else "N/A", "元素名称": element['name'],
                        "动作": step['action'], "选择器 (Selector)": element['selector']
                    })
        if overview_data:
            # 使用 Pandas DataFrame 来展示数据，美观且功能强大
            st.dataframe(pd.DataFrame(overview_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.info("您可以在下方导入、导出您的所有配置数据。")
        col1, col2 = st.columns(2)
        with col1:
            # 将当前所有配置数据转换为格式化的 JSON 字符串
            json_data = json.dumps(self.config.get_data(), indent=2, ensure_ascii=False)
            # 创建一个下载按钮
            st.download_button(label="📥 导出配置到 JSON", data=json_data, file_name="scraper_config.json",
                               mime="application/json")
        with col2:
            # 创建一个文件上传组件
            if uploaded_file := st.file_uploader("📤 从 JSON 文件导入配置", type="json"):
                try:
                    new_data = json.load(uploaded_file)
                    # 调用 ConfigManager 的导入方法
                    if self.config.import_data(new_data):
                        st.success("配置已成功导入并兼容！");
                        st.rerun()  # 导入成功后，刷新整个页面以显示新数据
                    else:
                        st.error("JSON文件格式不正确。")
                except json.JSONDecodeError:
                    st.error("上传的文件不是有效的JSON格式。")

    def render_page_manager_tab(self):
        """渲染“页面管理”选项卡的内容。"""
        st.subheader("📄 页面管理")
        pages = self.config.get_pages()
        # 以表格形式展示所有页面
        st.dataframe(pd.DataFrame(pages), use_container_width=True, hide_index=True, key="pages_df")
        # 使用 expander 创建一个可折叠的表单区域
        with st.expander("➕ 添加新页面"):
            with st.form("new_page_form", clear_on_submit=True):
                new_page_name = st.text_input("页面名称")
                if st.form_submit_button("添加") and new_page_name:
                    self.config.add_page(new_page_name)
                    st.success(f"成功添加页面: {new_page_name}");
                    st.rerun()  # 添加成功后刷新页面

    def render_element_manager_tab(self):
        """渲染“元素管理”选项卡的内容。"""
        st.subheader("🖱️ 元素管理")
        elements = self.config.get_elements()
        elements_data = []
        # 准备要在 DataFrame 中显示的数据，这里将 page_id 转换成了更易读的 page_name
        for elem in elements:
            page = self.config.get_item_by_id('pages', elem.get('page_id', ''))
            elements_data.append({
                "元素名称": elem['name'],
                "所属页面": page['name'] if page else "N/A",
                "选择器 (Selector)": elem['selector'],
                "说明": elem['description']
            })
        st.dataframe(pd.DataFrame(elements_data), use_container_width=True, hide_index=True, key="elements_df")

        with st.expander("➕ 添加新元素"):
            with st.form("new_element_form", clear_on_submit=True):
                pages = self.config.get_pages()
                if not pages:
                    st.warning("请先至少创建一个页面。");
                    return

                # 创建一个字典，方便从页面名称映射到页面ID
                pages_dict = {page['name']: page['id'] for page in pages}
                element_name = st.text_input("元素名称")
                page_name = st.selectbox("所属页面", options=pages_dict.keys())
                selector = st.text_input("选择器 (Selector)")
                description = st.text_area("元素说明")

                # 确保关键信息都已填写
                if st.form_submit_button("添加") and all([element_name, page_name, selector]):
                    self.config.add_element(element_name, pages_dict[page_name], selector, description)
                    st.success(f"成功添加元素: {element_name}");
                    st.rerun()

    def render_action_manager_tab(self):
        """渲染“动作管理”选项卡的内容。"""
        st.subheader("🔧 动作管理")
        st.info("在这里管理流程中可用的动作类型。")
        actions = self.config.get_actions()
        st.write(f"当前可用动作: `{', '.join(actions)}`")

        col1, col2 = st.columns(2)
        with col1:
            # 添加新动作的表单
            with st.form("new_action_form", clear_on_submit=True):
                new_action = st.text_input("添加新动作")
                if st.form_submit_button("➕ 添加"):
                    if new_action and new_action not in actions:
                        self.config.add_action(new_action)
                        st.success(f"成功添加动作: {new_action}");
                        st.rerun()
                    else:
                        st.warning("动作不能为空或已存在。")
        with col2:
            # 删除动作的下拉选择框和按钮
            action_to_remove = st.selectbox("选择要删除的动作", options=[""] + actions)
            if st.button("❌ 删除选中动作", disabled=(not action_to_remove)):
                self.config.remove_action(action_to_remove)
                st.success(f"成功删除动作: {action_to_remove}");
                st.rerun()

    def render_flow_manager_tab(self):
        """渲染“流程管理与编排”选项卡的内容。"""
        st.subheader("⚙️ 流程管理与编排")
        col1, col2 = st.columns([1, 2])  # 左右两栏布局，左边窄，右边宽
        flows = self.config.get_flows()
        flow_names = [flow['name'] for flow in flows]

        with col1:  # 左侧栏：创建和选择流程
            st.write("**流程列表**")
            with st.form("new_flow_form", clear_on_submit=True):
                new_flow_name = st.text_input("新流程名称")
                if st.form_submit_button("创建新流程"):
                    if new_flow_name and new_flow_name not in flow_names:
                        self.config.add_flow(new_flow_name)
                        st.success(f"成功创建流程: {new_flow_name}");
                        st.rerun()
                    else:
                        st.warning("流程名称不能为空或已存在。")

            # 使用 radio 按钮来选择当前要编辑的流程
            selected_flow_name = st.radio("选择要编辑的流程:", flow_names, key="flow_selector")

        with col2:  # 右侧栏：编排选中流程的步骤
            if not selected_flow_name:
                st.warning("请先在左侧创建或选择一个流程。");
                return

            # 根据选择的流程名称，找到对应的流程对象
            selected_flow = next((f for f in flows if f['name'] == selected_flow_name), None)
            st.write(f"#### 正在编排流程: **{selected_flow_name}**")

            # 如果流程存在且包含步骤，则渲染步骤列表
            if selected_flow and selected_flow.get('steps'):
                steps = selected_flow['steps']
                renumbered_steps = self.renumber_steps(steps)

                # ---------- v2.0: 优化后的分层渲染逻辑 ----------
                # 定义一个递归函数，用于按层级渲染步骤。
                # 当一个步骤有子步骤时，它会创建一个带边框的容器并将子步骤渲染在其中。
                def _render_steps_hierarchically(start_index: int, current_indent: int) -> int:
                    """
                    递归地渲染步骤，为子步骤创建可视化的容器。
                    :param start_index: 要开始处理的步骤在列表中的索引。
                    :param current_indent: 当前渲染的缩进层级。
                    :return: 下一个应该由父级调用处理的步骤的索引。
                    """
                    i = start_index
                    while i < len(renumbered_steps):
                        step = renumbered_steps[i]
                        step_indent = step.get('indent_level', 0)

                        if step_indent < current_indent:
                            # 如果当前步骤的缩进小于我们正在渲染的层级，
                            # 说明这个子流程块已经结束，返回到上一层。
                            return i

                        if step_indent > current_indent:
                            # 这是一个异常情况（例如，缩进从0直接跳到2）。
                            # 为防止无限循环，我们跳过这个错误的步骤。
                            i += 1
                            continue

                        # --- 渲染当前层级的步骤 ---
                        element = self.config.get_item_by_id('elements', step['element_id'])
                        page = self.config.get_item_by_id('pages', element['page_id']) if element else None

                        # 显示步骤的核心信息
                        st.markdown(
                            f"<div><b>{step['display_order']}.</b> 在 <b>{page['name'] if page else 'N/A'}</b> 页面 <b>{step['action']}</b> <b>{element['name'] if element else 'N/A'}</b></div>",
                            unsafe_allow_html=True)
                        if step.get('description'):
                            st.markdown(
                                f"<div><blockquote>📝: <i>{step['description']}</i></blockquote></div>",
                                unsafe_allow_html=True)

                        # 创建一行按钮用于操作步骤
                        b_cols = st.columns((1, 1, 1, 1, 1, 5))
                        if b_cols[0].button("⬆️", key=f"up_{i}_{selected_flow['id']}", help="上移"):
                            if i > 0:
                                steps[i], steps[i - 1] = steps[i - 1], steps[i]
                                self.config.update_flow_steps(selected_flow['id'], steps)
                                st.rerun()
                        if b_cols[1].button("⬇️", key=f"down_{i}_{selected_flow['id']}", help="下移"):
                            if i < len(steps) - 1:
                                steps[i], steps[i + 1] = steps[i + 1], steps[i]
                                self.config.update_flow_steps(selected_flow['id'], steps)
                                st.rerun()
                        if b_cols[2].button("➡️", key=f"indent_{i}_{selected_flow['id']}", help="增加缩进"):
                            current_level = step.get('indent_level', 0)
                            if i > 0 and steps[i - 1].get('indent_level', 0) >= current_level:
                                step['indent_level'] = current_level + 1
                                self.config.update_flow_steps(selected_flow['id'], steps)
                                st.rerun()
                        if b_cols[3].button("⬅️", key=f"outdent_{i}_{selected_flow['id']}", help="减少缩进"):
                            if step.get('indent_level', 0) > 0:
                                step['indent_level'] -= 1
                                self.config.update_flow_steps(selected_flow['id'], steps)
                                st.rerun()
                        if b_cols[4].button("❌", key=f"del_{i}_{selected_flow['id']}", help="删除"):
                            steps.pop(i)
                            self.config.update_flow_steps(selected_flow['id'], steps)
                            st.rerun()
                        st.divider()

                        # --- 检查子步骤并进行递归 ---
                        next_index = i + 1
                        if next_index < len(renumbered_steps) and renumbered_steps[next_index].get('indent_level',
                                                                                                   0) > current_indent:
                            # 如果下一个步骤是当前步骤的子步骤，创建一个带边框的容器，
                            # 并递归调用本函数来渲染这个容器内的所有子步骤。
                            with st.container(border=True):
                                i = _render_steps_hierarchically(start_index=next_index,
                                                                 current_indent=current_indent + 1)
                        else:
                            # 如果没有子步骤， просто (just) 移动到下一个同级步骤。
                            i += 1

                    return i  # 当循环结束时，返回最终的索引位置。

                # --- 初始调用，开始渲染整个流程 ---
                _render_steps_hierarchically(start_index=0, current_indent=0)
                # ---------- v2.0: 优化逻辑结束 ----------
            else:
                st.info("该流程当前没有任何步骤。")

            # 添加新步骤的表单
            with st.form("add_step_form", clear_on_submit=True):
                st.write("**添加新步骤** (将添加至列表末尾)")
                elements = self.config.get_elements()
                pages = self.config.get_pages()

                if not elements or not pages:
                    st.warning("请先至少创建一个页面和一个元素。");
                    return

                # 创建一个易于阅读的元素字典，格式为 "页面名 - 元素名": element_id
                elements_dict = {}
                for e in elements:
                    page = self.config.get_item_by_id('pages', e.get('page_id', ''))
                    page_name = page['name'] if page else "未分配页面"
                    elements_dict[f"{page_name} - {e['name']}"] = e['id']

                selected_element_display = st.selectbox("选择元素", options=elements_dict.keys())
                action_type = st.selectbox("选择动作", options=self.config.get_actions())
                step_description = st.text_input("步骤说明 (可选)")

                if st.form_submit_button("✔️ 添加步骤"):
                    if selected_element_display:
                        element_id = elements_dict[selected_element_display]
                        self.config.add_step_to_flow(selected_flow['id'], element_id, action_type, step_description)
                        st.rerun()

    def render_prompt_generator_tab(self):
        """渲染“生成提示词”选项卡的内容。"""
        st.subheader("📝 生成开发提示词 (Prompt)")
        flows = self.config.get_flows()
        flow_names = [flow['name'] for flow in flows]
        if not flow_names:
            st.warning("请先创建至少一个流程。");
            return

        selected_flow_name = st.selectbox("选择一个流程来生成提示词", options=flow_names, key="prompt_flow_selector")

        if st.button("🚀 生成提示词"):
            selected_flow = next((f for f in flows if f['name'] == selected_flow_name), None)
            if selected_flow and selected_flow.get('steps'):
                renumbered_steps = self.renumber_steps(selected_flow['steps'])
                prompt_lines, page_flow = [], []

                # 第一步：生成页面流转序列 (Page A -> Page B -> Page C)
                for step in renumbered_steps:
                    element = self.config.get_item_by_id('elements', step['element_id'])
                    if not element: continue
                    page = self.config.get_item_by_id('pages', element['page_id'])
                    page_name = page['name'] if page else "未知页面"
                    # 如果页面流转列表为空，或者当前页面和上一个页面不同，则添加
                    if not page_flow or page_flow[-1] != page_name:
                        page_flow.append(page_name)

                # 将生成的元信息添加到 prompt 列表
                prompt_lines.extend([
                    f"**目的**: 自动化执行“{selected_flow_name}”流程。",
                    f"**页面流转**: {' -> '.join(page_flow)}",
                    "-" * 20
                ])

                # 第二步：逐行生成详细的步骤指令
                for step in renumbered_steps:
                    element = self.config.get_item_by_id('elements', step.get('element_id'))
                    page = self.config.get_item_by_id('pages', element.get('page_id')) if element else None
                    if not element or not page: continue

                    indent_str = "    " * step.get('indent_level', 0)  # 使用真实空格，以便复制到文本文件
                    action_line = f"{indent_str}**{step['display_order']}.** 在 **{page['name']}** 页面 **{step['action']}** “{element['name']}” 元素 (Selector: `{element['selector']}`)"
                    if step.get('description'):
                        action_line += f" (📝 **备注**: {step['description']})"
                    prompt_lines.append(action_line)

                # 将最终生成的 prompt 字符串存入 session_state
                st.session_state.generated_prompt = "\n".join(prompt_lines)

        # 如果 session_state 中有已生成的 prompt，则显示它
        if st.session_state.generated_prompt:
            st.markdown("---")
            st.write("✨ **生成的提示词预览 (可编辑)**")
            # 提供一个可编辑的文本区域
            edited_prompt = st.text_area("Prompt", value=st.session_state.generated_prompt, height=500,
                                         label_visibility="collapsed")
            # 确保即使页面重跑后，文件名也能正确生成
            prompt_flow_name = st.session_state.get("prompt_flow_selector", "flow")
            st.download_button(label="📥 下载提示词", data=edited_prompt,
                               file_name=f"prompt_{prompt_flow_name.replace(' ', '_')}.txt", mime="text/plain")


# --- 3. 主应用 ---
def main():
    """应用的主入口函数。"""
    # 设置页面配置，比如标题和布局
    st.set_page_config(page_title="采神-采集流程助手", layout="wide")
    st.title("采神 - 浏览器插件采集流程助手")

    # 初始化数据和界面管理器
    config = ConfigManager(st.session_state)
    ui = UIManager(config)

    # 定义所有选项卡的标题
    tab_titles = ["📊 总览", "📄 页面管理", "🖱️ 元素管理", "🔧 动作管理", "⚙️ 流程管理", "📝 生成提示词"]
    # 创建选项卡
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_titles)

    # 在每个 'with' 代码块中，调用 UIManager 对应的方法来渲染该选项卡的内容
    with tab1:
        ui.render_overview_tab()
    with tab2:
        ui.render_page_manager_tab()
    with tab3:
        ui.render_element_manager_tab()
    with tab4:
        ui.render_action_manager_tab()
    with tab5:
        ui.render_flow_manager_tab()
    with tab6:
        ui.render_prompt_generator_tab()


# 当这个脚本作为主程序直接运行时，执行 main() 函数
if __name__ == "__main__":
    main()