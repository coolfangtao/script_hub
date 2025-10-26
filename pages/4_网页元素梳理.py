import streamlit as st
import pandas as pd
import json
import uuid
from typing import Dict, List, Any, Optional

# from shared.sidebar import create_common_sidebar # This line is commented out as the file is not provided
# create_common_sidebar()


# --- 1. 配置管理类 (ConfigManager) ---
# MODIFIED: Removed all mock data and starts with a clean, empty structure.
class ConfigManager:
    """负责所有数据的状态管理、加载、保存和修改。"""

    def __init__(self, state):
        self._state = state
        if 'data' not in self._state:
            # Initialize with an empty but valid structure instead of mock data.
            self._state.data = {
                "actions": ["点击", "采集文本", "采集图像", "输入文本"],
                "pages": [],
                "elements": [],
                "flows": []
            }
        self._migrate_data()

    def _migrate_data(self):
        """Ensures data structure compatibility, useful for imported files."""
        data = self._state.data
        if 'actions' not in data:
            data['actions'] = ["点击", "采集文本", "采集图像", "输入文本"]
        if 'flows' in data:
            for flow in data['flows']:
                if 'steps' in flow:
                    for step in flow['steps']:
                        if 'indent_level' not in step:
                            step['indent_level'] = 0
        self._state.data = data

    def get_data(self) -> Dict[str, List[Dict]]:
        return self._state.data

    def import_data(self, new_data: Dict):
        # Basic validation for the imported data structure
        if ('pages' in new_data and isinstance(new_data['pages'], list) and
                'elements' in new_data and isinstance(new_data['elements'], list) and
                'flows' in new_data and isinstance(new_data['flows'], list)):
            self._state.data = new_data
            self._migrate_data()  # Ensure compatibility of imported data
            return True
        return False

    def get_actions(self) -> List[str]:
        return self._state.data.get('actions', [])

    def get_pages(self) -> List[Dict]:
        return self._state.data.get('pages', [])

    def get_elements(self) -> List[Dict]:
        return self._state.data.get('elements', [])

    def get_flows(self) -> List[Dict]:
        return self._state.data.get('flows', [])

    def get_item_by_id(self, item_type: str, item_id: str) -> Optional[Dict]:
        if item_type in self._state.data:
            for item in self._state.data[item_type]:
                if item['id'] == item_id:
                    return item
        return None

    def add_action(self, action_name: str):
        if action_name and action_name not in self.get_actions():
            self._state.data['actions'].append(action_name)

    def remove_action(self, action_name: str):
        if action_name in self.get_actions():
            self._state.data['actions'].remove(action_name)

    def add_page(self, page_name: str):
        if page_name:
            new_page = {"id": f"page_{uuid.uuid4().hex[:6]}", "name": page_name}
            self._state.data['pages'].append(new_page)

    def update_page(self, page_id: str, new_name: str):
        page = self.get_item_by_id('pages', page_id)
        if page and new_name:
            page['name'] = new_name

    def remove_page(self, page_id: str):
        elements_to_remove = [elem['id'] for elem in self.get_elements() if elem.get('page_id') == page_id]
        for elem_id in elements_to_remove:
            self.remove_element(elem_id)
        self._state.data['pages'] = [p for p in self.get_pages() if p['id'] != page_id]

    def add_element(self, name: str, page_id: str, selector: str, description: str):
        new_element = {
            "id": f"elem_{uuid.uuid4().hex[:6]}",
            "page_id": page_id,
            "name": name,
            "selector": selector,
            "description": description
        }
        self._state.data['elements'].append(new_element)

    def update_element(self, element_id: str, name: str, page_id: str, selector: str, description: str):
        element = self.get_item_by_id('elements', element_id)
        if element:
            element['name'] = name
            element['page_id'] = page_id
            element['selector'] = selector
            element['description'] = description

    def remove_element(self, element_id: str):
        for flow in self.get_flows():
            if 'steps' in flow:
                flow['steps'] = [step for step in flow['steps'] if step.get('element_id') != element_id]
        self._state.data['elements'] = [elem for elem in self.get_elements() if elem['id'] != element_id]

    def add_flow(self, flow_name: str):
        if flow_name and not any(f['name'] == flow_name for f in self.get_flows()):
            new_flow = {"id": f"flow_{uuid.uuid4().hex[:6]}", "name": flow_name, "steps": []}
            self._state.data['flows'].append(new_flow)

    def add_step_to_flow(self, flow_id: str, element_id: str, action: str, description: str):
        flow = self.get_item_by_id('flows', flow_id)
        if flow:
            new_step = {'element_id': element_id, 'action': action, 'description': description, 'indent_level': 0}
            if 'steps' not in flow:
                flow['steps'] = []
            flow['steps'].append(new_step)

    def update_flow_steps(self, flow_id: str, new_steps: List[Dict]):
        flow = self.get_item_by_id('flows', flow_id)
        if flow:
            flow['steps'] = new_steps


