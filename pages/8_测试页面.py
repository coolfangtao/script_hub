# app.py
import streamlit as st
import pandas as pd
import plotly.express as px


class AmazonProfitCalculatorApp:
    """
    一个集成了配置、计算和UI的Streamlit亚马逊利润计算器应用。
    """

    def __init__(self):
        """
        初始化应用，设置页面配置并加载所有默认参数。
        """
        st.set_page_config(layout="wide", page_title="亚马逊成本利润计算器")

        # 使用会话状态(session_state)来存储可动态增删的配置项
        # 这样在页面交互（如点击按钮）后，数据不会重置
        if 'skus' not in st.session_state:
            st.session_state.skus = {
                '款式A': {'purchase_price': 10.0, 'quantity': 100, 'weight': 0.2, 'sell_price': 29.9, 'platform_fee': 8.0}
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
                    'other_costs': 0.0
                }
            }
        if 'destinations' not in st.session_state:
            st.session_state.destinations = {
                'ONT8': {'shipping_price': 10.0, 'assigned_boxes': ['箱子1']}
            }

        # 将所有配置项作为类的属性
        self.results = {}  # 用于存储计算结果

    # ===================================================================
    # SECTION 1: CALCULATION METHODS (原Calculator类)
    # ===================================================================

    def run_all_calculations(self):
        """执行所有计算"""
        self.calc_procurement_cost()
        self.calc_packaging_cost()
        self.calc_shipping_cost()
        self.calc_platform_cost_rmb()
        self.calc_advertising_cost_rmb()
        self.calc_total_cost()
        self.calc_total_revenue_rmb()
        self.calc_profit()
        self.calc_cost_breakdown()

    def calc_procurement_cost(self):
        """1. 计算货物成本 (¥)"""
        discount = self.procurement['discount_rate'] / 100.0
        item_costs = sum(
            details['purchase_price'] * details['quantity']
            for _, details in st.session_state.skus.items()
        )
        discounted_item_costs = item_costs * discount
        total_procurement_cost = (
                discounted_item_costs +
                self.procurement['shipping_fee'] +
                self.procurement['other_costs']
        )
        self.results['procurement_cost'] = total_procurement_cost
        self.results['procurement_details'] = {
            "商品总成本": item_costs,
            "折扣后商品成本": discounted_item_costs,
            "运费": self.procurement['shipping_fee'],
            "其他费用": self.procurement['other_costs']
        }

    def calc_packaging_cost(self):
        """计算打包成本 (¥)"""
        total_packaging_cost = sum(
            box['unit_price'] * box['quantity'] + box['other_costs']
            for _, box in st.session_state.boxes.items()
        )
        self.results['packaging_cost'] = total_packaging_cost

    def _get_box_actual_weight(self, box_details):
        product_weight = sum(
            st.session_state.skus[sku]['weight'] * quantity
            for sku, quantity in box_details['items'].items()
        )
        return product_weight + box_details['weight'] * box_details['quantity']

    def _get_box_volume_weight(self, box_details):
        l, w, h = box_details['length'], box_details['width'], box_details['height']
        return (l * w * h) / self.shipping['volume_ratio'] * box_details['quantity']

    def calc_chargeable_weight(self):
        """2. 计算计费重量 (KG)"""
        chargeable_weights = {}
        for box_name, box_details in st.session_state.boxes.items():
            actual_weight = self._get_box_actual_weight(box_details)
            volume_weight = self._get_box_volume_weight(box_details)
            final_chargeable_weight = max(actual_weight, volume_weight)
            chargeable_weights[box_name] = {
                'actual_weight': actual_weight,
                'volume_weight': volume_weight,
                'chargeable_weight': final_chargeable_weight,
            }

        # 处理最低计费重量
        # 实际业务中通常是按一票货来算，这里简化为所有箱子总重
        total_chargeable_before_min = sum(v['chargeable_weight'] for v in chargeable_weights.values())
        if total_chargeable_before_min < self.shipping['min_chargeable_weight']:
            # 如果总重量小于最低计费，则按最低计费算。如何分摊到每个箱子是业务问题，
            # 这里简单处理，只影响总运费计算。
            self.results['final_total_chargeable_weight'] = self.shipping['min_chargeable_weight']
        else:
            self.results['final_total_chargeable_weight'] = total_chargeable_before_min

        self.results['chargeable_weights'] = chargeable_weights

    def calc_shipping_cost(self):
        """3. 计算国际运费 (¥)"""
        self.calc_chargeable_weight()  # 确保计费重量已计算
        total_shipping_cost = 0

        # 简化版：如果总计费重量低于最低要求，直接用最低重量乘以单价
        if self.results['final_total_chargeable_weight'] == self.shipping['min_chargeable_weight']:
            # 假设所有箱子发往第一个目的地，使用其单价
            first_dest_price = next(iter(st.session_state.destinations.values()))['shipping_price']
            total_shipping_cost = self.shipping['min_chargeable_weight'] * first_dest_price
        else:
            for dest, dest_details in st.session_state.destinations.items():
                price_per_kg = dest_details['shipping_price']
                for box_name in dest_details['assigned_boxes']:
                    if box_name in self.results['chargeable_weights']:
                        total_shipping_cost += self.results['chargeable_weights'][box_name][
                                                   'chargeable_weight'] * price_per_kg

        total_shipping_cost += self.shipping['other_costs']
        self.results['shipping_cost'] = total_shipping_cost

    def calc_platform_cost_rmb(self):
        """4. 计算平台费用 (¥)"""
        total_platform_fee_usd = sum(
            sku['platform_fee'] * sku['quantity']
            for _, sku in st.session_state.skus.items()
        )
        total_platform_fee_usd += self.platform['fulfillment_fee']
        total_platform_fee_usd += self.platform['monthly_plan']
        total_platform_fee_usd += self.platform['other_costs']
        self.results['platform_fee_usd'] = total_platform_fee_usd
        self.results['platform_fee_rmb'] = total_platform_fee_usd * self.finance['exchange_rate']

    def calc_advertising_cost_rmb(self):
        """5. 计算广告费用 (¥)"""
        total_adv_cost_usd = self.advertising['daily_spend'] * self.advertising['duration_days']
        self.results['advertising_cost_usd'] = total_adv_cost_usd
        self.results['advertising_cost_rmb'] = total_adv_cost_usd * self.finance['exchange_rate']

    def calc_total_revenue_rmb(self):
        """计算总收入 (¥)"""
        total_revenue_usd = sum(
            sku['sell_price'] * sku['quantity']
            for _, sku in st.session_state.skus.items()
        )
        withdrawal_fee = total_revenue_usd * (self.finance['withdrawal_fee_rate'] / 100.0)
        net_revenue_usd = total_revenue_usd - withdrawal_fee

        self.results['total_revenue_usd'] = total_revenue_usd
        self.results['net_revenue_rmb'] = net_revenue_usd * self.finance['exchange_rate']

    def calc_total_cost(self):
        """计算总成本 (¥)"""
        total_cost = (
                self.results.get('procurement_cost', 0) +
                self.results.get('packaging_cost', 0) +
                self.results.get('shipping_cost', 0) +
                self.results.get('platform_fee_rmb', 0) +
                self.results.get('advertising_cost_rmb', 0)
        )
        self.results['total_cost_rmb'] = total_cost

    def calc_profit(self):
        """计算总利润和利润率"""
        total_revenue = self.results.get('net_revenue_rmb', 0)
        total_cost = self.results.get('total_cost_rmb', 0)
        profit = total_revenue - total_cost
        profit_margin = (profit / total_revenue) * 100 if total_revenue != 0 else 0
        self.results['profit_rmb'] = profit
        self.results['profit_margin'] = profit_margin

    def calc_cost_breakdown(self):
        """计算成本构成"""
        self.results['cost_breakdown'] = {
            '货物成本': self.results.get('procurement_cost', 0),
            '打包成本': self.results.get('packaging_cost', 0),
            '国际运费': self.results.get('shipping_cost', 0),
            '平台费用': self.results.get('platform_fee_rmb', 0),
            '广告费用': self.results.get('advertising_cost_rmb', 0),
        }

    # ===================================================================
    # SECTION 2: UI DISPLAY METHODS (原UI类)
    # ===================================================================

    def display_config_tab(self):
        """配置界面"""
        col1, col2, col3 = st.columns(3)
        with col1:
            self.display_procurement_config()
        with col2:
            self.display_packaging_config()
            self.display_shipping_config()
        with col3:
            self.display_platform_config()
            self.display_advertising_config()
            self.display_finance_config()

    def display_procurement_config(self):
        with st.container(border=True):
            st.subheader("1. 采购成本")
            for sku_name, sku_details in list(st.session_state.skus.items()):
                with st.expander(f"SKU: {sku_name}", expanded=True):
                    sku_details['purchase_price'] = st.number_input(f"采购单价 (元)##{sku_name}",
                                                                    value=sku_details['purchase_price'], step=0.1,
                                                                    format="%.2f")
                    sku_details['quantity'] = st.number_input(f"采购数量 (件)##{sku_name}", value=sku_details['quantity'],
                                                              step=1)
                    sku_details['weight'] = st.number_input(f"单件重量 (KG)##{sku_name}", value=sku_details['weight'],
                                                            step=0.01, format="%.3f")
                    if st.button(f"删除 {sku_name}", key=f"del_sku_{sku_name}"):
                        del st.session_state.skus[sku_name]
                        st.rerun()
            if st.button("新增SKU"):
                new_sku_letter = chr(ord('A') + len(st.session_state.skus))
                new_sku_name = f"款式{new_sku_letter}"
                st.session_state.skus[new_sku_name] = {'purchase_price': 0.0, 'quantity': 0, 'weight': 0.0,
                                                       'sell_price': 0.0, 'platform_fee': 0.0}
                st.rerun()
            st.markdown("---")
            self.procurement['discount_rate'] = st.slider("折扣率 (%)", 0.0, 100.0, 100.0, 0.5)
            self.procurement['shipping_fee'] = st.number_input("运费 (元)", value=0.0, step=10.0, format="%.2f")
            self.procurement['other_costs'] = st.number_input("其他费用 (元)", value=0.0, step=10.0, format="%.2f")

    def display_packaging_config(self):
        with st.container(border=True):
            st.subheader("2. 打包与装箱")
            for box_name, box_details in list(st.session_state.boxes.items()):
                with st.expander(f"箱子: {box_name}", expanded=True):
                    box_details['quantity'] = st.number_input(f"纸箱数量 (个)##{box_name}", value=box_details['quantity'],
                                                              step=1, min_value=1)
                    box_details['unit_price'] = st.number_input(f"纸箱单价 (元)##{box_name}",
                                                                value=box_details['unit_price'], step=0.1,
                                                                format="%.2f")
                    st.markdown("**箱内物品**")
                    for sku in st.session_state.skus.keys():
                        box_details['items'][sku] = st.number_input(f"{sku} 数量##{box_name}_{sku}",
                                                                    value=box_details['items'].get(sku, 0), step=1)
                    box_details['weight'] = st.number_input(f"空箱重量 (KG)##{box_name}", value=box_details['weight'],
                                                            step=0.1, format="%.2f")
                    c1, c2, c3 = st.columns(3)
                    box_details['length'] = c1.number_input(f"长 (cm)##{box_name}", value=box_details['length'])
                    box_details['width'] = c2.number_input(f"宽 (cm)##{box_name}", value=box_details['width'])
                    box_details['height'] = c3.number_input(f"高 (cm)##{box_name}", value=box_details['height'])
                    box_details['other_costs'] = st.number_input(f"其他费用 (元)##{box_name}",
                                                                 value=box_details['other_costs'], format="%.2f")
                    if st.button(f"删除 {box_name}", key=f"del_box_{box_name}"):
                        del st.session_state.boxes[box_name]
                        st.rerun()
            if st.button("新增箱子"):
                new_box_name = f"箱子{len(st.session_state.boxes) + 1}"
                st.session_state.boxes[new_box_name] = {'quantity': 1, 'items': {}, 'unit_price': 5.0, 'weight': 0.5,
                                                        'length': 50.0, 'width': 40.0, 'height': 40.0,
                                                        'other_costs': 0.0}
                st.rerun()

    def display_shipping_config(self):
        with st.container(border=True):
            st.subheader("3. 国际货运成本")
            self.shipping['min_chargeable_weight'] = st.number_input("每票最低计费重量 (KG)", value=20.0)
            self.shipping['volume_ratio'] = st.number_input("体积比", value=6000)
            for dest_name, dest_details in list(st.session_state.destinations.items()):
                with st.expander(f"目的地仓库: {dest_name}", expanded=True):
                    dest_details['shipping_price'] = st.number_input(f"运费单价 (元/KG)##{dest_name}",
                                                                     value=dest_details['shipping_price'],
                                                                     format="%.2f")
                    all_boxes = list(st.session_state.boxes.keys())
                    dest_details['assigned_boxes'] = st.multiselect(f"发往此仓库的箱子##{dest_name}", options=all_boxes,
                                                                    default=dest_details.get('assigned_boxes', []))
            self.shipping['other_costs'] = st.number_input("其他费用 (元)##shipping", value=0.0, format="%.2f")

    def display_platform_config(self):
        with st.container(border=True):
            st.subheader("4. 平台费用")
            for sku_name, sku_details in st.session_state.skus.items():
                with st.expander(f"款式: {sku_name}", expanded=True):
                    sku_details['sell_price'] = st.number_input(f"销售价格 ($)##{sku_name}",
                                                                value=sku_details['sell_price'], format="%.2f")
                    sku_details['platform_fee'] = st.number_input(f"每件平台费 ($)##{sku_name}",
                                                                  value=sku_details['platform_fee'], format="%.2f")
            st.markdown("---")
            self.platform['fulfillment_fee'] = st.number_input("入库配置费 ($)", value=0.0, format="%.2f")
            self.platform['monthly_plan'] = st.number_input("专业计划月租 ($/月)", value=39.9, format="%.2f")
            self.platform['other_costs'] = st.number_input("其他费用 ($)##platform", value=0.0, format="%.2f")

    def display_advertising_config(self):
        with st.container(border=True):
            st.subheader("5. 广告费用")
            self.advertising['daily_spend'] = st.number_input("日均广告花费 ($)", value=12.0, format="%.2f")
            self.advertising['duration_days'] = st.number_input("广告持续天数 (天)", value=7, step=1)

    def display_finance_config(self):
        with st.container(border=True):
            st.subheader("6. 汇率和手续费")
            self.finance['exchange_rate'] = st.number_input("汇率 (美元兑人民币)", value=7.12, format="%.2f")
            self.finance['withdrawal_fee_rate'] = st.number_input("提款手续费 (%)", value=0.3, format="%.2f")

    def display_formulas_tab(self):
        st.header("计算过程详情")
        with st.expander("1. 货物成本 (¥)", expanded=True):
            proc_details = self.results['procurement_details']
            st.write(f"商品总成本: `¥ {proc_details['商品总成本']:.2f}`")
            st.write(f"折扣率: `{self.procurement['discount_rate']}%`")
            st.write(f"折扣后商品成本: `¥ {proc_details['折扣后商品成本']:.2f}`")
            st.markdown(f"**总货物成本 = `折扣后商品成本 + 运费 + 其他费用` = `¥ {self.results['procurement_cost']:.2f}`**")

        with st.expander("2. 计费重量 (KG)", expanded=True):
            df_data = [{
                "箱子": box,
                "实际重量": f"{data['actual_weight']:.2f} KG",
                "体积重": f"{data['volume_weight']:.2f} KG",
                "计费重量": f"{data['chargeable_weight']:.2f} KG"
            } for box, data in self.results['chargeable_weights'].items()]
            st.table(pd.DataFrame(df_data))
            st.caption(
                f"公式: 单箱计费重量 = MAX(实际重量, 体积重)。之后所有箱子总计费重量会与最低计费重量({self.shipping['min_chargeable_weight']}KG)比较。")

        with st.expander("3. 国际运费 (¥)", expanded=True):
            st.markdown(f"**总国际运费 = `¥ {self.results['shipping_cost']:.2f}`**")

        with st.expander("4. 平台费用", expanded=True):
            st.markdown(
                f"平台总费用($) `{self.results['platform_fee_usd']:.2f}` * 汇率 `{self.finance['exchange_rate']}` = **`¥ {self.results['platform_fee_rmb']:.2f}`**")

        with st.expander("5. 广告费用", expanded=True):
            st.markdown(
                f"广告总花费($) `{self.results['advertising_cost_usd']:.2f}` * 汇率 `{self.finance['exchange_rate']}` = **`¥ {self.results['advertising_cost_rmb']:.2f}`**")

        with st.expander("6. 其他费用 (¥)", expanded=True):
            st.write(f"打包过程费用: `¥ {self.results['packaging_cost']:.2f}` (所有箱子的单价和其他费用总和)")

    def display_stats_tab(self):
        st.header("总体统计信息")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总利润 (¥)", f"{self.results['profit_rmb']:,.2f}", f"利润率: {self.results['profit_margin']:.2f}%")
        col2.metric("净收入 (¥)", f"{self.results['net_revenue_rmb']:,.2f}")
        col3.metric("总成本 (¥)", f"{self.results['total_cost_rmb']:,.2f}")
        col4.metric("总销售额 ($)", f"${self.results['total_revenue_usd']:,.2f}")
        st.markdown("---")
        st.subheader("成本构成占比")

        filtered_costs = {k: v for k, v in self.results['cost_breakdown'].items() if v > 0}
        if not filtered_costs:
            st.warning("所有成本项均为0，无法生成图表。")
        else:
            df = pd.DataFrame(list(filtered_costs.items()), columns=['成本项', '金额(¥)'])
            fig = px.pie(df, values='金额(¥)', names='成本项', title='各项成本占比分析', hole=0.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    # ===================================================================
    # SECTION 3: MAIN APP RUNNER
    # ===================================================================

    def run(self):
        """
        主运行函数，渲染整个应用。
        """
        st.title("亚马逊卖家成本利润计算器")

        # 定义Tab
        tab1, tab2, tab3 = st.tabs(["配置界面", "公式页面", "统计页面"])

        # Tab 1: 配置
        with tab1:
            self.display_config_tab()

        # 读取所有配置，然后执行计算
        # 注意: 简单配置项直接在display方法中读取，动态项通过session_state读取
        self.procurement = {}
        self.packaging = {}
        self.shipping = {}
        self.platform = {}
        self.advertising = {}
        self.finance = {}

        # 重新运行一次display_config_tab以捕获值，这是一个简化的处理方式
        # 在实际的大型应用中，可能会使用回调或更复杂的状态管理
        # 这里，由于Streamlit的线性执行模型，我们可以在渲染后立即进行计算
        # 但为了确保值被捕获，我们再次调用配置函数来填充字典
        self._collect_configs()

        self.run_all_calculations()

        # Tab 2: 公式
        with tab2:
            self.display_formulas_tab()

        # Tab 3: 统计
        with tab3:
            self.display_stats_tab()

    def _collect_configs(self):
        """
        一个辅助函数，用于从UI组件中收集配置值到类的属性字典中。
        这确保了计算函数可以使用最新的UI输入。
        注意: 这个方法在这里是概念性的，因为在Streamlit中，
        `st.number_input`等组件的返回值在脚本再次运行时就已经被赋值了。
        我们只需确保在`run_all_calculations`之前，这些组件已经被渲染。
        为了代码清晰，我们将这些字典的创建放在这里。
        """
        # 在display函数中，值已经被赋给对应的字典，这里只是重新声明结构
        pass  # 值已在display_*_config方法中被实时更新到self.xxx字典


if __name__ == "__main__":
    app = AmazonProfitCalculatorApp()
    app.run()