import streamlit as st
import json
import copy
import pandas as pd  # 引入Pandas以修复表格编辑问题
from typing import List, Dict, Any, Optional

# 定义常量
INPUT_FORMATS = ['text', 'image', 'file', 'audio', 'video']
OUTPUT_FORMATS = ['text', 'image', 'file', 'audio', 'video']
PRICING_METHODS = ['per_token', 'per_call']
CURRENCIES = ['CNY', 'USD']


class DataManager:
    def __init__(self, state):
        self._state = state
        if 'data' not in self._state:
            self._state.data = self.get_default_data()

    @staticmethod
    def get_default_data() -> Dict[str, Any]:
        return {
            "tasks": [],
            "platforms": [],
            "settings": {"usd_to_cny_rate": 7.25}
        }

    @property
    def data(self) -> Dict[str, Any]:
        return self._state.data

    def load_data_from_json(self, uploaded_file) -> bool:
        try:
            new_data = json.load(uploaded_file)
            if "tasks" in new_data and "platforms" in new_data:
                self._state.data = new_data
                if "settings" not in self._state.data:
                    self._state.data["settings"] = self.get_default_data()["settings"]
                return True
            return False
        except Exception as e:
            st.error(f"JSON加载错误: {e}")
            return False

    def export_data_to_json(self) -> str:
        return json.dumps(self.data, indent=4, ensure_ascii=False)

    def find_compatible_models(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not task: return []
        compatible_models = []
        task_in = {i['format'] for i in task.get('inputs', [])}
        task_out = {i['format'] for i in task.get('outputs', [])}

        for platform in self.data.get('platforms', []):
            for model in platform.get('models', []):
                # 确保数据结构存在
                m_in = set(model.get('supported_inputs', []))
                m_out = set(model.get('supported_outputs', []))

                if m_in.issuperset(task_in) and m_out.issuperset(task_out):
                    m_copy = copy.deepcopy(model)
                    m_copy['platform_name'] = platform['name']
                    compatible_models.append(m_copy)
        return compatible_models

    def calculate_task_cost(self, task: Dict[str, Any], model: Dict[str, Any]) -> Optional[Dict[str, float]]:
        if not task or not model: return None

        # 免费模型处理
        pricing = model.get('pricing', [])
        if pricing == 'free' or (isinstance(pricing, list) and len(pricing) == 0 and model.get('is_free', False)):
            return {'CNY': 0.0, 'USD': 0.0}

        total_usd = 0.0
        count = task.get('count', 1000)
        rate = self.data['settings']['usd_to_cny_rate']

        # 遍历任务的所有输入输出组件
        for io_type in ['inputs', 'outputs']:
            for item in task.get(io_type, []):
                fmt = item['format']
                tokens = item.get('tokens', 0)

                # 查找匹配的定价规则
                matched_rule = None
                # model['pricing'] 应该是一个列表
                if isinstance(pricing, list):
                    for rule in pricing:
                        # 匹配 IO类型 (input/output) 和 格式 (text/image...)
                        # 注意：task里是 'inputs'/'outputs'，rule里是 'input'/'output'
                        if rule.get('io_type') == io_type[:-1] and rule.get('format') == fmt:
                            matched_rule = rule
                            break

                if not matched_rule:
                    return None  # 缺少必要的定价规则，无法计算

                price = matched_rule.get('price', 0)
                unit = matched_rule.get('unit', 1)
                method = matched_rule.get('method', 'per_token')
                currency = matched_rule.get('currency', 'USD')

                cost = 0
                if method == 'per_token':
                    cost = (tokens / unit) * price if unit > 0 else 0
                elif method == 'per_call':
                    cost = (1 / unit) * price if unit > 0 else 0

                if currency == 'CNY':
                    total_usd += cost / rate if rate > 0 else 0
                else:
                    total_usd += cost

        total_usd *= count
        return {'CNY': total_usd * rate, 'USD': total_usd}


class UIManager:
    def __init__(self, dm: DataManager):
        self.dm = dm
        if 'current_task_idx' not in st.session_state:
            st.session_state.current_task_idx = None

    def run(self):
        st.set_page_config(layout="wide", page_title="AI成本计算器")
        st.title("🤖 AI 模型成本可视化计算器")

        self.render_sidebar()
        tab1, tab2 = st.tabs(["📊 任务与结果", "⚙️ 平台与模型配置"])

        with tab1: self.render_task_tab()
        with tab2: self.render_config_tab()

    def render_sidebar(self):
        with st.sidebar:
            st.header("数据管理")
            st.download_button("📥 导出配置", self.dm.export_data_to_json(), "config.json", "application/json")
            f = st.file_uploader("📤 导入配置", type="json")
            if f and self.dm.load_data_from_json(f):
                st.success("导入成功")
                st.rerun()

            st.divider()
            st.header("汇率设置")
            self.dm.data['settings']['usd_to_cny_rate'] = st.number_input(
                "USD -> CNY", value=self.dm.data['settings']['usd_to_cny_rate'], step=0.01
            )

    def render_task_tab(self):
        tasks = self.dm.data['tasks']

        # --- 任务选择区域 ---
        c1, c2 = st.columns([3, 1])
        with c1:
            # 获取当前选项的索引，如果列表为空则处理
            options = [t['name'] for t in tasks]
            idx = st.session_state.current_task_idx
            # 修正索引越界问题
            if idx is not None and idx >= len(options):
                idx = 0 if options else None

            selected_name = st.selectbox(
                "选择任务", options,
                index=idx if (idx is not None and options) else 0,
                key="task_select"
            )
            # 更新 session state
            if selected_name:
                st.session_state.current_task_idx = options.index(selected_name)

        with c2:
            if st.button("➕ 新建任务", use_container_width=True):
                tasks.append({"name": f"任务-{len(tasks) + 1}", "count": 1000, "inputs": [], "outputs": []})
                st.session_state.current_task_idx = len(tasks) - 1
                st.rerun()

        if not tasks or st.session_state.current_task_idx is None:
            st.info("暂无任务，请先新建。")
            return

        curr_task = tasks[st.session_state.current_task_idx]

        # --- 任务编辑区域 ---
        with st.expander("✏️ 编辑当前任务", expanded=True):
            t_name = st.text_input("任务名称", curr_task['name'])
            t_count = st.number_input("任务总数", 1, value=curr_task['count'])

            c_in, c_out = st.columns(2)

            # Helper: 使用 Pandas DataFrame 确保空表格也有表头
            def get_editor_df(data_list):
                if not data_list:
                    return pd.DataFrame(columns=["format", "tokens"])
                return pd.DataFrame(data_list)

            with c_in:
                st.markdown("##### 输入 (Inputs)")
                df_in = get_editor_df(curr_task.get('inputs', []))
                edited_in = st.data_editor(
                    df_in, num_rows="dynamic", key="ed_in", use_container_width=True,
                    column_config={
                        "format": st.column_config.SelectboxColumn("格式", options=INPUT_FORMATS, required=True),
                        "tokens": st.column_config.NumberColumn("Token消耗", min_value=0, required=True)
                    }
                )

            with c_out:
                st.markdown("##### 输出 (Outputs)")
                df_out = get_editor_df(curr_task.get('outputs', []))
                edited_out = st.data_editor(
                    df_out, num_rows="dynamic", key="ed_out", use_container_width=True,
                    column_config={
                        "format": st.column_config.SelectboxColumn("格式", options=OUTPUT_FORMATS, required=True),
                        "tokens": st.column_config.NumberColumn("Token消耗", min_value=0, required=True)
                    }
                )

            # 保存与删除按钮
            btn_col1, btn_col2 = st.columns([1, 5])
            if btn_col1.button("💾 保存任务"):
                curr_task['name'] = t_name
                curr_task['count'] = t_count
                # 将 DataFrame 转回 List[Dict]
                curr_task['inputs'] = edited_in.to_dict('records')
                curr_task['outputs'] = edited_out.to_dict('records')
                st.success("已保存")
                st.rerun()  # 刷新以更新下拉框名称

            if btn_col2.button("🗑️ 删除任务", type="primary"):
                tasks.pop(st.session_state.current_task_idx)
                st.session_state.current_task_idx = None
                st.rerun()

        # --- 结果计算区域 ---
        st.divider()
        st.subheader("💰 成本计算结果")

        # 只有在已保存后（内存中有数据）才计算
        valid_inputs = [i for i in curr_task.get('inputs', []) if i.get('format')]
        valid_outputs = [i for i in curr_task.get('outputs', []) if i.get('format')]

        if not valid_inputs and not valid_outputs:
            st.warning("请先配置任务的输入或输出格式并保存。")
        else:
            compat_models = self.dm.find_compatible_models(curr_task)
            if not compat_models:
                st.error("没有找到支持该输入/输出组合的模型。请在'平台配置'中添加对应的模型。")
            else:
                results = []
                for m in compat_models:
                    cost = self.dm.calculate_task_cost(curr_task, m)
                    if cost:
                        results.append({
                            "model": m,
                            "cost": cost
                        })

                # 按价格排序
                results.sort(key=lambda x: x['cost']['CNY'])

                for res in results:
                    m = res['model']
                    c = res['cost']

                    with st.container(border=True):
                        col_main, col_cost = st.columns([3, 1])
                        with col_main:
                            st.markdown(f"**{m['name']}** <small style='color:gray'>({m['platform_name']})</small>",
                                        unsafe_allow_html=True)
                            st.caption(
                                f"Input: {', '.join(m['supported_inputs'])} | Output: {', '.join(m['supported_outputs'])}")
                        with col_cost:
                            st.markdown(f"#### ¥ {c['CNY']:,.2f}")
                            st.caption(f"$ {c['USD']:,.2f}")

    def render_config_tab(self):
        st.header("平台与模型管理")

        if st.button("➕ 添加新平台"):
            self.dm.data['platforms'].append({
                "name": "新平台", "limits": {"daily_limit": 0}, "models": []
            })
            st.rerun()

        platforms = self.dm.data['platforms']

        for p_idx, platform in enumerate(platforms):
            with st.expander(f"🏢 {platform['name']}", expanded=False):
                # 平台基本信息
                c1, c2, c3 = st.columns([2, 2, 1])
                new_p_name = c1.text_input("平台名称", platform['name'], key=f"p_name_{p_idx}")
                new_p_limit = c2.number_input("每日限制 (0为无限)", 0, value=platform.get('limits', {}).get('daily_limit', 0),
                                              key=f"p_lim_{p_idx}")

                if c3.button("❌ 删除平台", key=f"del_p_{p_idx}"):
                    platforms.pop(p_idx)
                    st.rerun()

                # 更新平台基本信息
                platform['name'] = new_p_name
                platform['limits'] = {"daily_limit": new_p_limit}

                st.divider()

                # --- 模型管理区域 (重构：不使用表格编辑复杂对象，改用列表+详情) ---
                st.markdown(f"**{len(platform['models'])} 个模型**")

                if st.button("✚ 添加模型", key=f"add_m_{p_idx}"):
                    platform['models'].append({
                        "name": "新模型",
                        "supported_inputs": ["text"],
                        "supported_outputs": ["text"],
                        "pricing": [],
                        "is_free": False
                    })
                    st.rerun()

                for m_idx, model in enumerate(platform['models']):
                    # 使用 container 区分每个模型
                    with st.container(border=True):
                        mc1, mc2 = st.columns([4, 1])
                        model['name'] = mc1.text_input("模型名称", model['name'], key=f"m_name_{p_idx}_{m_idx}")
                        if mc2.button("删除", key=f"del_m_{p_idx}_{m_idx}"):
                            platform['models'].pop(m_idx)
                            st.rerun()

                        # 输入输出多选 (解决了之前无法在表格里选多个的问题)
                        c_io1, c_io2 = st.columns(2)
                        model['supported_inputs'] = c_io1.multiselect(
                            "支持输入", INPUT_FORMATS, default=model.get('supported_inputs', []),
                            key=f"m_in_{p_idx}_{m_idx}"
                        )
                        model['supported_outputs'] = c_io2.multiselect(
                            "支持输出", OUTPUT_FORMATS, default=model.get('supported_outputs', []),
                            key=f"m_out_{p_idx}_{m_idx}"
                        )

                        # 速率限制
                        c_rl1, c_rl2 = st.columns(2)
                        limits = model.get('rate_limits', {})
                        limits['rpm'] = c_rl1.number_input("RPM (每分请求)", 0, value=limits.get('rpm', 0),
                                                           key=f"rpm_{p_idx}_{m_idx}")
                        limits['tpm'] = c_rl2.number_input("TPM (每分Token)", 0, value=limits.get('tpm', 0),
                                                           key=f"tpm_{p_idx}_{m_idx}")
                        model['rate_limits'] = limits

                        # 定价规则
                        st.markdown("**定价策略**")
                        is_free = st.checkbox("完全免费", value=model.get('is_free', False), key=f"free_{p_idx}_{m_idx}")
                        model['is_free'] = is_free

                        if not is_free:
                            # 使用 Pandas DataFrame 管理定价列表
                            pricing_data = model.get('pricing', [])
                            if not isinstance(pricing_data, list): pricing_data = []  # 防止旧数据错误

                            df_pricing = pd.DataFrame(pricing_data) if pricing_data else pd.DataFrame(
                                columns=['io_type', 'format', 'method', 'price', 'unit', 'currency'])

                            edited_pricing = st.data_editor(
                                df_pricing,
                                num_rows="dynamic",
                                key=f"pr_ed_{p_idx}_{m_idx}",
                                use_container_width=True,
                                column_config={
                                    "io_type": st.column_config.SelectboxColumn("类型", options=['input', 'output'],
                                                                                required=True),
                                    "format": st.column_config.SelectboxColumn("格式", options=INPUT_FORMATS,
                                                                               required=True),
                                    "method": st.column_config.SelectboxColumn("计价方式", options=PRICING_METHODS,
                                                                               required=True),
                                    "price": st.column_config.NumberColumn("价格", format="%.6f", required=True),
                                    "unit": st.column_config.NumberColumn("单位(如1k=1000)", min_value=1, required=True),
                                    "currency": st.column_config.SelectboxColumn("货币", options=CURRENCIES,
                                                                                 required=True)
                                }
                            )
                            # 实时写回数据
                            model['pricing'] = edited_pricing.to_dict('records')
                        else:
                            model['pricing'] = []


if __name__ == "__main__":
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager(st.session_state)
    UIManager(st.session_state.data_manager).run()