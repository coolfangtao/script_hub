# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import copy
import json
from shared.sidebar import create_common_sidebar


# ===================================================================
# CLASS 1: Config - 数据配置中心
# ===================================================================
class Config:
    """
    用于存储所有配置信息的数据类。
    重构后，此类不再保存状态副本，而是直接作为 st.session_state 的接口，
    确保数据源的唯一性。
    """

    def __init__(self):
        if 'params' not in st.session_state:
            st.session_state.params = {
                'procurement': {
                    'skus': {
                        '款式A': {'purchase_price': 10.0, 'quantity': 100, 'weight': 0.2}
                    },
                    'discount_rate': 100.0,
                    'shipping_fee': 0.0,
                    'other_costs': 0.0,
                },
                'packaging': {
                    'boxes': {
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
                },
                'shipping': {
                    'min_chargeable_weight': 20.0,
                    'volume_ratio': 6000,
                    'other_costs': 0.0,
                },
                'platform': {
                    'skus_platform_fees': {
                        '款式A': {'sell_price': 29.9, 'platform_fee': 8.0}
                    },
                    'fulfillment_fee': 0.0,
                    'monthly_plan': 39.9,
                    'other_costs': 0.0,
                },
                'advertising': {
                    'daily_spend': 12.0,
                    'duration_days': 7,
                },
                'finance': {
                    'exchange_rate': 7.12,
                    'withdrawal_fee_rate': 0.3,
                }
            }

        self.procurement = st.session_state.params['procurement']
        self.packaging = st.session_state.params['packaging']
        self.shipping = st.session_state.params['shipping']
        self.platform = st.session_state.params['platform']
        self.advertising = st.session_state.params['advertising']
        self.finance = st.session_state.params['finance']

        # 快捷方式，确保UI渲染逻辑能直接访问
        st.session_state.skus = self.procurement['skus']
        st.session_state.boxes = self.packaging['boxes']

    def get_all_params(self):
        """将所有配置数据打包成一个字典用于导出。"""
        return copy.deepcopy(st.session_state.params)


# ===================================================================
# CLASS 2: Calculator - 业务逻辑计算器
# ===================================================================
class Calculator:
    """
    负责所有业务逻辑的计算。 (此类无需修改)
    """

    def __init__(self, config: Config):
        self.config = config
        self.results = {}

    def run_all_calculations(self):
        self.calc_procurement_cost()
        self.calc_packaging_cost()
        self.calc_shipping_cost()
        self.calc_platform_cost_rmb()
        self.calc_advertising_cost_rmb()
        self.calc_total_cost()
        self.calc_total_revenue_rmb()
        self.calc_profit()
        self.calc_cost_breakdown()
        self.calc_per_sku_analysis()

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
        details = {}
        for name, box in self.config.packaging['boxes'].items():
            product_weight_total = sum(
                self.config.procurement['skus'][sku]['weight'] * qty for sku, qty in box['items'].items() if
                sku in self.config.procurement['skus']
            )
            actual_weight_total = (product_weight_total + box['weight'] * box['quantity'])
            volume_weight_total = (box['length'] * box['width'] * box['height']) / self.config.shipping[
                'volume_ratio'] * box['quantity']
            details[name] = {
                'actual_weight': actual_weight_total,
                'volume_weight': volume_weight_total,
                'chargeable_weight': max(actual_weight_total, volume_weight_total)
            }
        return details

    def calc_shipping_cost(self):
        weight_details = self._get_chargeable_weight_details()
        self.results['chargeable_weights'] = weight_details
        min_weight_per_box = self.config.shipping['min_chargeable_weight']
        total_shipping_cost = 0
        per_box_final_costs = {}
        per_box_final_weights_details = {}

        for box_name, box_config in self.config.packaging['boxes'].items():
            if box_name in weight_details and box_config['quantity'] > 0:
                base_chargeable_weight_per_box = weight_details[box_name]['chargeable_weight'] / box_config['quantity']
                final_chargeable_weight_per_box = max(base_chargeable_weight_per_box, min_weight_per_box)
                price_per_kg = box_config['shipping_price']
                cost_for_this_box_type = final_chargeable_weight_per_box * box_config['quantity'] * price_per_kg
                total_shipping_cost += cost_for_this_box_type
                per_box_final_costs[box_name] = cost_for_this_box_type
                per_box_final_weights_details[box_name] = {
                    'base_chargeable_weight_per_box': base_chargeable_weight_per_box,
                    'final_chargeable_weight_per_box': final_chargeable_weight_per_box,
                    'total_final_chargeable_weight': final_chargeable_weight_per_box * box_config['quantity']
                }
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

    def calc_per_sku_analysis(self):
        total_overhead_costs = (
                self.results['procurement_details'].get('采购运费', 0) +
                self.results['procurement_details'].get('采购其他费用', 0) +
                self.results.get('packaging_cost', 0) +
                self.results.get('shipping_cost', 0) +
                (
                        self.config.platform.get('fulfillment_fee', 0) +
                        self.config.platform.get('monthly_plan', 0) +
                        self.config.platform.get('other_costs', 0)
                ) * self.config.finance['exchange_rate'] +
                self.results.get('advertising_cost_rmb', 0)
        )
        all_skus = self.config.procurement['skus']
        total_items = sum(sku['quantity'] for sku in all_skus.values())
        overhead_cost_per_item = total_overhead_costs / total_items if total_items > 0 else 0
        analysis_results = {}
        for sku_name, sku_details in all_skus.items():
            quantity = sku_details.get('quantity', 0)
            if quantity == 0: continue
            sell_price_usd = self.config.platform['skus_platform_fees'].get(sku_name, {}).get('sell_price', 0)
            total_revenue_usd = sell_price_usd * quantity
            net_revenue_rmb = total_revenue_usd * (1 - self.config.finance['withdrawal_fee_rate'] / 100.0) * \
                              self.config.finance['exchange_rate']
            direct_procurement_cost = sku_details['purchase_price'] * quantity * (
                    self.config.procurement['discount_rate'] / 100.0)
            platform_fee_usd = self.config.platform['skus_platform_fees'].get(sku_name, {}).get('platform_fee', 0)
            direct_platform_fee_rmb = platform_fee_usd * quantity * self.config.finance['exchange_rate']
            allocated_overhead_rmb = overhead_cost_per_item * quantity
            total_cost_rmb = direct_procurement_cost + direct_platform_fee_rmb + allocated_overhead_rmb
            profit_rmb = net_revenue_rmb - total_cost_rmb
            margin = (profit_rmb / net_revenue_rmb * 100) if net_revenue_rmb != 0 else 0
            roi = (profit_rmb / total_cost_rmb * 100) if total_cost_rmb != 0 else 0
            analysis_results[sku_name] = {
                'SKU': sku_name, 'Quantity': quantity, 'Net Revenue (¥)': net_revenue_rmb,
                'Total Cost (¥)': total_cost_rmb, 'Profit (¥)': profit_rmb, 'Profit Margin (%)': margin,
                'ROI (%)': roi, 'Unit Revenue (¥)': net_revenue_rmb / quantity,
                'Unit Cost (¥)': total_cost_rmb / quantity, 'Unit Profit (¥)': profit_rmb / quantity
            }
        self.results['per_sku_analysis'] = analysis_results


# ===================================================================
# CLASS 3: UI - 用户界面渲染器 (Refactored for Simplicity and Robustness)
# ===================================================================
class UI:
    """
    负责构建Streamlit用户界面。
    该版本采用“状态重置”模式，在导入文件后清空并重新加载状态，
    从而避免了手动同步UI的复杂性，代码更简洁、健壮且易于维护。
    """

    def __init__(self, config: Config, calculator: Calculator):
        self.config = config
        self.calculator = calculator
        self.uploader_key = "params_uploader"

    def _handle_file_upload_and_reset(self):
        """
        [核心优化] 这是一个回调函数，在文件上传时触发。
        它通过清空整个session_state，然后仅恢复核心数据源，
        来强制所有UI组件在下一次渲染时从导入的JSON文件中获取其初始值。
        这消除了手动同步UI状态的需要。
        """
        uploaded_file = st.session_state.get(self.uploader_key)
        if uploaded_file is None:
            return

        try:
            # 1. 从上传的文件加载新数据
            new_params = json.load(uploaded_file)

            # 2. (推荐) 验证数据基本结构
            required_keys = ['procurement', 'packaging', 'shipping', 'platform', 'advertising', 'finance']
            if not all(key in new_params for key in required_keys):
                st.error("导入失败：JSON文件格式不正确或缺少必要的配置项。")
                return

            # 3. 【关键步骤】清空session_state，移除所有旧的UI组件状态
            st.session_state.clear()

            # 4. 【关键步骤】将新的数据源作为唯一状态放回session_state
            st.session_state.params = new_params
            st.success("参数已成功导入！页面已使用新配置刷新。")

        except Exception as e:
            st.error(f"导入失败，文件可能不是有效的JSON: {e}")

        # 回调函数结束后，Streamlit会自动rerun页面，所有UI组件将自然地使用新的数据

    def run(self):
        create_common_sidebar(current_label="📈 亚马逊利润统计")
        st.set_page_config(layout="wide", page_title="亚马逊成本利润计算器", page_icon="📊")
        st.title("📊 亚马逊卖家成本利润计算器")

        self.calculator.run_all_calculations()

        st.subheader("📈 核心数据一览")
        r = self.calculator.results
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("💰 总利润 (¥)", f"{r.get('profit_rmb', 0):,.2f}", f"{r.get('profit_margin', 0):.2f}% 利润率")
        res_col2.metric("💵 净收入 (¥)", f"{r.get('net_revenue_rmb', 0):,.2f}",
                        f"总销售额 ${r.get('total_revenue_usd', 0):,.2f}")
        res_col3.metric("🧾 总成本 (¥)", f"{r.get('total_cost_rmb', 0):,.2f}")
        res_col4.metric("📈 投资回报率 (ROI)", f"{r.get('profit_rmb', 0) / r.get('total_cost_rmb', 1):.2%}")

        tab1, tab2, tab3, tab4 = st.tabs(["⚙️ 费用配置", "🧮 计算过程", "📊 统计图表", "💡 使用说明"])

        with tab1:
            self._display_config_tab()
        with tab2:
            self._display_formulas_tab()
        with tab3:
            self._display_stats_tab()
        with tab4:
            self._display_instructions_tab()

    def _display_config_tab(self):
        st.subheader("参数导入/导出", anchor=False, divider="rainbow")
        with st.container(border=True):
            try:
                json_data = json.dumps(
                    self.config.get_all_params(), indent=4, ensure_ascii=False
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

            st.file_uploader(
                "📤 从本地文件导入参数",
                type="json",
                key=self.uploader_key,
                on_change=self._handle_file_upload_and_reset  # <-- 使用新的回调函数
            )
            st.warning("**注意**: 导入将覆盖当前所有配置，建议先导出备份。", icon="⚠️")

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

                    # 无需手动同步，UI组件直接从核心数据源(value=...)初始化
                    details['purchase_price'] = p_col1.number_input(
                        "采购单价(元)", key=f"price_{name}", value=details['purchase_price'],
                        step=0.1, format="%.2f"
                    )
                    details['quantity'] = p_col2.number_input(
                        "采购数量(件)", key=f"qty_{name}", value=details['quantity'],
                        step=1, min_value=0
                    )
                    details['weight'] = p_col3.number_input(
                        "单件重量(KG)", key=f"weight_{name}", value=details['weight'],
                        step=0.01, format="%.3f"
                    )

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
            self.config.shipping['min_chargeable_weight'] = ship_col1.number_input(
                "每箱最低计费重量(KG)", value=self.config.shipping['min_chargeable_weight']
            )
            self.config.shipping['volume_ratio'] = ship_col2.number_input(
                "体积比", value=self.config.shipping['volume_ratio']
            )

            st.divider()
            st.markdown("**各箱运费设置**")
            for name, details in list(self.config.packaging['boxes'].items()):
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    s_col1, s_col2 = st.columns(2)
                    details['shipping_price'] = s_col1.number_input(
                        "运费单价(元/KG)", key=f"ship_price_{name}", value=details.get('shipping_price', 10.0),
                        format="%.2f"
                    )
                    details['destination_code'] = s_col2.text_input(
                        "目的仓库代码", key=f"dest_code_{name}", value=details.get('destination_code', 'ONT8')
                    )

            st.divider()
            self.config.shipping['other_costs'] = st.number_input("货运其他费用(元)",
                                                                  value=self.config.shipping['other_costs'],
                                                                  format="%.2f")

    def _display_platform_config(self):
        with st.container(border=True):
            st.subheader("🌐 4. 平台费用", divider="rainbow")
            fees_cfg = self.config.platform['skus_platform_fees']
            for sku_name in self.config.procurement['skus'].keys():
                if sku_name not in fees_cfg:
                    fees_cfg[sku_name] = {'sell_price': 0.0, 'platform_fee': 0.0}
                with st.expander(f"SKU 平台费: {sku_name}", expanded=True):
                    plat_col1, plat_col2 = st.columns(2)
                    fees_cfg[sku_name]['sell_price'] = plat_col1.number_input(
                        "销售价格($)", key=f"sell_price_{sku_name}", value=fees_cfg[sku_name]['sell_price'],
                        format="%.2f"
                    )
                    fees_cfg[sku_name]['platform_fee'] = plat_col2.number_input(
                        "每件平台费($)", key=f"plat_fee_{sku_name}", value=fees_cfg[sku_name]['platform_fee'],
                        format="%.2f"
                    )
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
            cfg['withdrawal_fee_rate'] = st.number_input("提款手续费(%)", value=cfg['withdrawal_fee_rate'],
                                                         format="%.2f")

    def _display_formulas_tab(self):
        # (此方法无需修改)
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
                    "箱子名称": box_name, "基础计费重量/个": data['base_chargeable_weight_per_box'],
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
        # (此方法无需修改)
        st.header("📊 数据分析中心")
        r = self.calculator.results
        st.subheader("总成本构成", divider="rainbow")
        cost_breakdown = r.get('cost_breakdown', {})
        filtered_costs = {k: v for k, v in cost_breakdown.items() if v > 0}
        if not filtered_costs:
            st.warning("所有成本项均为0，无法生成成本构成图表。")
        else:
            df_cost = pd.DataFrame(list(filtered_costs.items()), columns=['成本项', '金额(¥)'])
            df_cost = df_cost.sort_values(by='金额(¥)', ascending=False)
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                fig_pie = px.pie(df_cost, values='金额(¥)', names='成本项', hole=0.3, title="各项成本占总成本的百分比")
                fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05] * len(df_cost))
                st.plotly_chart(fig_pie, use_container_width=True)
            with chart_col2:
                fig_bar = px.bar(df_cost, x='成本项', y='金额(¥)', text_auto='.2s', title="各项成本的绝对金额对比")
                fig_bar.update_traces(texttemplate='%{value:,.2f} 元', textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("SKU表现分析", divider="rainbow")
        sku_analysis_data = r.get('per_sku_analysis', {})
        if not sku_analysis_data:
            st.warning("没有可供分析的SKU数据。请在'费用配置'中添加SKU并设置其数量和价格。")
        else:
            df_sku = pd.DataFrame.from_dict(sku_analysis_data, orient='index')
            df_sku_profit = df_sku[df_sku['Profit (¥)'] != 0]
            sku_chart_col1, sku_chart_col2 = st.columns(2)
            with sku_chart_col1:
                df_revenue_positive = df_sku[df_sku['Net Revenue (¥)'] > 0]
                fig_sku_revenue = px.pie(df_revenue_positive, values='Net Revenue (¥)', names='SKU', hole=0.3,
                                         title="各SKU净收入贡献占比")
                fig_sku_revenue.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_sku_revenue, use_container_width=True)
            with sku_chart_col2:
                df_sku_profit['利润状态'] = df_sku_profit['Profit (¥)'].apply(lambda x: '盈利' if x > 0 else '亏损')
                fig_sku_profit = px.bar(df_sku_profit.sort_values(by='Profit (¥)', ascending=False),
                                        x='SKU', y='Profit (¥)', text_auto='.2s', title="各SKU利润对比", color='利润状态',
                                        color_discrete_map={'盈利': 'green', '亏损': 'red'})
                fig_sku_profit.update_traces(texttemplate='%{value:,.2f} 元', textposition='outside')
                st.plotly_chart(fig_sku_profit, use_container_width=True)
            st.subheader("📝 各SKU详细数据")
            st.info("点击列标题可以对表格进行排序，方便您发现表现最优和最差的SKU。")
            display_df = df_sku[
                ['Quantity', 'Net Revenue (¥)', 'Total Cost (¥)', 'Profit (¥)', 'Profit Margin (%)', 'ROI (%)',
                 'Unit Revenue (¥)', 'Unit Cost (¥)', 'Unit Profit (¥)']].copy()
            st.dataframe(display_df.style.format({
                'Net Revenue (¥)': "¥{:,.2f}", 'Total Cost (¥)': "¥{:,.2f}", 'Profit (¥)': "¥{:,.2f}",
                'Profit Margin (%)': "{:,.2f}%", 'ROI (%)': "{:,.2f}%", 'Unit Revenue (¥)': "¥{:,.2f}",
                'Unit Cost (¥)': "¥{:,.2f}", 'Unit Profit (¥)': "¥{:,.2f}",
            }).background_gradient(
                cmap='RdYlGn', subset=['Profit (¥)', 'Profit Margin (%)', 'ROI (%)', 'Unit Profit (¥)']
            ), use_container_width=True)

    def _display_instructions_tab(self):
        # (此方法无需修改)
        st.header("💡 使用说明与注意事项")
        st.markdown("""
        欢迎使用亚马逊成本利润计算器！本工具旨在帮助亚马逊卖家精确估算一票货物的总成本、预期利润及各项费用明细。为了获得最准确的结果，请仔细阅读以下说明。
        """)
        st.subheader("🚀 快速上手指南")
        st.markdown("""
        计算器的核心操作流程非常简单，主要集中在 **"⚙️ 费用配置"** 选项卡中。请按照从左到右，从上到下的顺序依次填写所有相关参数。

        **1. 填写采购成本 (第1列)**
        - **SKU管理**: 点击 "➕ 新增SKU" 来添加新的产品款式。您可以为每个SKU设置采购单价、数量和单件重量。
        - **删除与复制**: 每个SKU卡片下方都有删除和复制按钮，方便您快速管理。
        - **公共费用**: 在SKU列表下方，填写适用于所有采购商品的折扣率、运费等。

        **2. 配置打包与装箱 (第2列)**
        - **箱子管理**: 与SKU类似，您可以新增、删除和复制箱子配置。
        - **装箱信息**: 对于每个箱子，请指定该类型箱子的总数量，并填入每个箱子中包含的各个SKU的数量。
        - **物理属性**: 准确填写纸箱的尺寸（长宽高）、空箱重量和单价。这些参数对计算运费至关重要。

        **3. 填写其他费用 (第3列)**
        - **国际货运**: 设定体积重计算标准（体积比）和 *每箱* 的最低计费重量。这是计算运费的关键。同时，为每个箱子类型设置其对应的运费单价（元/KG）。
        - **平台费用**: 填写每个SKU的预期销售价格和平台抽成（均以美元计价）。
        - **广告与财务**: 设定广告预算、汇率和提款手续费。

        **4. 查看结果**
        - 所有参数输入后，顶部的 **"📈 核心数据一览"** 会实时更新，显示总利润、净收入等关键指标。
        - **"🧮 计算过程"** 选项卡会详细展示每个成本项是如何计算出来的，方便您核对。
        - **"📊 统计图表"** 选项卡则将成本构成可视化，让您对成本分布一目了然。
        """)
        st.subheader("💾 参数的导入与导出")
        st.markdown("""
        - **导出**: 当您完成一次完整的参数配置后，可以点击 **"📥 导出当前参数到本地"** 按钮。这会将所有配置保存为一个 `.json` 文件。这个功能非常适合用于备份、存档或与团队成员分享。
        - **导入**: 如果您有一个之前导出的 `.json` 文件，可以通过 **"📤 从本地文件导入参数"** 上传它。上传成功后，页面会自动刷新，并将所有配置更新为文件中的数据。
        - **⚠️ 注意**: 导入操作会 **覆盖** 页面上所有当前的配置，请在导入前确认是否已保存好当前数据。
        """)
        st.subheader("📝 注意事项")
        st.markdown("""
        - **单位一致性**: 请特别注意每个输入框后面的单位提示（例如 `元` vs `$`，`KG` vs `cm`）。错误的单位将导致计算结果严重偏差。
        - **实时计算**: 页面上的所有计算都是实时触发的。每当您修改任何一个数字，整个计算链条都会自动重新运行。
        - **计费重量逻辑**: 国际运费的计算逻辑是：
            1. 计算出单个箱子的 `实际重量` 和 `体积重量`。
            2. 取两者中的较大值，得到 `单箱基础计费重`。
            3. 再将 `单箱基础计费重` 与您设定的 `每箱最低计费重量` 比较，取较大值作为 `最终单箱计费重`。
            4. `总运费 = Σ (最终单箱计费重 × 该类型箱子总数 × 运费单价)`。
        - **数据持久化**: 您的所有输入都保存在当前浏览器会话中。刷新页面不会丢失数据，但关闭浏览器标签页后数据会丢失。请善用导出功能来持久化保存您的工作。
        """)
        st.success("现在，您可以开始在 **“⚙️ 参数配置”** 选项卡中输入您的数据了！祝您使用愉快！")


# ===================================================================
# MAIN - 程序主入口
# ===================================================================
def main():
    # 实例化核心类
    config = Config()
    calculator = Calculator(config)
    ui = UI(config, calculator)
    # 运行UI
    ui.run()


if __name__ == "__main__":
    main()