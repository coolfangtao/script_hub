# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import copy
import json
import time


# ===================================================================
# CLASS 1: Config - 数据配置中心
# ===================================================================
class Config:
    """
    用于存储所有配置信息的数据类。
    """

    def __init__(self):
        # 初始化会话状态，用于动态添加/删除SKU和箱子
        if 'skus' not in st.session_state:
            st.session_state.skus = {
                '款式A': {'purchase_price': 10.0, 'quantity': 100, 'weight': 0.2}
            }
        if 'boxes' not in st.session_state:
            st.session_state.boxes = {
                '箱子1': {
                    'quantity': 1,
                    'items': {'款式A': 100},
                    'unit_price': 5.0,
                    'weight': 0.5,
                    'length': 50.0,
                    'width': 40.0,
                    'height': 40.0,
                    'other_costs': 0.0,
                    'shipping_price': 10.0,
                    'destination_code': 'ONT8'
                }
            }

        # ==================== 代码修改处 1/2 ====================
        # 将平台费用的字典也存入 session_state，以实现数据持久化
        if 'platform' not in st.session_state:
            st.session_state.platform = {
                'skus_platform_fees': {
                    '款式A': {'sell_price': 29.9, 'platform_fee': 8.0}
                },
                'fulfillment_fee': 0.0,
                'monthly_plan': 39.9,
                'other_costs': 0.0,
            }

        # 将所有配置项分组存放在字典中
        self.procurement = {
            'skus': st.session_state.skus,
            'discount_rate': 100.0,
            'shipping_fee': 0.0,
            'other_costs': 0.0,
        }
        self.packaging = {
            'boxes': st.session_state.boxes
        }
        self.shipping = {
            'min_chargeable_weight': 20.0,
            'volume_ratio': 6000,
            'other_costs': 0.0,
        }

        # 直接引用 session_state 中的 platform 对象
        self.platform = st.session_state.platform

        self.advertising = {
            'daily_spend': 12.0,
            'duration_days': 7,
        }
        self.finance = {
            'exchange_rate': 7.12,
            'withdrawal_fee_rate': 0.3,
        }

    def get_all_params(self):
        """将所有配置数据打包成一个字典用于导出。"""
        # 注意：这里的 self.platform 现在引用的是 session_state，所以会导出最新的数据
        params = {
            'procurement': copy.deepcopy(self.procurement),
            'packaging': copy.deepcopy(self.packaging),
            'shipping': copy.deepcopy(self.shipping),
            'platform': copy.deepcopy(self.platform),
            'advertising': copy.deepcopy(self.advertising),
            'finance': copy.deepcopy(self.finance),
        }
        return params

    def load_all_params(self, params: dict):
        """从字典加载配置数据，并更新session_state和自身属性。"""
        required_keys = ['procurement', 'packaging', 'shipping', 'platform', 'advertising', 'finance']
        if not all(key in params for key in required_keys):
            raise ValueError("导入的JSON文件格式不正确或缺少必要的配置项。")

        # 优先更新session_state，因为config对象依赖于它
        st.session_state.skus = params['procurement']['skus']
        st.session_state.boxes = params['packaging']['boxes']

        # ==================== 代码修改处 2/2 ====================
        # 导入时，必须更新 session_state 中的 platform 数据
        st.session_state.platform = params['platform']

        # 更新config对象
        self.procurement = params['procurement']
        self.packaging = params['packaging']
        self.shipping = params['shipping']
        self.platform = params['platform']
        self.advertising = params['advertising']
        self.finance = params['finance']