# --- 2. 界面渲染类 (UIManager) ---
class UIManager:
    """处理所有 Streamlit 界面的渲染和交互。"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager

    @staticmethod
    def renumber_steps(steps: List[Dict]) -> List[Dict]:
        counters = [0]
        for step in steps:
            indent = step.get('indent_level', 0)
            if indent >= len(counters):
                counters.extend([0] * (indent - len(counters) + 1))
            counters[indent] += 1
            counters = counters[:indent + 1]
            step['display_order'] = '.'.join(map(str, counters))
        return steps

    # MODIFIED: Fixed the infinite loop issue after file upload.
        # MODIFIED: Fixed the AttributeError by using the correct 'file_id' attribute.
    def render_overview_tab(self):
        st.subheader("🔎 流程与元素总览")

        pages = self.config.get_pages()
        flows = self.config.get_flows()

        # Check for a completely empty state to guide the user.
        if not pages and not flows:
            st.info(
                """
                **欢迎使用采神-采集流程助手！**

                看起来您还没有任何配置数据。请选择以下任一方式开始：
                1.  **导入配置 (推荐)**：在下方上传一个 `scraper_config.json` 文件来加载现有流程。
                2.  **手动创建**：前往“📄 页面与元素管理”选项卡来开始定义您的第一个页面和元素。
                """
            )
        elif not flows:
            st.warning("当前没有配置任何流程。您可以在“⚙️ 流程与提示词”选项卡中创建新流程。")
        else:
            flow_names = [flow['name'] for flow in flows]
            selected_flows = st.multiselect("筛选流程:", options=flow_names, default=flow_names)
            overview_data = []
            for flow in [f for f in flows if f['name'] in selected_flows]:
                if not flow.get('steps'): continue
                renumbered_steps = self.renumber_steps(flow['steps'])
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
                st.dataframe(pd.DataFrame(overview_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.info("您可以在下方导入、导出您的所有配置数据。")

        # FIX: Initialize a session state variable to track the processed file ID
        if 'processed_file_id' not in st.session_state:
            st.session_state.processed_file_id = None

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True, height=180):
                st.write("##### 📤 从 JSON 文件导入配置")
                uploaded_file = st.file_uploader("上传配置文件", type="json", label_visibility="collapsed")

                # FIX: Check if the file is new using the correct 'file_id' attribute
                if uploaded_file is not None and uploaded_file.file_id != st.session_state.processed_file_id:
                    try:
                        new_data = json.load(uploaded_file)
                        if self.config.import_data(new_data):
                            # Mark this file as processed by storing its unique file_id
                            st.session_state.processed_file_id = uploaded_file.file_id
                            st.success("配置已成功导入！页面将刷新。")
                            st.rerun()
                        else:
                            st.error("JSON文件格式不正确。请确保文件包含 'pages', 'elements', 和 'flows' 键。")
                            st.session_state.processed_file_id = None  # Reset on failure
                    except json.JSONDecodeError:
                        st.error("上传的文件不是有效的JSON格式。")
                        st.session_state.processed_file_id = None  # Reset on failure
        with col2:
            with st.container(border=True, height=180):
                st.write("##### 📥 导出配置到 JSON")
                json_data = json.dumps(self.config.get_data(), indent=2, ensure_ascii=False)
                st.download_button(label="下载当前配置", data=json_data, file_name="scraper_config.json",
                                   mime="application/json", use_container_width=True, disabled=not (pages or flows))

    def render_page_and_element_manager_tab(self):
        st.subheader("📄 页面与元素管理")
        st.info("在这里管理所有页面及其包含的元素。页面按三列进行展示。")

        pages = self.config.get_pages()
        all_elements = self.config.get_elements()

        if not pages:
            st.warning("目前没有任何页面。请在下方添加一个新页面开始。")

        cols = st.columns(3)
        for index, page in enumerate(pages):
            with cols[index % 3]:
                with st.expander(f"**页面: {page['name']}**", expanded=True):
                    st.write("**此页面包含的元素:**")
                    elements_on_this_page = [elem for elem in all_elements if elem.get('page_id') == page['id']]

                    if not elements_on_this_page:
                        st.caption("此页面下暂无元素。")

                    for elem in elements_on_this_page:
                        with st.expander(f"元素: {elem['name']}"):
                            st.code(elem.get('selector', '无选择器'), language='css')
                            st.caption(f"说明: {elem.get('description', '无')}")

                            edit_form_visible_key = f"edit_form_visible_{elem['id']}"
                            b_col1, b_col2, _ = st.columns([1, 1, 4])
                            if not st.session_state.get(edit_form_visible_key, False):
                                if b_col1.button("✏️ 编辑", key=f"edit_elem_{elem['id']}"):
                                    st.session_state[edit_form_visible_key] = True
                                    st.rerun()

                            confirm_delete_key = f"confirm_delete_elem_{elem['id']}"
                            if st.session_state.get(confirm_delete_key, False):
                                st.warning(f"确定要删除元素 “{elem['name']}” 吗？")
                                c_col1, c_col2, _ = st.columns([1, 1, 3])
                                if c_col1.button("✔️ 是", key=f"confirm_yes_elem_{elem['id']}", type="primary"):
                                    self.config.remove_element(elem['id'])
                                    del st.session_state[confirm_delete_key]
                                    st.success(f"元素 '{elem['name']}' 已删除。")
                                    st.rerun()
                                if c_col2.button("❌ 否", key=f"confirm_no_elem_{elem['id']}"):
                                    del st.session_state[confirm_delete_key]
                                    st.rerun()
                            else:
                                if b_col2.button("🗑️ 删除", key=f"delete_elem_{elem['id']}"):
                                    st.session_state[confirm_delete_key] = True
                                    st.rerun()

                            if st.session_state.get(edit_form_visible_key, False):
                                with st.form(key=f"edit_element_{elem['id']}"):
                                    st.write("---")
                                    edited_name = st.text_input("元素名称", value=elem['name'])
                                    edited_selector = st.text_input("选择器 (Selector)", value=elem['selector'])
                                    edited_description = st.text_area("元素说明", value=elem.get('description', ''))
                                    submit_col, cancel_col = st.columns(2)
                                    if submit_col.form_submit_button("💾 保存更改"):
                                        if all([edited_name, edited_selector]):
                                            self.config.update_element(elem['id'], edited_name, page['id'],
                                                                       edited_selector, edited_description)
                                            st.session_state[edit_form_visible_key] = False
                                            st.success(f"成功更新元素: {edited_name}")
                                            st.rerun()
                                        else:
                                            st.error("元素名称和选择器不能为空。")
                                    if cancel_col.form_submit_button("❌ 取消", type="secondary"):
                                        st.session_state[edit_form_visible_key] = False
                                        st.rerun()

                    with st.expander("➕ 添加新元素到此页面"):
                        with st.form(f"new_element_form_{page['id']}", clear_on_submit=True):
                            element_name = st.text_input("新元素名称")
                            selector = st.text_input("新元素选择器 (Selector)")
                            description = st.text_area("新元素说明")
                            if st.form_submit_button("✔️ 添加元素"):
                                if all([element_name, selector]):
                                    self.config.add_element(element_name, page['id'], selector, description)
                                    st.success(f"成功将元素 '{element_name}' 添加到页面 '{page['name']}'")
                                    st.rerun()
                                else:
                                    st.warning("元素名称和选择器不能为空。")

                    with st.expander("⚙️ 管理此页面"):
                        page_col1, page_col2 = st.columns(2)
                        with page_col1:
                            if st.session_state.get(f"editing_page_{page['id']}", False):
                                with st.form(key=f"edit_page_{page['id']}"):
                                    new_page_name = st.text_input("新页面名称", value=page['name'],
                                                                  label_visibility="collapsed")
                                    if st.form_submit_button("💾 保存", use_container_width=True):
                                        self.config.update_page(page['id'], new_page_name)
                                        st.session_state[f"editing_page_{page['id']}"] = False
                                        st.rerun()
                            else:
                                if st.button("✏️ 编辑名称", key=f"edit_btn_{page['id']}", use_container_width=True):
                                    st.session_state[f"editing_page_{page['id']}"] = True
                                    st.rerun()

                        with page_col2:
                            confirm_delete_page_key = f"confirm_delete_page_{page['id']}"
                            if st.session_state.get(confirm_delete_page_key, False):
                                st.warning(f"确定删除页面 “{page['name']}” 吗？此操作会同时删除该页面下的所有元素。", icon="⚠️")
                                pdel_c1, pdel_c2 = st.columns(2)
                                if pdel_c1.button("✔️ 是，删除", key=f"p_confirm_yes_{page['id']}",
                                                  use_container_width=True, type="primary"):
                                    self.config.remove_page(page['id'])
                                    del st.session_state[confirm_delete_page_key]
                                    st.success(f"页面 '{page['name']}' 及其所有元素已删除。")
                                    st.rerun()
                                if pdel_c2.button("❌ 否，取消", key=f"p_confirm_no_{page['id']}",
                                                  use_container_width=True):
                                    del st.session_state[confirm_delete_page_key]
                                    st.rerun()
                            else:
                                if st.button("🗑️ 删除页面", key=f"delete_btn_{page['id']}", type="primary",
                                             use_container_width=True):
                                    st.session_state[confirm_delete_page_key] = True
                                    st.rerun()

        st.divider()
        with st.expander("➕ 添加一个全新的页面"):
            with st.form("new_page_form", clear_on_submit=True):
                new_page_name = st.text_input("新页面名称")
                if st.form_submit_button("创建页面") and new_page_name:
                    self.config.add_page(new_page_name)
                    st.success(f"成功创建页面: {new_page_name}")
                    st.rerun()

    def render_action_manager_tab(self):
        st.subheader("🔧 动作管理")
        st.info("在这里管理流程中可用的动作类型。")
        actions = self.config.get_actions()
        st.write(f"当前可用动作: `{', '.join(actions)}`")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("new_action_form", clear_on_submit=True):
                new_action = st.text_input("添加新动作")
                if st.form_submit_button("➕ 添加"):
                    if new_action and new_action not in actions:
                        self.config.add_action(new_action)
                        st.rerun()
                    else:
                        st.warning("动作不能为空或已存在。")
        with col2:
            action_to_remove = st.selectbox("选择要删除的动作", options=[""] + actions)
            if st.button("❌ 删除选中动作", disabled=(not action_to_remove)):
                self.config.remove_action(action_to_remove)
                st.rerun()

    # MODIFIED: Added logic to include the element's own description in the prompt.
    def _generate_prompt_string(self, flow: Optional[Dict]) -> str:
        """Generates the prompt string for a given flow."""
        if not flow or not flow.get('steps'):
            return "当前流程没有步骤，无法生成提示词。"

        renumbered_steps = self.renumber_steps(flow['steps'])
        prompt_lines, page_flow = [], []

        for step in renumbered_steps:
            element = self.config.get_item_by_id('elements', step['element_id'])
            if not element: continue
            page = self.config.get_item_by_id('pages', element['page_id'])
            page_name = page['name'] if page else "未知页面"
            if not page_flow or page_flow[-1] != page_name: page_flow.append(page_name)

        prompt_lines.extend(
            [f"**目的**: 自动化执行“{flow['name']}”流程。", f"**页面流转**: {' -> '.join(page_flow)}", "-" * 20])

        for step in renumbered_steps:
            element = self.config.get_item_by_id('elements', step.get('element_id'))
            page = self.config.get_item_by_id('pages', element.get('page_id')) if element else None
            if not element or not page: continue

            indent_str = "    " * step.get('indent_level', 0)

            # Start building the main action line
            action_line = f"{indent_str}**{step['display_order']}.** 在 **{page['name']}** 页面 **{step['action']}** “{element['name']}” 元素 (Selector: `{element['selector']}`)"

            # --- THIS IS THE NEW PART ---
            # Check for the ELEMENT's description and add it
            if element.get('description'):
                action_line += f" (ℹ️ **元素说明**: {element['description']})"
            # --- END OF NEW PART ---

            # Check for the STEP's description and add it
            if step.get('description'):
                action_line += f" (📝 **步骤备注**: {step['description']})"

            prompt_lines.append(action_line)

        return "\n".join(prompt_lines)

    def render_flow_and_prompt_tab(self):
        """渲染“流程与提示词”选项卡，集成了流程编排和实时提示词生成。"""

        def _update_selected_page_for_flow():
            st.session_state.add_step_page_selection = st.session_state.add_step_page_selector

        def _clear_page_selection():
            if 'add_step_page_selection' in st.session_state:
                del st.session_state.add_step_page_selection

        left_col, right_col = st.columns(2)

        with right_col:
            st.subheader("⚙️ 流程配置")
            flows = self.config.get_flows()
            flow_names = [flow['name'] for flow in flows]

            with st.form("new_flow_form", clear_on_submit=True):
                new_flow_name = st.text_input("新流程名称")
                if st.form_submit_button("创建新流程"):
                    if new_flow_name and new_flow_name not in flow_names:
                        self.config.add_flow(new_flow_name)
                        st.rerun()
                    else:
                        st.warning("流程名称不能为空或已存在。")

            selected_flow_name = st.radio(
                "选择要编辑的流程:", flow_names, key="flow_selector", on_change=_clear_page_selection,
                disabled=not flow_names
            )
            st.divider()
            st.write("**添加新步骤** (将添加至列表末尾)")
            elements = self.config.get_elements()
            pages = self.config.get_pages()

            if not pages:
                st.warning("请先在“页面与元素管理”中创建页面。")
            else:
                page_names = [p['name'] for p in pages]
                selected_page_name = st.selectbox(
                    "1. 首先选择页面", options=page_names, key='add_step_page_selector',
                    on_change=_update_selected_page_for_flow
                )
                page_to_filter_by = st.session_state.get('add_step_page_selection', selected_page_name)
                selected_page = next((p for p in pages if p['name'] == page_to_filter_by), None)
                elements_on_page = [e for e in elements if
                                    e.get('page_id') == (selected_page['id'] if selected_page else None)]
                element_names_on_page = [e['name'] for e in elements_on_page]
                selected_element_name = st.selectbox(
                    "2. 然后选择元素", options=element_names_on_page, disabled=not elements_on_page
                )
                if not elements_on_page and selected_page:
                    st.caption(f"页面“{page_to_filter_by}”下没有可用的元素。")

                with st.form("add_step_submit_form", clear_on_submit=True):
                    action_type = st.selectbox("选择动作", options=self.config.get_actions())
                    step_description = st.text_input("步骤说明 (可选)")
                    submitted = st.form_submit_button("✔️ 添加步骤", disabled=(not selected_element_name or not selected_flow_name))
                    if submitted:
                        selected_flow = next((f for f in flows if f['name'] == selected_flow_name), None)
                        selected_element = next((e for e in elements_on_page if e['name'] == selected_element_name),
                                                None)
                        if selected_element and selected_flow:
                            self.config.add_step_to_flow(selected_flow['id'], selected_element['id'], action_type,
                                                         step_description)
                            _clear_page_selection()
                            st.rerun()
        with left_col:
            st.subheader("📝 流程编排与提示词")
            if not selected_flow_name:
                st.info("请在右侧选择或创建一个流程进行编排。")
                return

            selected_flow = next((f for f in self.config.get_flows() if f['name'] == selected_flow_name), None)
            st.write(f"#### 正在编排: **{selected_flow_name}**")

            if selected_flow and selected_flow.get('steps'):
                steps = selected_flow['steps']
                renumbered_steps = self.renumber_steps(steps)

                def _render_steps_hierarchically(start_index: int, current_indent: int) -> int:
                    i = start_index
                    while i < len(renumbered_steps):
                        step = renumbered_steps[i]
                        step_indent = step.get('indent_level', 0)

                        if step_indent < current_indent:
                            return i

                        if step_indent > current_indent:
                            i += 1
                            continue

                        element = self.config.get_item_by_id('elements', step['element_id'])
                        page = self.config.get_item_by_id('pages', element['page_id']) if element else None

                        st.markdown(
                            f"<div><b>{step['display_order']}.</b> 在 <b>{page['name'] if page else 'N/A'}</b> 页面 <b>{step['action']}</b> <b>{element['name'] if element else 'N/A'}</b></div>",
                            unsafe_allow_html=True)
                        if step.get('description'):
                            st.markdown(
                                f"<div><blockquote>📝: <i>{step['description']}</i></blockquote></div>",
                                unsafe_allow_html=True)

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

                        next_index = i + 1
                        if next_index < len(renumbered_steps) and renumbered_steps[next_index].get('indent_level',
                                                                                                   0) > current_indent:
                            with st.container(border=True):
                                i = _render_steps_hierarchically(start_index=next_index,
                                                                 current_indent=current_indent + 1)
                        else:
                            i += 1
                    return i

                _render_steps_hierarchically(start_index=0, current_indent=0)
            else:
                st.info("该流程当前没有任何步骤。请在右侧添加新步骤。")

            with st.expander("✨ 开发提示词 (Prompt)", expanded=True):
                prompt_text = self._generate_prompt_string(selected_flow)
                st.text_area("Prompt", value=prompt_text, height=250, label_visibility="collapsed")
                st.download_button(
                    label="📥 下载提示词", data=prompt_text,
                    file_name=f"prompt_{selected_flow_name.replace(' ', '_')}.txt", mime="text/plain"
                )


# --- 3. 主应用 ---
def main():
    """应用的主入口函数。"""
    st.set_page_config(page_title="采神-采集流程助手", layout="wide")
    st.title("采神 - 浏览器插件采集流程助手")

    config = ConfigManager(st.session_state)
    ui = UIManager(config)

    tab_titles = ["📊 总览与导入导出", "📄 页面与元素管理", "⚙️ 流程与提示词", "🔧 动作管理"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        ui.render_overview_tab()
    with tab2:
        ui.render_page_and_element_manager_tab()
    with tab3:
        ui.render_flow_and_prompt_tab()
    with tab4:
        ui.render_action_manager_tab()


if __name__ == "__main__":
    main()