import streamlit as st
import json
import copy
import uuid


# --- 配置类 ---
class Config:
    """存放应用的静态配置"""
    INPUT_OUTPUT_TYPES = ["text", "image", "file", "audio", "video"]
    PRICING_UNITS = {
        "按Token (每百万)": "per_token_m",
        "按Token (每一千)": "per_token_k",
        "按次 (每一次)": "per_call_single",
        "按次 (每一千次)": "per_call_k"
    }
    CURRENCIES = ["USD", "CNY"]
    # 假设一个固定的汇率用于转换，实际应用中可以考虑API调用获取实时汇率
    USD_TO_CNY_RATE = 7.2


# --- 数据管理类 ---
class DataManager:
    """处理所有数据的增删改查、导入导出"""

    def __init__(self):
        if 'tasks' not in st.session_state:
            st.session_state.tasks = []
        if 'platforms' not in st.session_state:
            st.session_state.platforms = []

    def get_tasks(self):
        return st.session_state.tasks

    def get_platforms(self):
        return st.session_state.platforms

    def add_or_update_task(self, task_data, task_id=None):
        if task_id:
            for i, task in enumerate(st.session_state.tasks):
                if task['id'] == task_id:
                    st.session_state.tasks[i] = task_data
                    return
        else:
            task_data['id'] = str(uuid.uuid4())
            st.session_state.tasks.append(task_data)

    def delete_task(self, task_id):
        st.session_state.tasks = [t for t in st.session_state.tasks if t.get('id') != task_id]

    def add_or_update_platform(self, platform_data, platform_id=None):
        if platform_id:
            for i, p in enumerate(st.session_state.platforms):
                if p['id'] == platform_id:
                    st.session_state.platforms[i] = platform_data
                    return
        else:
            platform_data['id'] = str(uuid.uuid4())
            st.session_state.platforms.append(platform_data)

    def delete_platform(self, platform_id):
        st.session_state.platforms = [p for p in st.session_state.platforms if p.get('id') != platform_id]

    def add_or_update_model(self, platform_id, model_data, model_id=None):
        for p in st.session_state.platforms:
            if p['id'] == platform_id:
                if 'models' not in p:
                    p['models'] = []
                if model_id:
                    for i, m in enumerate(p['models']):
                        if m['id'] == model_id:
                            p['models'][i] = model_data
                            return
                else:
                    model_data['id'] = str(uuid.uuid4())
                    p['models'].append(model_data)
                return

    def delete_model(self, platform_id, model_id):
        for p in st.session_state.platforms:
            if p['id'] == platform_id:
                p['models'] = [m for m in p['models'] if m.get('id') != model_id]
                return

    def export_data(self):
        return json.dumps({
            "tasks": st.session_state.tasks,
            "platforms": st.session_state.platforms
        }, indent=2)

    def import_data(self, uploaded_file):
        try:
            data = json.load(uploaded_file)
            st.session_state.tasks = data.get("tasks", [])
            st.session_state.platforms = data.get("platforms", [])
            # 确保导入的数据有ID
            for task in st.session_state.tasks:
                task.setdefault('id', str(uuid.uuid4()))
            for platform in st.session_state.platforms:
                platform.setdefault('id', str(uuid.uuid4()))
                for model in platform.get('models', []):
                    model.setdefault('id', str(uuid.uuid4()))
            return True
        except json.JSONDecodeError:
            return False


