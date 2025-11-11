# app.py
import streamlit as st
import pandas as pd
import plotly.express as px


# ===================================================================
# CLASS 1: Config - 数据配置中心
# 负责存储和管理所有的配置信息。
# ===================================================================
class Config:
    """
    用于存储所有配置信息的数据类。
    通过st.session_state管理动态添加的SKU和箱子。
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
                    'other_costs': 0.0
                }
            }
        if 'destinations' not in st.session_state:
            st.session_state.destinations = {
                'ONT8': {'shipping_price': 10.0, 'assigned_boxes': ['箱子1']}
            }

        # 将所有配置项分组存放在字典中
        self.procurement = {
            'skus': st.session_state.skus,  # 引用会话状态
            'discount_rate': 100.0,
            'shipping_fee': 0.0,
            'other_costs': 0.0,
        }
        self.packaging = {
            'boxes': st.session_state.boxes  # 引用会话状态
        }
        self.shipping = {
            'min_chargeable_weight': 20.0,
            'volume_ratio': 6000,
            'destinations': st.session_state.destinations,  # 引用会话状态
            'other_costs': 0.0,
        }
        self.platform = {
            'skus_platform_fees': {
                '款式A': {'sell_price': 29.9, 'platform_fee': 8.0}
            },
            'fulfillment_fee': 0.0,
            'monthly_plan': 39.9,
            'other_costs': 0.0,
        }
        self.advertising = {
            'daily_spend': 12.0,
            'duration_days': 7,
        }
        self.finance = {
            'exchange_rate': 7.12,
            'withdrawal_fee_rate': 0.3,
        }


# ===================================================================
# CLASS 2: Calculator - 业务逻辑计算器
# 负责执行所有的计算任务。
# ===================================================================
class Calculator:
    """
    负责所有业务逻辑的计算。
    接收一个Config对象，并根据其数据进行计算。
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

    def calc_procurement_cost(self):
        cfg = self.config.procurement
        discount = cfg['discount_rate'] / 100.0
        item_costs = sum(d['purchase_price'] * d['quantity'] for d in cfg['skus'].values())
        discounted_item_costs = item_costs * discount
        total = discounted_item_costs + cfg['shipping_fee'] + cfg['other_costs']
        self.results['procurement_cost'] = total
        self.results['procurement_details'] = {
            "商品总成本": item_costs, "折扣后商品成本": discounted_item_costs,
            "运费": cfg['shipping_fee'], "其他费用": cfg['other_costs']
        }

    def calc_packaging_cost(self):
        self.results['packaging_cost'] = sum(
            b['unit_price'] * b['quantity'] + b['other_costs'] for b in self.config.packaging['boxes'].values()
        )

    def _get_chargeable_weight_details(self):
        details = {}
        for name, box in self.config.packaging['boxes'].items():
            product_weight = sum(
                self.config.procurement['skus'][sku]['weight'] * qty for sku, qty in box['items'].items()
            )
            actual_weight = product_weight + box['weight'] * box['quantity']
            volume_weight = (box['length'] * box['width'] * box['height']) / self.config.shipping['volume_ratio'] * box[
                'quantity']
            details[name] = {
                'actual_weight': actual_weight, 'volume_weight': volume_weight,
                'chargeable_weight': max(actual_weight, volume_weight)
            }
        return details

    def calc_shipping_cost(self):
        weight_details = self._get_chargeable_weight_details()
        self.results['chargeable_weights'] = weight_details
        total_shipping_cost = 0

        # 实际业务中，最低计费重量是按“票”算的，这里简化处理
        total_chargeable_weight = sum(d['chargeable_weight'] for d in weight_details.values())
        min_weight = self.config.shipping['min_chargeable_weight']

        if total_chargeable_weight < min_weight:
            # 如果总重小于最低计费，按最低计费*单价（这里用第一个目的地的单价作为示例）
            first_dest_price = next(iter(self.config.shipping['destinations'].values()))['shipping_price']
            total_shipping_cost = min_weight * first_dest_price
        else:
            for dest, dest_details in self.config.shipping['destinations'].items():
                price_per_kg = dest_details['shipping_price']
                for box_name in dest_details['assigned_boxes']:
                    if box_name in weight_details:
                        total_shipping_cost += weight_details[box_name]['chargeable_weight'] * price_per_kg

        total_shipping_cost += self.config.shipping['other_costs']
        self.results['shipping_cost'] = total_shipping_cost

    def calc_platform_cost_rmb(self):
        cfg_p = self.config.platform
        total_usd = sum(
            details['platform_fee'] * self.config.procurement['skus'][sku]['quantity']
            for sku, details in cfg_p['skus_platform_fees'].items()
        ) + cfg_p['fulfillment_fee'] + cfg_p['monthly_plan'] + cfg_p['other_costs']
        self.results['platform_fee_usd'] = total_usd
        self.results['platform_fee_rmb'] = total_usd * self.config.finance['exchange_rate']

    def calc_advertising_cost_rmb(self):
        cfg_a = self.config.advertising
        total_usd = cfg_a['daily_spend'] * cfg_a['duration_days']
        self.results['advertising_cost_usd'] = total_usd
        self.results['advertising_cost_rmb'] = total_usd * self.config.finance['exchange_rate']

    def calc_total_revenue_rmb(self):
        total_revenue_usd = sum(
            d['sell_price'] * self.config.procurement['skus'][sku]['quantity']
            for sku, d in self.config.platform['skus_platform_fees'].items()
        )
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
# 负责构建Streamlit的所有前端组件。
# ===================================================================
class UI:
    """
    负责构建Streamlit用户界面。
    接收Config和Calculator对象，用于数据绑定和结果展示。
    """

    def __init__(self, config: Config, calculator: Calculator):
        self.config = config
        self.calculator = calculator

    def run(self):
        st.title("亚马逊卖家成本利润计算器")
        tab1, tab2, tab3 = st.tabs(["配置界面", "公式页面", "统计页面"])

        with tab1:
            self._display_config_tab()

        self.calculator.run_all_calculations()

        with tab2:
            self._display_formulas_tab()

        with tab3:
            self._display_stats_tab()

    def _display_config_tab(self):
        col1, col2, col3 = st.columns(3)
        with col1:
            self._display_procurement_config()
        with col2:
            self._display_packaging_config()
            self._display_shipping_config()
        with col3:
            self._display_platform_config()
            self._display_advertising_config()
            self._display_finance_config()

    def _display_procurement_config(self):
        with st.container(border=True):
            st.subheader("1. 采购成本")
            # 动态增删SKU
            for name, details in list(st.session_state.skus.items()):
                with st.expander(f"SKU: {name}", expanded=True):
                    details['purchase_price'] = st.number_input(f"采购单价 (元)##{name}", value=details['purchase_price'],
                                                                step=0.1, format="%.2f")
                    details['quantity'] = st.number_input(f"采购数量 (件)##{name}", value=details['quantity'], step=1,
                                                          min_value=0)
                    details['weight'] = st.number_input(f"单件重量 (KG)##{name}", value=details['weight'], step=0.01,
                                                        format="%.3f")
                    if st.button(f"删除 {name}", key=f"del_sku_{name}"):
                        del st.session_state.skus[name]
                        st.rerun()
            if st.button("新增SKU"):
                new_name = f"款式{chr(ord('A') + len(st.session_state.skus))}"
                st.session_state.skus[new_name] = {'purchase_price': 0.0, 'quantity': 0, 'weight': 0.0}
                st.rerun()
            st.markdown("---")
            self.config.procurement['discount_rate'] = st.slider("折扣率 (%)", 0.0, 100.0,
                                                                 self.config.procurement['discount_rate'], 0.5)
            self.config.procurement['shipping_fee'] = st.number_input("运费 (元)",
                                                                      value=self.config.procurement['shipping_fee'])
            self.config.procurement['other_costs'] = st.number_input("其他费用 (元)",
                                                                     value=self.config.procurement['other_costs'])

    def _display_packaging_config(self):
        with st.container(border=True):
            st.subheader("2. 打包与装箱")
            for name, details in list(st.session_state.boxes.items()):
                with st.expander(f"箱子: {name}", expanded=True):
                    details['quantity'] = st.number_input(f"纸箱数量 (个)##{name}", value=details['quantity'], step=1)
                    details['unit_price'] = st.number_input(f"纸箱单价 (元)##{name}", value=details['unit_price'],
                                                            format="%.2f")
                    st.markdown("**箱内物品**")
                    for sku in self.config.procurement['skus'].keys():
                        details['items'][sku] = st.number_input(f"{sku} 数量##{name}_{sku}",
                                                                value=details['items'].get(sku, 0), step=1)
                    details['weight'] = st.number_input(f"空箱重量 (KG)##{name}", value=details['weight'], format="%.2f")
                    c1, c2, c3 = st.columns(3)
                    details['length'] = c1.number_input(f"长(cm)##{name}", value=details['length'])
                    details['width'] = c2.number_input(f"宽(cm)##{name}", value=details['width'])
                    details['height'] = c3.number_input(f"高(cm)##{name}", value=details['height'])
                    details['other_costs'] = st.number_input(f"其他费用(元)##{name}", value=details['other_costs'],
                                                             format="%.2f")
                    if st.button(f"删除 {name}", key=f"del_box_{name}"):
                        del st.session_state.boxes[name]
                        st.rerun()
            if st.button("新增箱子"):
                new_name = f"箱子{len(st.session_state.boxes) + 1}"
                st.session_state.boxes[new_name] = {'quantity': 1, 'items': {}, 'unit_price': 5.0, 'weight': 0.5,
                                                    'length': 50.0, 'width': 40.0, 'height': 40.0, 'other_costs': 0.0}
                st.rerun()

    def _display_shipping_config(self):
        with st.container(border=True):
            st.subheader("3. 国际货运成本")
            self.config.shipping['min_chargeable_weight'] = st.number_input("每票最低计费重量 (KG)", value=self.config.shipping[
                'min_chargeable_weight'])
            self.config.shipping['volume_ratio'] = st.number_input("体积比", value=self.config.shipping['volume_ratio'])
            for name, details in list(self.config.shipping['destinations'].items()):
                with st.expander(f"目的地: {name}", expanded=True):
                    details['shipping_price'] = st.number_input(f"运费单价(元/KG)##{name}", value=details['shipping_price'],
                                                                format="%.2f")
                    details['assigned_boxes'] = st.multiselect(f"发往此仓库的箱子##{name}",
                                                               options=list(self.config.packaging['boxes'].keys()),
                                                               default=details.get('assigned_boxes', []))
            self.config.shipping['other_costs'] = st.number_input("其他费用(元)##shipping",
                                                                  value=self.config.shipping['other_costs'],
                                                                  format="%.2f")

    def _display_platform_config(self):
        with st.container(border=True):
            st.subheader("4. 平台费用")
            fees_cfg = self.config.platform['skus_platform_fees']
            for sku_name in self.config.procurement['skus'].keys():
                if sku_name not in fees_cfg: fees_cfg[sku_name] = {'sell_price': 0.0, 'platform_fee': 0.0}
                with st.expander(f"款式: {sku_name}", expanded=True):
                    fees_cfg[sku_name]['sell_price'] = st.number_input(f"销售价格($)##{sku_name}",
                                                                       value=fees_cfg[sku_name]['sell_price'],
                                                                       format="%.2f")
                    fees_cfg[sku_name]['platform_fee'] = st.number_input(f"每件平台费($)##{sku_name}",
                                                                         value=fees_cfg[sku_name]['platform_fee'],
                                                                         format="%.2f")
            st.markdown("---")
            self.config.platform['fulfillment_fee'] = st.number_input("入库配置费($)",
                                                                      value=self.config.platform['fulfillment_fee'],
                                                                      format="%.2f")
            self.config.platform['monthly_plan'] = st.number_input("专业计划月租($/月)",
                                                                   value=self.config.platform['monthly_plan'],
                                                                   format="%.2f")
            self.config.platform['other_costs'] = st.number_input("其他费用($)##platform",
                                                                  value=self.config.platform['other_costs'],
                                                                  format="%.2f")

    def _display_advertising_config(self):
        with st.container(border=True):
            st.subheader("5. 广告费用")
            cfg = self.config.advertising
            cfg['daily_spend'] = st.number_input("日均广告花费($)", value=cfg['daily_spend'], format="%.2f")
            cfg['duration_days'] = st.number_input("广告持续天数(天)", value=cfg['duration_days'], step=1)

    def _display_finance_config(self):
        with st.container(border=True):
            st.subheader("6. 汇率和手续费")
            cfg = self.config.finance
            cfg['exchange_rate'] = st.number_input("汇率(美元兑人民币)", value=cfg['exchange_rate'], format="%.2f")
            cfg['withdrawal_fee_rate'] = st.number_input("提款手续费(%)", value=cfg['withdrawal_fee_rate'], format="%.2f")

    def _display_formulas_tab(self):
        st.header("计算过程详情")
        r = self.calculator.results
        st.expander("1. 货物成本 (¥)", expanded=True).write(r['procurement_details'])
        st.expander("2. 计费重量 (KG)", expanded=True).table(pd.DataFrame(r['chargeable_weights']).T)
        st.expander("3. 国际运费 (¥)", expanded=True).metric("总国际运费", f"¥ {r['shipping_cost']:.2f}")
        st.expander("4. 平台费用 (¥)", expanded=True).metric("平台费用", f"¥ {r['platform_fee_rmb']:.2f}",
                                                         f"${r['platform_fee_usd']:.2f}")
        st.expander("5. 广告费用 (¥)", expanded=True).metric("广告费用", f"¥ {r['advertising_cost_rmb']:.2f}",
                                                         f"${r['advertising_cost_usd']:.2f}")
        st.expander("6. 其他费用 (¥)", expanded=True).metric("打包过程费用", f"¥ {r['packaging_cost']:.2f}")

    def _display_stats_tab(self):
        st.header("总体统计信息")
        r = self.calculator.results
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总利润 (¥)", f"{r['profit_rmb']:,.2f}", f"{r['profit_margin']:.2f}% 利润率")
        col2.metric("净收入 (¥)", f"{r['net_revenue_rmb']:,.2f}")
        col3.metric("总成本 (¥)", f"{r['total_cost_rmb']:,.2f}")
        col4.metric("总销售额 ($)", f"${r['total_revenue_usd']:,.2f}")
        st.markdown("---")
        st.subheader("成本构成占比")

        filtered_costs = {k: v for k, v in r['cost_breakdown'].items() if v > 0}
        if not filtered_costs:
            st.warning("所有成本项均为0，无法生成图表。")
        else:
            df = pd.DataFrame(list(filtered_costs.items()), columns=['成本项', '金额(¥)'])
            fig = px.pie(df, values='金额(¥)', names='成本项', hole=0.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)


# ===================================================================
# MAIN - 程序主入口
# 负责实例化对象并运行应用。
# ===================================================================
def main():
    """
    应用程序主函数：
    1. 初始化配置对象。
    2. 初始化计算器对象，并传入配置。
    3. 初始化UI对象，并传入配置和计算器。
    4. 运行UI。
    """
    config = Config()
    calculator = Calculator(config)
    ui = UI(config, calculator)
    ui.run()


if __name__ == "__main__":
    main()