# ===================================================================
# CLASS 2: Calculator - 业务逻辑计算器
# ===================================================================
class Calculator:
    """
    负责所有业务逻辑的计算。
    """

    def __init__(self, config: Config):
        self.config = config
        self.results = {}

    def run_all_calculations(self):
        self.calc_procurement_cost()
        self.calc_packaging_cost()
        self.calc_shipping_cost()  # --- 运费计算逻辑已更新 ---
        self.calc_platform_cost_rmb()
        self.calc_advertising_cost_rmb()
        self.calc_total_cost()
        self.calc_total_revenue_rmb()
        self.calc_profit()
        self.calc_cost_breakdown()

    def calc_procurement_cost(self):
        cfg = self.config.procurement
        discount = cfg['discount_rate'] / 100.0

        per_sku_costs = {
            name: sku['purchase_price'] * sku['quantity']
            for name, sku in cfg['skus'].items()
        }
        item_costs = sum(per_sku_costs.values())
        discounted_item_costs = item_costs * discount
        total = discounted_item_costs + cfg['shipping_fee'] + cfg['other_costs']

        self.results['procurement_cost'] = total
        self.results['procurement_details'] = {
            "各SKU成本": per_sku_costs,
            "商品总成本": item_costs,
            "折扣后商品成本": discounted_item_costs,
            "采购运费": cfg['shipping_fee'],
            "采购其他费用": cfg['other_costs']
        }

    def calc_packaging_cost(self):
        per_box_costs = {
            name: box['unit_price'] * box['quantity'] + box['other_costs']
            for name, box in self.config.packaging['boxes'].items()
        }
        self.results['packaging_per_box'] = per_box_costs
        self.results['packaging_cost'] = sum(per_box_costs.values())

    def _get_chargeable_weight_details(self):
        """计算每个箱子类型的总实际重和总体积重（未考虑最低计费）"""
        details = {}
        for name, box in self.config.packaging['boxes'].items():
            # 计算箱内所有商品的总重量
            product_weight_total = sum(
                self.config.procurement['skus'][sku]['weight'] * qty for sku, qty in box['items'].items() if
                sku in self.config.procurement['skus']
            )
            # 计算此类型所有箱子的总实际重量
            actual_weight_total = (product_weight_total + box['weight'] * box['quantity'])

            # 计算此类型所有箱子的总体积重量
            volume_weight_total = (box['length'] * box['width'] * box['height']) / self.config.shipping[
                'volume_ratio'] * box['quantity']

            details[name] = {
                'actual_weight': actual_weight_total,
                'volume_weight': volume_weight_total,
                'chargeable_weight': max(actual_weight_total, volume_weight_total)
            }
        return details

    def calc_shipping_cost(self):
        """ --- 优化后的国际运费计算逻辑 (按箱应用最低计费) --- """
        weight_details = self._get_chargeable_weight_details()
        self.results['chargeable_weights'] = weight_details  # 存储基础计费重，用于UI展示

        min_weight_per_box = self.config.shipping['min_chargeable_weight']
        total_shipping_cost = 0
        per_box_final_costs = {}
        per_box_final_weights_details = {}

        for box_name, box_config in self.config.packaging['boxes'].items():
            if box_name in weight_details and box_config['quantity'] > 0:
                # 1. 计算单个箱子的基础计费重量 = MAX(单箱实际重, 单箱体积重)
                base_chargeable_weight_per_box = weight_details[box_name]['chargeable_weight'] / box_config['quantity']

                # 2. 确定单个箱子的最终计费重量 = MAX(基础计费重, 每箱最低计费重)
                final_chargeable_weight_per_box = max(base_chargeable_weight_per_box, min_weight_per_box)

                # 3. 计算此类型所有箱子的总运费
                price_per_kg = box_config['shipping_price']
                cost_for_this_box_type = final_chargeable_weight_per_box * box_config['quantity'] * price_per_kg

                # 4. 累加总费用并存储明细
                total_shipping_cost += cost_for_this_box_type
                per_box_final_costs[box_name] = cost_for_this_box_type
                per_box_final_weights_details[box_name] = {
                    'base_chargeable_weight_per_box': base_chargeable_weight_per_box,
                    'final_chargeable_weight_per_box': final_chargeable_weight_per_box,
                    'total_final_chargeable_weight': final_chargeable_weight_per_box * box_config['quantity']
                }

        # 5. 最后加上整票货的其它费用
        total_shipping_cost += self.config.shipping['other_costs']

        self.results['shipping_cost'] = total_shipping_cost
        self.results['shipping_details'] = {
            '各箱最终计费重量详情': per_box_final_weights_details,
            '各箱运费': per_box_final_costs,
            '货运其他费用': self.config.shipping['other_costs']
        }

    def calc_platform_cost_rmb(self):
        cfg_p = self.config.platform
        total_usd = 0
        for sku, details in cfg_p['skus_platform_fees'].items():
            if sku in self.config.procurement['skus']:
                total_usd += details['platform_fee'] * self.config.procurement['skus'][sku]['quantity']

        total_usd += cfg_p['fulfillment_fee'] + cfg_p['monthly_plan'] + cfg_p['other_costs']
        self.results['platform_fee_usd'] = total_usd
        self.results['platform_fee_rmb'] = total_usd * self.config.finance['exchange_rate']

    def calc_advertising_cost_rmb(self):
        cfg_a = self.config.advertising
        total_usd = cfg_a['daily_spend'] * cfg_a['duration_days']
        self.results['advertising_cost_usd'] = total_usd
        self.results['advertising_cost_rmb'] = total_usd * self.config.finance['exchange_rate']

    def calc_total_revenue_rmb(self):
        total_revenue_usd = 0
        for sku, d in self.config.platform['skus_platform_fees'].items():
            if sku in self.config.procurement['skus']:
                total_revenue_usd += d['sell_price'] * self.config.procurement['skus'][sku]['quantity']

        net_revenue_usd = total_revenue_usd * (1 - self.config.finance['withdrawal_fee_rate'] / 100.0)
        self.results['total_revenue_usd'] = total_revenue_usd
        self.results['net_revenue_rmb'] = net_revenue_usd * self.config.finance['exchange_rate']

    def calc_total_cost(self):
        self.results['total_cost_rmb'] = sum(self.results.get(cost_item, 0) for cost_item in
                                             ['procurement_cost', 'packaging_cost', 'shipping_cost', 'platform_fee_rmb',
                                              'advertising_cost_rmb']
                                             )

    def calc_profit(self):
        revenue = self.results.get('net_revenue_rmb', 0)
        cost = self.results.get('total_cost_rmb', 0)
        profit = revenue - cost
        self.results['profit_rmb'] = profit
        self.results['profit_margin'] = (profit / revenue * 100) if revenue != 0 else 0

    def calc_cost_breakdown(self):
        self.results['cost_breakdown'] = {
            '货物成本': self.results.get('procurement_cost', 0),
            '打包成本': self.results.get('packaging_cost', 0),
            '国际运费': self.results.get('shipping_cost', 0),
            '平台费用': self.results.get('platform_fee_rmb', 0),
            '广告费用': self.results.get('advertising_cost_rmb', 0),
        }