# --- UI界面类 ---
class StreamlitApp:
    """管理所有Streamlit界面组件和逻辑"""

    def __init__(self, data_manager):
        self.dm = data_manager
        self.config = Config()

    def render(self):
        st.set_page_config(layout="wide", page_title="AI模型成本计算器")
        st.title("AI模型成本计算与任务管理")
        st.write("一个用于管理AI任务、模型价格并快速计算任务成本的工具。")

        self.render_import_export()

        tab1, tab2 = st.tabs(["📊 任务与计费", "🛠️ 平台与模型配置"])

        with tab1:
            self.render_task_and_billing_tab()

        with tab2:
            self.render_platform_and_model_tab()

    def render_import_export(self):
        with st.sidebar:
            st.header("数据导入/导出")

            # 导出
            json_data = self.dm.export_data()
            st.download_button(
                label="📥 导出所有配置 (JSON)",
                data=json_data,
                file_name="ai_model_config.json",
                mime="application/json"
            )

            # 导入
            uploaded_file = st.file_uploader("📤 导入配置 (JSON)", type="json")
            if uploaded_file is not None:
                if self.dm.import_data(uploaded_file):
                    st.success("配置已成功导入！")
                    st.rerun()
                else:
                    st.error("导入失败，请检查文件格式是否正确。")

    # --- 任务与计费标签页 ---
    def render_task_and_billing_tab(self):
        st.header("任务管理")

        # 任务表单
        with st.expander("➕ 新建/编辑任务", expanded=False):
            self.render_task_form()

        # 任务列表
        tasks = self.dm.get_tasks()
        if not tasks:
            st.info("尚未创建任何任务。请在上方表单中新建一个任务。")
            return

        task_options = {task['name']: task['id'] for task in tasks}
        selected_task_name = st.selectbox("选择要分析的任务", options=task_options.keys())

        if selected_task_name:
            task_id = task_options[selected_task_name]
            task = next((t for t in tasks if t['id'] == task_id), None)

            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader(f"任务详情: {task['name']}")
                st.write(f"**任务总数**: {task['total_count']:,}")
                st.write("**输入格式与Token消耗:**")
                for item in task['inputs']:
                    st.write(f"- {item['type'].capitalize()}: {item['tokens']:,} tokens")
                st.write("**输出格式与Token消耗:**")
                for item in task['outputs']:
                    st.write(f"- {item['type'].capitalize()}: {item['tokens']:,} tokens")

                edit_btn, delete_btn = st.columns(2)
                if edit_btn.button("✏️ 编辑此任务"):
                    st.session_state.editing_task_id = task_id
                    # 当开始编辑时，将当前任务数据加载到session_state中
                    if 'task_form_inputs' not in st.session_state:
                        st.session_state.task_form_inputs = task.get('inputs', [])
                    if 'task_form_outputs' not in st.session_state:
                        st.session_state.task_form_outputs = task.get('outputs', [])
                    st.rerun()
                if delete_btn.button("🗑️ 删除此任务", key=f"del_{task_id}"):
                    self.dm.delete_task(task_id)
                    st.success(f"任务 '{task['name']}' 已删除。")
                    st.rerun()

            with col2:
                st.subheader("可用模型与成本预估")
                self.calculate_and_display_costs(task)

    def render_task_form(self, task_id=None):
        is_editing = 'editing_task_id' in st.session_state and st.session_state.editing_task_id is not None

        task_to_edit = None
        if is_editing:
            task_id = st.session_state.editing_task_id
            task_to_edit = next((t for t in self.dm.get_tasks() if t['id'] == task_id), None)

        default_task = {
            'name': '', 'total_count': 1000, 'inputs': [{'type': 'text', 'tokens': 100}],
            'outputs': [{'type': 'text', 'tokens': 100}]
        }
        task_data = task_to_edit or default_task

        # 初始化表单状态
        if 'task_form_inputs' not in st.session_state:
            st.session_state.task_form_inputs = copy.deepcopy(task_data.get('inputs', []))
        if 'task_form_outputs' not in st.session_state:
            st.session_state.task_form_outputs = copy.deepcopy(task_data.get('outputs', []))

        # 表单本身，只包含数据输入字段
        with st.form(key="task_form"):
            name = st.text_input("任务名称", value=task_data['name'])
            total_count = st.number_input("任务总数", min_value=1, value=task_data['total_count'])

            st.markdown("---")
            st.markdown("**输入配置**")
            self._render_io_widgets_in_form('inputs')

            st.markdown("---")
            st.markdown("**输出配置**")
            self._render_io_widgets_in_form('outputs')

            submitted = st.form_submit_button("✅ 保存任务" if is_editing else "➕ 添加任务")
            if submitted:
                if not name:
                    st.error("任务名称不能为空！")
                else:
                    final_task = {
                        "id": task_id,
                        "name": name,
                        "total_count": total_count,
                        "inputs": st.session_state.task_form_inputs,
                        "outputs": st.session_state.task_form_outputs
                    }
                    self.dm.add_or_update_task(final_task, task_id)
                    st.success(f"任务 '{name}' 已成功保存！")
                    # 清理状态
                    if 'editing_task_id' in st.session_state:
                        del st.session_state.editing_task_id
                    del st.session_state.task_form_inputs
                    del st.session_state.task_form_outputs
                    st.rerun()

        # 管理按钮，放在表单外部
        st.markdown("---")
        st.markdown("**管理输入/输出行**")
        self._render_io_management_buttons('inputs')
        self._render_io_management_buttons('outputs')

        if is_editing:
            if st.button("❌ 取消编辑"):
                del st.session_state.editing_task_id
                del st.session_state.task_form_inputs
                del st.session_state.task_form_outputs
                st.rerun()

    def _render_io_widgets_in_form(self, io_type: str):
        """仅在表单内部渲染输入和输出的字段（无按钮）"""
        state_key = f'task_form_{io_type}'

        for i in range(len(st.session_state[state_key])):
            cols = st.columns([3, 3])
            with cols[0]:
                st.session_state[state_key][i]['type'] = st.selectbox(
                    "格式", self.config.INPUT_OUTPUT_TYPES,
                    index=self.config.INPUT_OUTPUT_TYPES.index(st.session_state[state_key][i]['type']),
                    key=f"{io_type}_type_{i}"
                )
            with cols[1]:
                st.session_state[state_key][i]['tokens'] = st.number_input(
                    "Token数量", min_value=0,
                    value=st.session_state[state_key][i]['tokens'],
                    key=f"{io_type}_tokens_{i}"
                )

    def _render_io_management_buttons(self, io_type: str):
        """在表单外部渲染用于添加和删除行的按钮"""
        state_key = f'task_form_{io_type}'
        io_label = '输入' if io_type == 'inputs' else '输出'

        # 倒序遍历以安全删除
        for i in reversed(range(len(st.session_state[state_key]))):
            cols = st.columns([6, 1])
            item = st.session_state[state_key][i]
            cols[0].info(f"{io_label}行 #{i + 1}: 类型={item['type'].capitalize()}, Tokens={item['tokens']}")
            if cols[1].button("➖", key=f"{io_type}_del_{i}", help=f"删除此{io_label}行"):
                st.session_state[state_key].pop(i)
                st.rerun()

        if st.button(f"➕ 添加{io_label}行", key=f"{io_type}_add"):
            st.session_state[state_key].append({'type': 'text', 'tokens': 0})
            st.rerun()

    # --- 平台与模型标签页 ---
    def render_platform_and_model_tab(self):
        st.header("平台与模型库")

        with st.expander("➕ 添加新平台"):
            with st.form("new_platform_form", clear_on_submit=True):
                platform_name = st.text_input("平台名称")
                platform_limits = st.text_area("平台限制说明（可选）", help="例如：所有免费模型总请求次数不超过50次/天")
                submitted = st.form_submit_button("添加平台")
                if submitted and platform_name:
                    self.dm.add_or_update_platform({
                        "name": platform_name,
                        "limits": platform_limits,
                        "models": []
                    })
                    st.success(f"平台 '{platform_name}' 已添加。")
                    st.rerun()

        platforms = self.dm.get_platforms()
        if not platforms:
            st.info("尚未配置任何AI平台。")
            return

        for platform in platforms:
            with st.container(border=True):
                st.subheader(f"平台: {platform['name']}")
                st.caption(platform.get('limits', '无特定限制'))

                if st.button("🗑️ 删除平台", key=f"del_platform_{platform['id']}"):
                    self.dm.delete_platform(platform['id'])
                    st.rerun()

                st.markdown("---")
                st.markdown("**模型列表**")

                for model in platform.get('models', []):
                    with st.expander(f"模型: {model['name']}", expanded=False):
                        self.render_model_form(platform['id'], model['id'])

                with st.expander("➕ 添加新模型到此平台"):
                    self.render_model_form(platform['id'])

    def render_model_form(self, platform_id, model_id=None):
        is_editing = model_id is not None
        model_data = None
        if is_editing:
            platform = next((p for p in self.dm.get_platforms() if p['id'] == platform_id), None)
            if platform:
                model_data = next((m for m in platform.get('models', []) if m['id'] == model_id), None)

        default_model = {
            "name": "", "is_free": False, "supported_inputs": [], "supported_outputs": [],
            "pricing": {}, "rate_limits": ""
        }
        model_data = model_data or default_model

        with st.form(key=f"model_form_{platform_id}_{model_id or 'new'}"):
            name = st.text_input("模型名称", value=model_data['name'])
            is_free = st.checkbox("这是一个免费模型", value=model_data.get('is_free', False))

            supported_inputs = st.multiselect(
                "支持的输入类型", self.config.INPUT_OUTPUT_TYPES, default=model_data['supported_inputs']
            )
            supported_outputs = st.multiselect(
                "支持的输出类型", self.config.INPUT_OUTPUT_TYPES, default=model_data['supported_outputs']
            )

            st.markdown("**定价信息 (如果非免费)**")
            pricing = copy.deepcopy(model_data.get('pricing', {}))

            if not is_free:
                # 定价配置
                all_io_types = sorted(list(set(supported_inputs + supported_outputs)))
                for io_type in all_io_types:
                    st.markdown(f"**{io_type.capitalize()} 定价:**")
                    cols = st.columns(3)

                    pricing_info = pricing.get(io_type,
                                               {'unit': list(self.config.PRICING_UNITS.values())[0], 'rate': 0.0,
                                                'currency': 'USD'})

                    with cols[0]:
                        unit_key = st.selectbox(
                            f"计价单位 ({io_type})", options=self.config.PRICING_UNITS.keys(),
                            key=f"unit_{platform_id}_{model_id}_{io_type}",
                            index=list(self.config.PRICING_UNITS.values()).index(pricing_info['unit'])
                        )
                        pricing_info['unit'] = self.config.PRICING_UNITS[unit_key]

                    with cols[1]:
                        pricing_info['rate'] = st.number_input(
                            f"费率 ({io_type})", min_value=0.0, format="%.6f",
                            value=float(pricing_info.get('rate', 0.0)),
                            key=f"rate_{platform_id}_{model_id}_{io_type}"
                        )

                    with cols[2]:
                        pricing_info['currency'] = st.selectbox(
                            f"货币 ({io_type})", self.config.CURRENCIES,
                            index=self.config.CURRENCIES.index(pricing_info.get('currency', 'USD')),
                            key=f"currency_{platform_id}_{model_id}_{io_type}"
                        )
                    pricing[io_type] = pricing_info

            rate_limits = st.text_area("速率限制说明 (可选)", value=model_data['rate_limits'], help="例如：RPM: 60, TPM: 100000")

            submit_btn = st.form_submit_button("✅ 保存模型")

            if submit_btn:
                if not name:
                    st.error("模型名称不能为空！")
                else:
                    new_model_data = {
                        "id": model_id,
                        "name": name,
                        "is_free": is_free,
                        "supported_inputs": supported_inputs,
                        "supported_outputs": supported_outputs,
                        "pricing": {} if is_free else pricing,
                        "rate_limits": rate_limits
                    }
                    self.dm.add_or_update_model(platform_id, new_model_data, model_id)
                    st.success(f"模型 '{name}' 已保存。")
                    st.rerun()

        if is_editing:
            if st.button("🗑️ 删除模型", key=f"del_model_{platform_id}_{model_id}"):
                self.dm.delete_model(platform_id, model_id)
                st.rerun()

    # --- 核心计算逻辑 ---
    def calculate_and_display_costs(self, task):
        required_inputs = {item['type'] for item in task['inputs']}
        required_outputs = {item['type'] for item in task['outputs']}

        compatible_models = []
        platforms = self.dm.get_platforms()

        for platform in platforms:
            for model in platform.get('models', []):
                supported_inputs = set(model.get('supported_inputs', []))
                supported_outputs = set(model.get('supported_outputs', []))

                if required_inputs.issubset(supported_inputs) and required_outputs.issubset(supported_outputs):
                    cost_usd, cost_cny = self._calculate_single_model_cost(task, model)
                    compatible_models.append({
                        "platform": platform['name'],
                        "model": model['name'],
                        "cost_usd": cost_usd,
                        "cost_cny": cost_cny,
                        "is_free": model.get('is_free', False),
                        "rate_limits": model.get('rate_limits', 'N/A')
                    })

        if not compatible_models:
            st.warning("根据当前任务的输入/输出配置，没有找到任何兼容的模型。")
            return

        # 排序：免费的在前，然后按美元价格升序
        sorted_models = sorted(compatible_models, key=lambda x: (x['is_free'], -x['cost_usd']), reverse=True)

        st.dataframe(
            [
                {
                    "平台": m['platform'], "模型": m['model'],
                    "成本 (USD)": "免费" if m['is_free'] else f"${m['cost_usd']:.4f}",
                    "成本 (CNY)": "免费" if m['is_free'] else f"¥{m['cost_cny']:.4f}",
                    "速率限制": m['rate_limits']
                } for m in sorted_models
            ],
            use_container_width=True
        )

    def _calculate_single_model_cost(self, task, model):
        if model.get('is_free', False):
            return 0.0, 0.0

        total_cost_usd = 0.0
        task_count = task['total_count']
        pricing = model.get('pricing', {})

        # 计算输入成本
        for item in task['inputs']:
            io_type = item['type']
            tokens = item['tokens']

            if io_type in pricing:
                price_info = pricing[io_type]
                rate = price_info.get('rate', 0.0)
                unit = price_info.get('unit')
                currency = price_info.get('currency', 'USD')

                cost = 0.0
                if unit == 'per_token_m':  # 每百万Token
                    cost = (task_count * tokens * rate) / 1_000_000
                elif unit == 'per_token_k':  # 每千Token
                    cost = (task_count * tokens * rate) / 1_000
                elif unit == 'per_call_k':  # 每千次调用
                    cost = (task_count * rate) / 1_000
                elif unit == 'per_call_single':  # 每一次调用
                    cost = task_count * rate

                if currency == 'CNY':
                    total_cost_usd += cost / self.config.USD_TO_CNY_RATE
                else:
                    total_cost_usd += cost

        # 计算输出成本
        for item in task['outputs']:
            io_type = item['type']
            tokens = item['tokens']

            if io_type in pricing:
                price_info = pricing[io_type]
                rate = price_info.get('rate', 0.0)
                unit = price_info.get('unit')
                currency = price_info.get('currency', 'USD')

                cost = 0.0
                if unit == 'per_token_m':
                    cost = (task_count * tokens * rate) / 1_000_000
                elif unit == 'per_token_k':
                    cost = (task_count * tokens * rate) / 1_000
                elif unit == 'per_call_k':
                    cost = (task_count * rate) / 1_000
                elif unit == 'per_call_single':
                    cost = task_count * rate

                if currency == 'CNY':
                    total_cost_usd += cost / self.config.USD_TO_CNY_RATE
                else:
                    total_cost_usd += cost

        total_cost_cny = total_cost_usd * self.config.USD_TO_CNY_RATE
        return total_cost_usd, total_cost_cny


# --- 主程序入口 ---
if __name__ == "__main__":
    data_manager = DataManager()
    app = StreamlitApp(data_manager)
    app.render()