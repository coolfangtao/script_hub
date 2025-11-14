import streamlit as st
import json
import copy
from typing import List, Dict, Any, Optional

# 定义常量以便复用和维护
INPUT_FORMATS = ['text', 'image', 'file', 'audio', 'video']
OUTPUT_FORMATS = ['text', 'image', 'file', 'audio', 'video']
PRICING_METHODS = ['per_token', 'per_call']
CURRENCIES = ['CNY', 'USD']


class DataManager:
    """
    负责管理所有应用数据，包括任务、平台、模型配置的加载、保存、计算等。
    """

    def __init__(self, state):
        self._state = state
        if 'data' not in self._state:
            self._state.data = self.get_default_data()

    @staticmethod
    def get_default_data() -> Dict[str, Any]:
        """返回一个空的初始数据结构。"""
        return {
            "tasks": [],
            "platforms": [],
            "settings": {"usd_to_cny_rate": 7.25}
        }

    @property
    def data(self) -> Dict[str, Any]:
        return self._state.data

    def load_data_from_json(self, uploaded_file) -> bool:
        """从上传的JSON文件加载数据。"""
        try:
            new_data = json.load(uploaded_file)
            # 基础的验证
            if "tasks" in new_data and "platforms" in new_data:
                self._state.data = new_data
                if "settings" not in self._state.data:  # 兼容旧格式
                    self._state.data["settings"] = self.get_default_data()["settings"]
                return True
            else:
                st.error("JSON文件格式不正确，缺少 'tasks' 或 'platforms' 键。")
                return False
        except Exception as e:
            st.error(f"加载或解析JSON文件时出错: {e}")
            return False

    def export_data_to_json(self) -> str:
        """将当前数据导出为JSON字符串。"""
        return json.dumps(self.data, indent=4, ensure_ascii=False)

    def find_compatible_models(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据任务的输入输出要求，筛选出所有兼容的模型。"""
        if not task:
            return []

        compatible_models = []
        task_input_formats = {item['format'] for item in task.get('inputs', [])}
        task_output_formats = {item['format'] for item in task.get('outputs', [])}

        for platform in self.data.get('platforms', []):
            for model in platform.get('models', []):
                model_input_formats = set(model.get('supported_inputs', []))
                model_output_formats = set(model.get('supported_outputs', []))

                # 模型的输入/输出能力必须是任务需求的超集
                if model_input_formats.issuperset(task_input_formats) and \
                        model_output_formats.issuperset(task_output_formats):
                    model_info = copy.deepcopy(model)
                    model_info['platform_name'] = platform.get('name')
                    model_info['platform_limits'] = platform.get('limits')
                    compatible_models.append(model_info)
        return compatible_models

    def calculate_task_cost(self, task: Dict[str, Any], model: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """计算单个模型完成指定任务的总成本。"""
        if not task or not model:
            return None

        # 如果模型免费，直接返回0
        if model.get('pricing', []) == 'free':
            return {'CNY': 0.0, 'USD': 0.0}

        total_cost_usd = 0.0
        task_count = task.get('count', 1000)

        # 遍历任务的每个输入和输出项
        for io_type in ['inputs', 'outputs']:
            for task_item in task.get(io_type, []):
                item_format = task_item['format']
                item_tokens = task_item.get('tokens', 0)
                item_cost_found = False

                # 在模型的定价规则中寻找匹配项
                for price_rule in model.get('pricing', []):
                    if price_rule.get('io_type', 'input') == io_type[:-1] and price_rule.get('format') == item_format:
                        price = price_rule.get('price', 0)
                        unit = price_rule.get('unit', 1)
                        method = price_rule.get('method')
                        currency = price_rule.get('currency', 'USD')

                        item_cost = 0
                        if method == 'per_token':
                            item_cost = (item_tokens / unit) * price if unit > 0 else 0
                        elif method == 'per_call':
                            # 每次调用计费，与token数无关
                            item_cost = (1 / unit) * price if unit > 0 else 0

                        # 统一换算成美元进行累加
                        if currency == 'CNY':
                            rate = self.data['settings']['usd_to_cny_rate']
                            total_cost_usd += item_cost / rate if rate > 0 else 0
                        else:
                            total_cost_usd += item_cost

                        item_cost_found = True
                        break  # 找到匹配的规则后就不再继续查找

                if not item_cost_found:
                    # 如果任务需要某个格式，但模型没有为该格式定价，则无法计算成本
                    return None

        total_cost_usd *= task_count
        total_cost_cny = total_cost_usd * self.data['settings']['usd_to_cny_rate']

        return {'CNY': total_cost_cny, 'USD': total_cost_usd}


class UIManager:
    """
    负责渲染Streamlit界面，并处理用户交互。
    """

    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        # 初始化session_state中的临时变量
        if 'current_task_idx' not in st.session_state:
            st.session_state.current_task_idx = None

    def run(self):
        """主运行函数，构建整个应用的UI。"""
        st.set_page_config(layout="wide", page_title="AI模型成本计算器")
        st.title("🤖 AI 模型成本可视化计算器")
        st.caption("帮助您快速筛选并计算不同AI模型处理特定任务的成本")

        self.render_sidebar()

        tab1, tab2 = st.tabs(["📊 任务与计费结果", "⚙️ 平台与模型配置"])

        with tab1:
            self.render_task_and_results_tab()

        with tab2:
            self.render_settings_tab()

    def render_sidebar(self):
        """渲染侧边栏，用于导入导出和全局设置。"""
        with st.sidebar:
            st.header("数据管理")

            # 导出功能
            st.download_button(
                label="📥 导出所有配置 (JSON)",
                data=self.dm.export_data_to_json(),
                file_name="ai_cost_config.json",
                mime="application/json"
            )

            # 导入功能
            uploaded_file = st.file_uploader("📤 导入配置 (JSON)", type="json")
            if uploaded_file is not None:
                if self.dm.load_data_from_json(uploaded_file):
                    st.success("配置已成功导入！")
                    st.rerun()

            st.divider()
            st.header("全局设置")
            rate = st.number_input(
                "美元兑人民币汇率",
                min_value=0.1,
                value=self.dm.data['settings']['usd_to_cny_rate'],
                step=0.01,
                format="%.2f"
            )
            self.dm.data['settings']['usd_to_cny_rate'] = rate

    def render_task_and_results_tab(self):
        """渲染任务定义和成本计算结果的标签页。"""
        st.header("第一步：定义或选择您的任务")

        tasks = self.dm.data['tasks']
        task_names = [t['name'] for t in tasks]

        col1, col2 = st.columns([1, 2])
        with col1:
            # 如果存在任务，允许用户选择
            if task_names:
                selected_task_name = st.selectbox(
                    "选择一个已有的任务",
                    options=task_names,
                    index=st.session_state.current_task_idx or 0,
                    key="task_selector"
                )
                st.session_state.current_task_idx = task_names.index(selected_task_name)

            # 按钮用于创建新任务
            if st.button("➕ 创建新任务"):
                new_task = {"name": f"新任务-{len(tasks) + 1}", "count": 1000, "inputs": [], "outputs": []}
                tasks.append(new_task)
                st.session_state.current_task_idx = len(tasks) - 1
                st.rerun()

        current_task = tasks[
            st.session_state.current_task_idx] if st.session_state.current_task_idx is not None else None

        # 任务编辑器
        if current_task:
            with st.expander("✏️ 编辑任务详情", expanded=True):
                with st.form("task_editor_form"):
                    edited_task = copy.deepcopy(current_task)

                    edited_task['name'] = st.text_input("任务名称", value=edited_task['name'])
                    edited_task['count'] = st.number_input("任务总数", min_value=1, value=edited_task['count'])

                    st.markdown("##### 输入配置")
                    edited_task['inputs'] = st.data_editor(
                        edited_task['inputs'],
                        num_rows="dynamic",
                        column_config={
                            "format": st.column_config.SelectboxColumn("输入格式", options=INPUT_FORMATS, required=True),
                            "tokens": st.column_config.NumberColumn("Token数量", min_value=0, required=True),
                        },
                        key="inputs_editor"
                    )

                    st.markdown("##### 输出配置")
                    edited_task['outputs'] = st.data_editor(
                        edited_task['outputs'],
                        num_rows="dynamic",
                        column_config={
                            "format": st.column_config.SelectboxColumn("输出格式", options=OUTPUT_FORMATS, required=True),
                            "tokens": st.column_config.NumberColumn("Token数量", min_value=0, required=True),
                        },
                        key="outputs_editor"
                    )

                    col_submit, col_delete, _ = st.columns([1, 1, 4])
                    if col_submit.form_submit_button("💾 保存任务变更"):
                        self.dm.data['tasks'][st.session_state.current_task_idx] = edited_task
                        st.success(f"任务 '{edited_task['name']}' 已保存！")
                        st.rerun()

                    if col_delete.form_submit_button("🗑️ 删除此任务"):
                        self.dm.data['tasks'].pop(st.session_state.current_task_idx)
                        st.session_state.current_task_idx = 0 if len(self.dm.data['tasks']) > 0 else None
                        st.rerun()

        st.divider()

        # 结果展示
        st.header("第二步：查看可用模型及其成本")
        if current_task:
            compatible_models = self.dm.find_compatible_models(current_task)
            if not compatible_models:
                st.warning("根据当前任务的输入/输出配置，没有找到任何兼容的模型。请检查您的模型配置或调整任务要求。")
            else:
                st.info(f"找到 **{len(compatible_models)}** 个兼容的模型。")

                for model in sorted(compatible_models,
                                    key=lambda m: (self.dm.calculate_task_cost(current_task, m) or {}).get('CNY',
                                                                                                           float('inf'))):
                    cost = self.dm.calculate_task_cost(current_task, model)

                    container = st.container(border=True)
                    c1, c2, c3 = container.columns([2, 3, 2])

                    c1.markdown(f"**模型名称**\n\n#### {model['name']}")
                    c1.markdown(f"**所属平台**: `{model['platform_name']}`")

                    with c2:
                        st.markdown("**模型能力**")
                        in_str = ", ".join(model.get('supported_inputs', []))
                        out_str = ", ".join(model.get('supported_outputs', []))
                        st.code(f"输入: {in_str}\n输出: {out_str}", language="text")

                        limits = model.get('rate_limits', {})
                        if limits:
                            limit_str = f"请求/分: {limits.get('rpm', 'N/A')} | Tokens/分: {limits.get('tpm', 'N/A')}"
                            st.markdown(f"**速率限制**: `{limit_str}`")

                    with c3:
                        if cost is not None:
                            st.metric(
                                label=f"执行 {current_task['count']} 次任务总花费 (CNY)",
                                value=f"¥ {cost['CNY']:.4f}"
                            )
                            st.caption(f"≈ $ {cost['USD']:.4f}")
                        else:
                            st.warning("无法计算成本，请检查该模型的定价规则是否覆盖了任务所需的所有格式。")
        else:
            st.info("请先在上方创建或选择一个任务以查看结果。")

    def render_settings_tab(self):
        """渲染平台和模型配置的标签页。"""
        st.header("配置AI聚合平台及其模型")

        if st.button("✚ 添加新平台"):
            new_platform = {
                "name": f"新平台-{len(self.dm.data['platforms']) + 1}",
                "limits": {"daily_free_requests": 0},
                "models": []
            }
            self.dm.data['platforms'].append(new_platform)
            st.rerun()

        for i, platform in enumerate(self.dm.data['platforms']):
            with st.expander(f"平台: {platform['name']}", expanded=False):
                with st.form(f"platform_form_{i}"):
                    platform['name'] = st.text_input("平台名称", value=platform['name'], key=f"p_name_{i}")
                    platform['limits']['daily_free_requests'] = st.number_input(
                        "每日免费模型总请求数限制",
                        min_value=0,
                        value=platform.get('limits', {}).get('daily_free_requests', 0),
                        key=f"p_limit_{i}"
                    )

                    st.markdown("---")
                    st.subheader("平台下的模型")

                    # 使用可编辑的数据帧来管理模型基本信息
                    edited_models = st.data_editor(
                        platform['models'],
                        num_rows="dynamic",
                        key=f"models_editor_{i}",
                        column_config={
                            "name": st.column_config.TextColumn("模型名称", required=True),
                            "supported_inputs": st.column_config.SelectboxColumn("支持的输入", options=INPUT_FORMATS,
                                                                                 required=True),
                            "supported_outputs": st.column_config.SelectboxColumn("支持的输出", options=OUTPUT_FORMATS,
                                                                                  required=True),
                            "pricing": st.column_config.ListColumn("定价规则 (详细配置)", help="请在下方模型详情中配置具体的定价规则"),
                            "rate_limits": st.column_config.Column("速率限制", help="请在下方模型详情中配置")
                        }
                    )
                    platform['models'] = edited_models

                    form_submitted, delete_platform = st.columns(2)
                    if form_submitted.form_submit_button("💾 保存平台和模型列表", use_container_width=True):
                        st.success(f"平台 '{platform['name']}' 信息已更新。")
                        st.rerun()

                    if delete_platform.form_submit_button("❌ 删除此平台", use_container_width=True):
                        self.dm.data['platforms'].pop(i)
                        st.rerun()

                # 为每个模型提供详细配置区域
                for j, model in enumerate(platform['models']):
                    with st.container(border=True):
                        st.markdown(f"##### 进一步配置模型: `{model.get('name', '未命名')}`")

                        # 初始化嵌套的字典/列表
                        if 'rate_limits' not in model or model['rate_limits'] is None:
                            model['rate_limits'] = {"rpm": 0, "tpm": 0}
                        if 'pricing' not in model or not isinstance(model['pricing'], list):
                            model['pricing'] = []

                        cols = st.columns(2)
                        model['rate_limits']['rpm'] = cols[0].number_input("请求/分钟 (RPM)", min_value=0,
                                                                           value=model['rate_limits'].get('rpm', 0),
                                                                           key=f"rpm_{i}_{j}")
                        model['rate_limits']['tpm'] = cols[1].number_input("Tokens/分钟 (TPM)", min_value=0,
                                                                           value=model['rate_limits'].get('tpm', 0),
                                                                           key=f"tpm_{i}_{j}")

                        st.markdown("###### 定价规则")

                        # 检查模型是否完全免费
                        is_free = st.checkbox("该模型完全免费", value=(model['pricing'] == 'free'), key=f"free_{i}_{j}")
                        if is_free:
                            model['pricing'] = 'free'
                        else:
                            # 如果之前是'free'，现在不是了，就重置为空列表
                            if model['pricing'] == 'free':
                                model['pricing'] = []

                            model['pricing'] = st.data_editor(
                                model['pricing'],
                                num_rows="dynamic",
                                key=f"pricing_editor_{i}_{j}",
                                column_config={
                                    "io_type": st.column_config.SelectboxColumn("类型", options=['input', 'output'],
                                                                                required=True),
                                    "format": st.column_config.SelectboxColumn("格式", options=INPUT_FORMATS,
                                                                               required=True),
                                    "method": st.column_config.SelectboxColumn("计价方式", options=PRICING_METHODS,
                                                                               required=True),
                                    "price": st.column_config.NumberColumn("价格", min_value=0.0, format="%.6f",
                                                                           required=True),
                                    "unit": st.column_config.NumberColumn("计价单位",
                                                                          help="例如: 按token计费时填1000000代表百万token; 按次计费时填1000代表千次",
                                                                          min_value=1, required=True),
                                    "currency": st.column_config.SelectboxColumn("货币", options=CURRENCIES,
                                                                                 required=True),
                                }
                            )


if __name__ == "__main__":
    # 在 Streamlit session state 中初始化 DataManager
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager(st.session_state)

    # 创建并运行 UI 管理器
    ui = UIManager(st.session_state.data_manager)
    ui.run()