# ===================================================================
# CLASS 3: UI - 用户界面渲染器
# ===================================================================
class UI:
    """
    负责构建Streamlit用户界面。
    """

    def __init__(self, config: Config, calculator: Calculator):
        self.config = config
        self.calculator = calculator

    def run(self):
        st.set_page_config(layout="wide", page_title="亚马逊成本利润计算器", page_icon="📊")
        st.title("📊 亚马逊卖家成本利润计算器")

        # 运行计算
        self.calculator.run_all_calculations()

        # --- 在顶部显示核心结果 ---
        st.subheader("📈 核心数据一览")
        r = self.calculator.results
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("💰 总利润 (¥)", f"{r.get('profit_rmb', 0):,.2f}", f"{r.get('profit_margin', 0):.2f}% 利润率")
        res_col2.metric("💵 净收入 (¥)", f"{r.get('net_revenue_rmb', 0):,.2f}",
                        f"总销售额 ${r.get('total_revenue_usd', 0):,.2f}")
        res_col3.metric("🧾 总成本 (¥)", f"{r.get('total_cost_rmb', 0):,.2f}")
        res_col4.metric("📈 投资回报率 (ROI)", f"{r.get('profit_rmb', 0) / r.get('total_cost_rmb', 1):.2%}")

        tab1, tab2, tab3 = st.tabs(["⚙️ 参数配置", "🧮 计算过程", "📊 统计图表"])

        with tab1:
            self._display_config_tab()
        with tab2:
            self._display_formulas_tab()
        with tab3:
            self._display_stats_tab()

    def _display_config_tab(self):

        st.subheader("参数导入/导出", anchor=False, divider="rainbow")
        with st.container(border=True):
            # 1. Export Section
            try:
                json_data = json.dumps(
                    self.config.get_all_params(),
                    indent=4,
                    ensure_ascii=False
                )
                st.download_button(
                    label="📥 导出当前参数到本地",
                    data=json_data,
                    file_name="amazon_calculator_params.json",
                    mime="application/json",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"导出参数时出错: {e}")

            # 2. Import Section
            uploaded_file = st.file_uploader(
                "📤 从本地文件导入参数",
                type="json",
                accept_multiple_files=False,
            )
            st.warning("**注意**: 导入将覆盖当前所有配置，建议先导出备份。", icon="⚠️")

            # 3. Import Logic (runs when a file is uploaded)
            if uploaded_file is not None:
                try:
                    params = json.load(uploaded_file)
                    self.config.load_all_params(params)
                    st.success("参数已成功导入！页面将自动刷新。")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"导入失败: {e}")


        col1, col2, col3 = st.columns(3)
        with col1:
            self._display_procurement_config()
        with col2:
            self._display_packaging_config()
        with col3:
            self._display_shipping_config()
            self._display_platform_config()
            self._display_advertising_config()
            self._display_finance_config()

    def _display_procurement_config(self):
        with st.container(border=True):
            st.subheader("🛒 1. 采购成本", divider="rainbow")
            for name, details in list(st.session_state.skus.items()):
                with st.expander(f"SKU: {name}", expanded=True):
                    p_col1, p_col2, p_col3 = st.columns(3)
                    details['purchase_price'] = p_col1.number_input("采购单价(元)", key=f"price_{name}",
                                                                    value=details['purchase_price'], step=0.1,
                                                                    format="%.2f")
                    details['quantity'] = p_col2.number_input("采购数量(件)", key=f"qty_{name}", value=details['quantity'],
                                                              step=1, min_value=0)
                    details['weight'] = p_col3.number_input("单件重量(KG)", key=f"weight_{name}", value=details['weight'],
                                                            step=0.01, format="%.3f")

                    b_col1, b_col2 = st.columns(2)
                    if b_col1.button(f"🗑️ 删除 {name}", key=f"del_sku_{name}", use_container_width=True):
                        del st.session_state.skus[name]
                        if name in self.config.platform['skus_platform_fees']:
                            del self.config.platform['skus_platform_fees'][name]
                        st.rerun()

                    if b_col2.button(f"📋 复制 {name}", key=f"copy_sku_{name}", use_container_width=True):
                        new_name = f"款式{chr(ord('A') + len(st.session_state.skus))}"
                        st.session_state.skus[new_name] = copy.deepcopy(details)
                        platform_fees = self.config.platform['skus_platform_fees'].get(name, {'sell_price': 0.0,
                                                                                              'platform_fee': 0.0})
                        self.config.platform['skus_platform_fees'][new_name] = copy.deepcopy(platform_fees)
                        st.rerun()

            if st.button("➕ 新增SKU", use_container_width=True, type="primary"):
                new_name = f"款式{chr(ord('A') + len(st.session_state.skus))}"
                st.session_state.skus[new_name] = {'purchase_price': 0.0, 'quantity': 0, 'weight': 0.0}
                st.rerun()

            st.divider()
            self.config.procurement['discount_rate'] = st.number_input("折扣率 (%)",
                                                                       value=self.config.procurement['discount_rate'],
                                                                       step=1.0, format="%.2f")
            self.config.procurement['shipping_fee'] = st.number_input("采购运费 (元)",
                                                                      value=self.config.procurement['shipping_fee'])
            self.config.procurement['other_costs'] = st.number_input("采购其他费用 (元)",
                                                                     value=self.config.procurement['other_costs'])

    def _display_packaging_config(self):
        with st.container(border=True):
            st.subheader("📦 2. 打包与装箱", divider="rainbow")
            for name, details in list(st.session_state.boxes.items()):
                with st.expander(f"箱子: {name}", expanded=True):
                    box_col1, box_col2 = st.columns(2)
                    details['quantity'] = box_col1.number_input("纸箱数量(个)", key=f"box_qty_{name}",
                                                                value=details['quantity'], step=1)
                    details['unit_price'] = box_col2.number_input("纸箱单价(元)", key=f"box_price_{name}",
                                                                  value=details['unit_price'], format="%.2f")

                    st.markdown("**箱内物品**")
                    for sku in self.config.procurement['skus'].keys():
                        details['items'][sku] = st.number_input(f"{sku} 数量", key=f"item_qty_{name}_{sku}",
                                                                value=details['items'].get(sku, 0), step=1)

                    dim_col1, dim_col2, dim_col3 = st.columns(3)
                    details['length'] = dim_col1.number_input("长(cm)", key=f"len_{name}", value=details['length'])
                    details['width'] = dim_col2.number_input("宽(cm)", key=f"wid_{name}", value=details['width'])
                    details['height'] = dim_col3.number_input("高(cm)", key=f"hei_{name}", value=details['height'])
                    details['weight'] = st.number_input("空箱重量(KG)", key=f"box_weight_{name}", value=details['weight'],
                                                        format="%.2f")

                    details['other_costs'] = st.number_input(f"打包其他费用(元)", key=f"pack_other_{name}",
                                                             value=details['other_costs'], format="%.2f")

                    b_col1, b_col2 = st.columns(2)
                    if b_col1.button(f"🗑️ 删除 {name}", key=f"del_box_{name}", use_container_width=True):
                        del st.session_state.boxes[name]
                        st.rerun()
                    if b_col2.button(f"📋 复制 {name}", key=f"copy_box_{name}", use_container_width=True):
                        new_name = f"箱子{len(st.session_state.boxes) + 1}"
                        st.session_state.boxes[new_name] = copy.deepcopy(details)
                        st.rerun()

            if st.button("➕ 新增箱子", use_container_width=True, type="primary"):
                new_name = f"箱子{len(st.session_state.boxes) + 1}"
                st.session_state.boxes[new_name] = {'quantity': 1, 'items': {}, 'unit_price': 5.0, 'weight': 0.5,
                                                    'length': 50.0, 'width': 40.0, 'height': 40.0, 'other_costs': 0.0,
                                                    'shipping_price': 10.0, 'destination_code': 'ONT8'}
                st.rerun()

    def _display_shipping_config(self):
        with st.container(border=True):
            st.subheader("🚢 3. 国际货运成本", divider="rainbow")
            ship_col1, ship_col2 = st.columns(2)
            self.config.shipping['min_chargeable_weight'] = ship_col1.number_input("每箱最低计费重量(KG)",
                                                                                   value=self.config.shipping[
                                                                                       'min_chargeable_weight'])
            self.config.shipping['volume_ratio'] = ship_col2.number_input("体积比",
                                                                          value=self.config.shipping['volume_ratio'])

            st.divider()
            st.markdown("**各箱运费设置**")
            for name, details in list(self.config.packaging['boxes'].items()):
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    s_col1, s_col2 = st.columns(2)
                    details['shipping_price'] = s_col1.number_input("运费单价(元/KG)", key=f"ship_price_{name}",
                                                                    value=details.get('shipping_price', 10.0),
                                                                    format="%.2f")
                    details['destination_code'] = s_col2.text_input("目的仓库代码", key=f"dest_code_{name}",
                                                                    value=details.get('destination_code', 'ONT8'))

            st.divider()
            self.config.shipping['other_costs'] = st.number_input("货运其他费用(元)",
                                                                  value=self.config.shipping['other_costs'],
                                                                  format="%.2f")

    def _display_platform_config(self):
        with st.container(border=True):
            st.subheader("🌐 4. 平台费用", divider="rainbow")
            fees_cfg = self.config.platform['skus_platform_fees']
            for sku_name in self.config.procurement['skus'].keys():
                if sku_name not in fees_cfg: fees_cfg[sku_name] = {'sell_price': 0.0, 'platform_fee': 0.0}
                with st.expander(f"SKU 平台费: {sku_name}", expanded=True):
                    plat_col1, plat_col2 = st.columns(2)
                    fees_cfg[sku_name]['sell_price'] = plat_col1.number_input("销售价格($)", key=f"sell_price_{sku_name}",
                                                                              value=fees_cfg[sku_name]['sell_price'],
                                                                              format="%.2f")
                    fees_cfg[sku_name]['platform_fee'] = plat_col2.number_input("每件平台费($)", key=f"plat_fee_{sku_name}",
                                                                                value=fees_cfg[sku_name][
                                                                                    'platform_fee'], format="%.2f")
            st.divider()
            self.config.platform['fulfillment_fee'] = st.number_input("入库配置费($)",
                                                                      value=self.config.platform['fulfillment_fee'],
                                                                      format="%.2f")
            self.config.platform['monthly_plan'] = st.number_input("专业计划月租($/月)",
                                                                   value=self.config.platform['monthly_plan'],
                                                                   format="%.2f")
            self.config.platform['other_costs'] = st.number_input("平台其他费用($)",
                                                                  value=self.config.platform['other_costs'],
                                                                  format="%.2f")

    def _display_advertising_config(self):
        with st.container(border=True):
            st.subheader("📢 5. 广告费用", divider="rainbow")
            cfg = self.config.advertising
            cfg['daily_spend'] = st.number_input("日均广告花费($)", value=cfg['daily_spend'], format="%.2f")
            cfg['duration_days'] = st.number_input("广告持续天数(天)", value=cfg['duration_days'], step=1)

    def _display_finance_config(self):
        with st.container(border=True):
            st.subheader("🏦 6. 汇率和手续费", divider="rainbow")
            cfg = self.config.finance
            cfg['exchange_rate'] = st.number_input("汇率(美元兑人民币)", value=cfg['exchange_rate'], format="%.2f")
            cfg['withdrawal_fee_rate'] = st.number_input("提款手续费(%)", value=cfg['withdrawal_fee_rate'], format="%.2f")

    def _display_formulas_tab(self):
        st.header("🧮 计算过程详情")
        r = self.calculator.results

        with st.expander("💰 **总收入、成本与利润**", expanded=True):
            st.info("净收入(¥) = (Σ(SKU销售价格 × 数量) * (1 - 提款手续费率)) × 汇率")
            st.warning("总成本(¥) = 货物成本 + 打包成本 + 国际运费 + 平台费用 + 广告费用")
            st.success("总利润(¥) = 净收入(¥) - 总成本(¥)")
            st.info("利润率(%) = (总利润(¥) / 净收入(¥)) × 100")

            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.metric("💵 净收入 (¥)", f"{r.get('net_revenue_rmb', 0):,.2f}")
            f_col2.metric("🧾 总成本 (¥)", f"{r.get('total_cost_rmb', 0):,.2f}")
            f_col3.metric("💰 总利润 (¥)", f"{r.get('profit_rmb', 0):,.2f}", f"{r.get('profit_margin', 0):.2f}% 利润率")

        with st.expander("🛒 **货物成本 (¥)**", expanded=True):
            st.info("总货物成本 = (Σ(各SKU采购单价 × 数量) × 折扣率) + 采购运费 + 其他费用")
            proc_details = r.get('procurement_details', {})
            if proc_details.get("各SKU成本"):
                st.markdown("**各SKU成本明细:**")
                st.table(pd.DataFrame.from_dict(proc_details["各SKU成本"], orient='index', columns=['成本(元)']))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("折扣后商品成本", f"¥ {proc_details.get('折扣后商品成本', 0):.2f}", f"折扣前 ¥ {proc_details.get('商品总成本', 0):.2f}")
            c2.metric("采购运费", f"¥ {proc_details.get('采购运费', 0):.2f}")
            c3.metric("采购其他费用", f"¥ {proc_details.get('采购其他费用', 0):.2f}")
            c4.success(f"货物总成本: ¥ {r.get('procurement_cost', 0):.2f}")

        with st.expander("⚖️ **基础计费重量 (KG)**", expanded=True):
            st.info("单箱基础计费重量 = MAX((箱内商品总重 + 空箱重), (长×宽×高 / 体积比))")
            df_weights = pd.DataFrame(r.get('chargeable_weights', {})).T.rename(
                columns={'actual_weight': '总实际重量', 'volume_weight': '总体积重', 'chargeable_weight': '总基础计费重量'}
            )
            st.table(df_weights.style.format("{:.2f}"))

        with st.expander("🚢 **国际运费 (¥)**", expanded=True):
            st.info("总国际运费 = Σ(MAX(单箱基础计费重, 每箱最低计费重) × 箱数 × 单价) + 其他费用")
            shipping_details = r.get('shipping_details', {})
            if shipping_details.get("各箱最终计费重量详情"):
                st.markdown("**各箱计费重量明细:**")
                df_data = [{
                    "箱子名称": box_name,
                    "基础计费重量/个": data['base_chargeable_weight_per_box'],
                    "最终计费重量/个": data['final_chargeable_weight_per_box'],
                    "总最终计费重量": data['total_final_chargeable_weight']
                } for box_name, data in shipping_details["各箱最终计费重量详情"].items()]
                st.table(pd.DataFrame(df_data).set_index("箱子名称").style.format("{:.2f}"))

            c1, c2, c3 = st.columns(3)
            if shipping_details.get("各箱运费"):
                with c1:
                    st.markdown("**各箱运费:**")
                    st.table(pd.DataFrame.from_dict(shipping_details["各箱运费"], orient='index', columns=['运费(元)']))
            c2.metric("货运其他费用", f"¥ {shipping_details.get('货运其他费用', 0):.2f}")
            c3.success(f"总国际运费: ¥ {r.get('shipping_cost', 0):.2f}")

        with st.expander("📦 **打包成本 (¥)**", expanded=True):
            st.info("总打包成本 = Σ(纸箱单价 × 纸箱数量 + 单箱其他费用)")
            packaging_per_box = r.get('packaging_per_box', {})
            c1, c2 = st.columns(2)
            with c1:
                if packaging_per_box:
                    st.markdown("**各箱打包成本明细:**")
                    st.table(pd.DataFrame.from_dict(packaging_per_box, orient='index', columns=['打包成本(元)']))
            c2.success(f"总打包成本: ¥ {r.get('packaging_cost', 0):.2f}")

        col_p, col_a = st.columns(2)
        with col_p:
            with st.expander("🌐 **平台费用 (¥)**", expanded=True):
                st.info("平台费用(¥) = (Σ(每件平台费×数量) + 其他费用) × 汇率")
                st.metric("平台费用", f"¥ {r.get('platform_fee_rmb', 0):.2f}", f"等同 ${r.get('platform_fee_usd', 0):.2f}")
        with col_a:
            with st.expander("📢 **广告费用 (¥)**", expanded=True):
                st.info("广告费用(¥) = (日均花费 × 天数) × 汇率")
                st.metric("广告费用", f"¥ {r.get('advertising_cost_rmb', 0):.2f}",
                          f"等同 ${r.get('advertising_cost_usd', 0):.2f}")

    def _display_stats_tab(self):
        st.header("📊 成本构成分析")
        r = self.calculator.results

        cost_breakdown = r.get('cost_breakdown', {})
        filtered_costs = {k: v for k, v in cost_breakdown.items() if v > 0}

        if not filtered_costs:
            st.warning("所有成本项均为0，无法生成图表。")
        else:
            df = pd.DataFrame(list(filtered_costs.items()), columns=['成本项', '金额(¥)'])
            df = df.sort_values(by='金额(¥)', ascending=False)

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.subheader("成本构成占比 (饼图)")
                fig_pie = px.pie(df, values='金额(¥)', names='成本项', hole=0.3,
                                 title="各项成本占总成本的百分比")
                fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05] * len(df))
                st.plotly_chart(fig_pie, use_container_width=True)

            with chart_col2:
                st.subheader("成本构成金额 (条形图)")
                fig_bar = px.bar(df, x='成本项', y='金额(¥)', text_auto='.2s',
                                 title="各项成本的绝对金额对比")
                fig_bar.update_traces(texttemplate='%{value:,.2f} 元', textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)


# ===================================================================
# MAIN - 程序主入口
# ===================================================================
def main():
    config = Config()
    calculator = Calculator(config)
    ui = UI(config, calculator)
    ui.run()


if __name__ == "__main__":
    main()