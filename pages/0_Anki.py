# 导入所需的库
import streamlit as st
from streamlit_jodit import st_jodit
import json
import uuid
from datetime import datetime
import pandas as pd
from collections import Counter
import base64
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px
from streamlit_paste_button import paste_image_button as pbutton


# --- 配置类 (Configuration Class) ---
class AppConfig:
    """
    集中管理应用的所有配置项，方便统一修改和维护。
    """
    # 1. 文件路径配置
    DATA_FILE = "cards.json"  # 存储卡片数据的文件名

    # 2. 复习结果定义 (使用柔和的十六进制颜色码)
    REVIEW_RESULTS = {
        "correct": {"label": "我知道", "color": "#73C6B6"},  # 正确：薄荷绿
        "unsure": {"label": "我不确定", "color": "#F8D775"},  # 模糊：琥珀黄
        "incorrect": {"label": "我不知道", "color": "#E57373"},  # 错误：珊瑚红
    }

    # 3. 标签颜色配置 (你可以自由增删改标签及其对应的颜色)
    TAG_COLORS = {
        "新概念": "blue",
        "流程": "orange",
        "算法": "green",
        "记忆": "violet",
        "默认": "gray",
    }

    # 4. 算法参数配置 (用于计算卡片困难度)
    DIFFICULTY_WEIGHTS = {
        "incorrect": 2,  # 答错一次，困难度增加 2
        "unsure": 1,  # 不确定一次，困难度增加 1
        "correct": -0.5,  # 答对一次，困难度减少 0.5
    }

    # 5. jodit编辑器配置
    # Jodit 配置 (最小高度，图片上传转为 Base64)
    JODIT_CONFIG = {
        'minHeight': 400,
        # 允许将图片转换为 Base64 编码，使其可以直接嵌入 HTML 中，避免文件路径问题
        'uploader': {
            'insertImageAsBase64URI': True,
            'imagesExtensions': ['jpg', 'png', 'jpeg', 'gif', 'svg', 'webp']
        },
        'toolbarButtonSize': 'large',
    }


# --- 核心数据管理类 (Data Management Class) ---
class CardDataManager:
    """
    这个类是应用的大脑，专门负责所有与卡片数据相关的操作，
    包括加载、保存、添加、更新、删除和查询。它不关心界面如何展示。
    """

    def __init__(self, filepath):
        """
        初始化数据管理器。
        Args:
            filepath (str): 数据文件的路径。
        """
        self.filepath = filepath
        self.cards = self.load_cards()

    def load_cards(self):
        """从 JSON 文件加载卡片数据。如果文件不存在或为空，则返回一个空列表。"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_cards(self):
        """将当前所有卡片数据保存回 JSON 文件。"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.cards, f, indent=4, ensure_ascii=False)

    def get_card_by_id(self, card_id):
        """通过唯一的 ID 查找并返回一张卡片。"""
        return next((card for card in self.cards if card['id'] == card_id), None)

    def add_card(self, question, answer, category_str, tags):
        """添加一张新卡片到数据列表中，并立即保存。"""
        new_card = {
            "id": str(uuid.uuid4()),
            "question": question,
            "answer": answer,
            "category_path": category_str.split('-'),
            "tags": tags,
            "add_time": datetime.now().isoformat(),
            "review_history": [],
            "difficulty": 0
        }
        self.cards.append(new_card)
        self.save_cards()
        return new_card

    def update_card(self, card_id, new_data):
        """根据卡片ID更新其数据。"""
        card = self.get_card_by_id(card_id)
        if card:
            card.update(new_data)
            self.save_cards()

    def delete_card(self, card_id):
        """根据卡片ID从数据列表中删除一张卡片。"""
        self.cards = [card for card in self.cards if card['id'] != card_id]
        self.save_cards()

    def add_review_record(self, card_id, result):
        """为指定的卡片添加一条新的复习记录，并触发困难度更新。"""
        card = self.get_card_by_id(card_id)
        if card and result in AppConfig.REVIEW_RESULTS:
            card['review_history'].append({"time": datetime.now().isoformat(), "result": result})
            self._update_difficulty(card)
            self.save_cards()

    def _update_difficulty(self, card):
        """根据复习历史和预设权重计算卡片的困难度。"""
        weights = AppConfig.DIFFICULTY_WEIGHTS
        difficulty = sum(weights.get(record['result'], 0) for record in card['review_history'])
        card['difficulty'] = max(0, round(difficulty, 2))

    def get_all_categories(self):
        """获取所有卡片中出现过的唯一类别路径。"""
        categories = set()
        for card in self.cards:
            path_parts = card.get('category_path', [])
            for i in range(1, len(path_parts) + 1):
                categories.add('-'.join(path_parts[:i]))
        return sorted(list(categories))

    def get_all_tags(self):
        """获取所有卡片中出现过的唯一标签。"""
        tags = set(tag for card in self.cards for tag in card.get('tags', []))
        return sorted(list(tags))

    def get_cards_by_category(self, category_str):
        """根据类别字符串筛选卡片，支持父级类别筛选。"""
        if not category_str or category_str == "所有":
            return self.cards
        selected_path = category_str.split('-')
        return [card for card in self.cards if card.get('category_path', [])[:len(selected_path)] == selected_path]

    def rename_category(self, old_category_str, new_category_str):
        """重命名一个类别，并更新所有相关的卡片。"""
        old_path = old_category_str.split('-')
        new_path = new_category_str.split('-')
        for card in self.cards:
            card_path = card.get('category_path', [])
            if card_path[:len(old_path)] == old_path:
                card['category_path'] = new_path + card_path[len(old_path):]
        self.save_cards()

    def rename_tag(self, old_tag, new_tag):
        """重命名一个标签，并更新所有相关的卡片。"""
        for card in self.cards:
            if old_tag in card.get('tags', []):
                card['tags'] = [new_tag if t == old_tag else t for t in card['tags']]
        self.save_cards()

    def delete_tag(self, tag_to_delete):
        """从所有卡片中删除一个指定的标签。"""
        for card in self.cards:
            if tag_to_delete in card.get('tags', []):
                card['tags'].remove(tag_to_delete)
        self.save_cards()


# --- UI 渲染类 (UI Rendering Class) ---
class AnkiUI:
    """
    这个类是应用的“门面”，专门负责所有与 Streamlit 界面渲染相关的逻辑。
    它通过持有一个 CardDataManager 实例来获取和操作数据。
    """

    def __init__(self, manager: CardDataManager):
        """
        初始化UI类。
        Args:
            manager (CardDataManager): 传入一个数据管理器实例，UI通过它与数据交互。
        """
        self.manager = manager

    def render(self):
        """
        渲染整个应用的主页面，包括标题和所有标签页。
        这是UI渲染的入口。
        """
        st.set_page_config(page_title="Streamlit Anki", layout="wide")
        st.title("🚀 Streamlit Anki: 你的专属记忆卡片应用")

        # 创建四个主要的标签页 (新增了“使用说明”)
        main_tabs = st.tabs(["复习 (Review)", "统计分析 (Statistics)", "卡片管理 (Card Management)", "使用说明 (Usage Guide)"])

        with main_tabs[0]:
            self._render_review_tab()
        with main_tabs[1]:
            self._render_stats_tab()
        with main_tabs[2]:
            self._render_management_tab()
        with main_tabs[3]:
            self._render_usage_guide_tab()

    def image_to_base64(self, image_file):
        """将上传的图片文件转换为Base64编码的字符串。"""
        buffered = BytesIO()
        # 将PIL Image对象保存到BytesIO流中
        # 假设 image_file 是一个 BytesIO 或类似的二进制流
        buffered.write(image_file.getvalue())
        # 获取Base64编码的字符串
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

    def _render_review_tab(self):
        """渲染“复习”标签页的内容。（已支持Markdown和图片显示）"""
        st.header("🧠 卡片复习")

        categories = ["所有"] + self.manager.get_all_categories()
        selected_category = st.selectbox("选择要复习的卡片类别：", options=categories)

        if st.button(f"开始复习 '{selected_category}' 类别"):
            st.session_state.review_cards = self.manager.get_cards_by_category(selected_category)
            st.session_state.review_cards.sort(key=lambda x: x.get('difficulty', 0), reverse=True)
            st.session_state.review_index = 0

        if 'review_cards' not in st.session_state or not st.session_state.review_cards:
            st.info("请选择一个类别并点击“开始复习”来加载卡片。")
            return

        total_cards = len(st.session_state.review_cards)
        if total_cards == 0:
            st.warning(f"'{selected_category}' 类别下没有卡片可供复习。")
            return

        current_index = st.session_state.get('review_index', 0)
        card = st.session_state.review_cards[current_index]

        st.progress((current_index + 1) / total_cards)
        st.write(f"进度: {current_index + 1} / {total_cards}")

        with st.container(border=True):
            new_question = st.text_area("问题：", value=card['question'], key=f"q_{card['id']}")

            # --- 修改：答案现在使用 st.markdown 渲染 ---
            with st.expander("👇 点击查看或编辑答案"):
                new_answer = st_jodit(AppConfig.JODIT_CONFIG, value=card['answer'], key=f"jodit1_{card['id']}")

            if st.button("💾 保存修改", key=f"save_{card['id']}"):
                if new_question != card['question'] or new_answer != card['answer']:
                    self.manager.update_card(card['id'], {"question": new_question, "answer": new_answer})
                    st.session_state.review_cards[current_index]['question'] = new_question
                    st.session_state.review_cards[current_index]['answer'] = new_answer
                    st.toast("卡片修改已保存！", icon="💾")
                else:
                    st.toast("内容未发生变化。", icon="🤷‍♂️")

            tags = card.get('tags', [])
            if tags:
                tag_html = " ".join([
                    f'<span style="background-color:{AppConfig.TAG_COLORS.get(tag, "gray")}; color:white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 5px;">{tag}</span>'
                    for tag in tags])
                st.markdown(f"**标签：** {tag_html}", unsafe_allow_html=True)
        st.write("---")

        # ... (按钮布局部分代码保持不变) ...
        cols_nav = st.columns(3)
        if cols_nav[0].button("⬅️ 上一个", use_container_width=True):
            st.session_state.review_index = max(0, current_index - 1)
            st.rerun()
        if cols_nav[1].button("⏭️ 跳过", use_container_width=True):
            st.session_state.review_index = min(total_cards - 1, current_index + 1)
            st.rerun()
        if cols_nav[2].button("➡️ 下一个", use_container_width=True):
            st.session_state.review_index = min(total_cards - 1, current_index + 1)
            st.rerun()

        st.write("")
        cols_review = st.columns(3)
        if cols_review[0].button(f"✅ {AppConfig.REVIEW_RESULTS['correct']['label']}", use_container_width=True):
            self.manager.add_review_record(card['id'], 'correct')
            st.toast("太棒了！继续下一个！", icon="✅")
            st.session_state.review_index = min(current_index + 1, total_cards - 1)
            st.rerun()
        if cols_review[1].button(f"🤔 {AppConfig.REVIEW_RESULTS['unsure']['label']}", use_container_width=True):
            self.manager.add_review_record(card['id'], 'unsure')
            st.toast("再记一下，下次就没问题了！", icon="🤔")
            st.session_state.review_index = min(current_index + 1, total_cards - 1)
            st.rerun()
        if cols_review[2].button(f"❌ {AppConfig.REVIEW_RESULTS['incorrect']['label']}", use_container_width=True):
            self.manager.add_review_record(card['id'], 'incorrect')
            st.toast("别灰心，这正是学习的机会！", icon="❌")
            st.session_state.review_index = min(current_index + 1, total_cards - 1)
            st.rerun()

    def _create_interactive_heatmap(self, data: pd.Series, title: str, cmap: str):
        """使用 Plotly 创建一个按月份分隔且数据正确的交互式日历热力图。"""

        # 1. 准备数据
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        start_date = data.index.min()
        end_date = data.index.max()
        all_days = pd.date_range(start=start_date, end=end_date, freq='D')

        data_dict = data.to_dict()

        # 2. 手动计算每个格子的坐标和数值
        display_weeks = []
        weekdays_from_mon = []
        counts = []
        hover_texts = []
        month_labels = {}

        current_week_col = 0

        if len(all_days) > 0:
            last_month = all_days[0].month
            month_labels[0] = all_days[0].strftime('%月')

        for i, date in enumerate(all_days):
            if i > 0:
                if date.weekday() == 0:
                    current_week_col += 1
                if date.month != last_month:
                    current_week_col += 1
                    month_labels[current_week_col] = date.strftime('%m月')
                    last_month = date.month

            display_weeks.append(current_week_col)
            weekdays_from_mon.append(date.weekday())

            count_for_day = data_dict.get(date, 0)
            counts.append(count_for_day)

            hover_texts.append(f"日期: {date.strftime('%Y-%m-%d')}<br>数量: {count_for_day}")

        # 3. 创建热力图
        fig = go.Figure(go.Heatmap(
            x=display_weeks,
            y=weekdays_from_mon,
            z=counts,
            text=hover_texts,
            hoverinfo='text',
            xgap=3, ygap=3,
            colorscale=cmap,
            showscale=False,
            colorbar=dict(
                title="数量",  # colorbar标题改为中文
                thickness=15,
                len=0.8
            ),
            zmin=0,
            zmax=max(counts) if counts and max(counts) > 0 else 1
        ))

        # 4. 美化图表布局
        fig.update_layout(
            title_text=title,
            yaxis_autorange='reversed',
            yaxis=dict(
                tickmode='array',
                tickvals=[0, 1, 2, 3, 4, 5, 6],
                ticktext=['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                showticklabels=True,
                title="星期"
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=list(month_labels.keys()),
                ticktext=list(month_labels.values()),
                showgrid=False,
                zeroline=False,
                title="时间"
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=50, l=50, r=20, b=50)
        )
        return fig

    def _prepare_stats_dataframe(self):
        """从原始卡片数据中准备用于统计分析的DataFrame。"""
        if not self.manager.cards:
            return pd.DataFrame()

        df = pd.DataFrame(self.manager.cards)
        df['add_time'] = pd.to_datetime(df['add_time'], format='ISO8601')
        df['review_count'] = df['review_history'].apply(len)
        df['category_str'] = df['category_path'].apply(lambda x: '-'.join(x))

        def count_results(history):
            counts = Counter(record['result'] for record in history)
            return counts['correct'], counts['unsure'], counts['incorrect']

        df[['correct_count', 'unsure_count', 'incorrect_count']] = df['review_history'].apply(count_results).tolist()
        return df

    def _render_subcategory_stats(self, df: pd.DataFrame):
        """渲染“最小子类统计”模块。"""
        st.subheader("最小子类统计", divider="rainbow")
        if df.empty:
            st.info("没有子类别可供统计。")
            return

        leaf_categories = df['category_str'].unique()
        selected_leaf_cat = st.selectbox("选择一个最小子类查看统计：", options=leaf_categories)
        if selected_leaf_cat:
            cat_df = df[df['category_str'] == selected_leaf_cat]
            cols = st.columns(4)
            cols[0].metric("卡片总数", len(cat_df))
            cols[1].metric("总正确次数", cat_df['correct_count'].sum())
            cols[2].metric("总模糊次数", cat_df['unsure_count'].sum())
            cols[3].metric("总错误次数", cat_df['incorrect_count'].sum())

    def _render_trend_analysis(self, df: pd.DataFrame):
        """渲染“趋势分析 (学习日历)”模块，包括筛选和热力图。"""
        st.subheader("趋势分析 (学习日历)", divider="rainbow")

        if df.empty:
            st.info("没有数据可用于趋势分析。")
            return

        cards_per_day = df.set_index('add_time').resample('D').size()  # 结果是一个Series，索引是日期，值是每日卡片数量
        review_df_data = [{'time': pd.to_datetime(r['time'])} for c in self.manager.cards for r in c['review_history']]
        reviews_per_day = pd.Series(dtype=int)
        if review_df_data:
            review_df = pd.DataFrame(review_df_data)
            reviews_per_day = review_df.set_index('time').resample('D').size()

        available_years = sorted(df['add_time'].dt.year.unique(), reverse=True)
        year_options = ["所有年份"] + available_years
        month_options = list(range(1, 13))

        filter_cols = st.columns(2)
        selected_year = filter_cols[0].selectbox("选择年份：", options=year_options)
        selected_months = filter_cols[1].multiselect("选择月份 (可多选)：", options=month_options)

        filtered_cards_data = cards_per_day.copy()
        filtered_reviews_data = reviews_per_day.copy()

        if selected_year != "所有年份":
            filtered_cards_data = filtered_cards_data[filtered_cards_data.index.year == selected_year]
            filtered_reviews_data = filtered_reviews_data[filtered_reviews_data.index.year == selected_year]

        if selected_months:
            filtered_cards_data = filtered_cards_data[filtered_cards_data.index.month.isin(selected_months)]
            filtered_reviews_data = filtered_reviews_data[filtered_reviews_data.index.month.isin(selected_months)]

        col1, col2 = st.columns(2)
        with col1:
            if not filtered_cards_data.empty:
                fig_cards = self._create_interactive_heatmap(filtered_cards_data, "每日新增卡片热力图", "Greens")
                st.plotly_chart(fig_cards, use_container_width=True)
            else:
                st.info("在筛选的日期范围内暂无新增卡片记录。")
        with col2:
            if not filtered_reviews_data.empty:
                fig_reviews = self._create_interactive_heatmap(filtered_reviews_data, "每日复习次数热力图", "Blues")
                st.plotly_chart(fig_reviews, use_container_width=True)
            else:
                st.info("在筛选的日期范围内暂无复习记录。")

    def _render_cards_overview_table(self, df: pd.DataFrame):
        """渲染“所有卡片总览”模块，包括表格和筛选控件。"""
        st.subheader("所有卡片总览", divider="rainbow")
        display_df = df[
            ['id', 'category_str', 'question', 'answer', 'tags', 'review_count', 'correct_count', 'unsure_count',
             'incorrect_count', 'difficulty']]

        filter_cols = st.columns([3, 3])
        all_cats = display_df['category_str'].unique() if not display_df.empty else []
        all_tags = display_df['tags'].explode().dropna().unique() if not display_df.empty else []

        with filter_cols[0]:
            selected_cats = st.multiselect("按类别筛选：", options=all_cats)
        with filter_cols[1]:
            selected_tags = st.multiselect("按标签筛选：", options=all_tags)

        filtered_df = display_df.copy()
        if selected_cats:
            filtered_df = filtered_df[filtered_df['category_str'].isin(selected_cats)]
        if selected_tags:
            filtered_df = filtered_df[filtered_df['tags'].apply(lambda tags: bool(set(tags) & set(selected_tags)))]

        st.dataframe(filtered_df)

    def _render_stats_tab(self):
        """
        渲染“统计分析”标签页的主函数。
        它调用多个辅助函数来分别渲染页面的不同部分。
        """
        st.header("📊 统计分析")
        if not self.manager.cards:
            st.info("还没有任何卡片，快去“卡片管理”标签页添加吧！")
            return

        # 1. 准备基础数据，只计算一次
        stats_df = self._prepare_stats_dataframe()

        # 2. 依次渲染各个UI模块
        self._render_subcategory_stats(stats_df)
        self._render_trend_analysis(stats_df)
        self._render_cards_overview_table(stats_df)

    def _render_management_tab(self):
        """渲染“卡片管理”标签页的内容。（已更新，新增类别/标签管理和默认类别功能）"""
        st.header("🗂️ 卡片管理")
        # 新增“类别/标签管理”子标签页
        m_tabs = st.tabs(["类别/标签管理", "单个添加", "编辑/删除卡片", "批量添加"])

        with m_tabs[0]:
            self._render_category_tag_management_tab()
        with m_tabs[1]:
            self._render_add_single_card_tab()
        with m_tabs[2]:
            self._render_edit_delete_card_tab()
        with m_tabs[3]:
            st.subheader("批量添加卡片")
            st.info("此功能正在开发中。未来将支持通过上传 CSV 或 Excel 文件批量导入卡片。")
            uploaded_file = st.file_uploader("上传文件", type=['csv', 'xlsx'])
            if uploaded_file:
                st.write("文件已上传，处理逻辑待实现。")

    def _render_category_tag_management_tab(self):
        """渲染“类别/标签管理”子标签页 (已修复UI联动更新问题)"""
        st.subheader("管理类别和标签")

        # --- 回调函数定义 ---
        def update_category_text_input():
            """当类别选择框变化时，强制更新文本输入框的状态"""
            st.session_state.new_cat_name = st.session_state.sel_cat

        def update_tag_text_input():
            """当标签选择框变化时，强制更新文本输入框的状态"""
            st.session_state.new_tag_name = st.session_state.sel_tag

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 类别管理")
            all_categories = self.manager.get_all_categories()
            if not all_categories:
                st.info("暂无类别可管理。")
            else:
                st.selectbox(
                    "选择要重命名的类别：",
                    options=all_categories,
                    key="sel_cat",
                    on_change=update_category_text_input  # 注册类别回调
                )
                new_category = st.text_input(
                    "输入新的类别名称：",
                    key="new_cat_name"  # 通过 key 从 session_state 获取值
                )
                if st.button("重命名类别"):
                    old_category_val = st.session_state.sel_cat
                    if old_category_val and new_category and old_category_val != new_category:
                        self.manager.rename_category(old_category_val, new_category)
                        st.success(f"类别 '{old_category_val}' 已成功重命名为 '{new_category}'！")
                        st.rerun()
                    else:
                        st.warning("新旧类别名称不能相同或为空。")
        with col2:
            st.markdown("#### 标签管理")
            all_tags = self.manager.get_all_tags()
            if not all_tags:
                st.info("暂无标签可管理。")
            else:
                st.selectbox(
                    "选择要操作的标签：",
                    options=all_tags,
                    key="sel_tag",
                    on_change=update_tag_text_input  # 注册标签回调
                )
                new_tag_name = st.text_input(
                    "输入新的标签名称（用于重命名）：",
                    key="new_tag_name"  # 通过 key 从 session_state 获取值
                )
                btn_cols = st.columns(2)
                if btn_cols[0].button("重命名标签"):
                    selected_tag_val = st.session_state.sel_tag
                    if selected_tag_val and new_tag_name and selected_tag_val != new_tag_name:
                        self.manager.rename_tag(selected_tag_val, new_tag_name)
                        st.success(f"标签 '{selected_tag_val}' 已成功重命名为 '{new_tag_name}'！")
                        st.rerun()
                    else:
                        st.warning("新旧标签名称不能相同或为空。")
                if btn_cols[1].button("删除标签", type="primary"):
                    selected_tag_val = st.session_state.sel_tag
                    if selected_tag_val:
                        self.manager.delete_tag(selected_tag_val)
                        st.warning(f"标签 '{selected_tag_val}' 已从所有卡片中删除！")
                        st.rerun()

    # <-- 2. START OF MAJOR CHANGES -->
    def _add_card_callback(self):
        """
        这是添加卡片按钮的on_click回调函数。
        它负责从session_state读取数据、验证、添加卡片，然后清空session_state。
        """
        # 从 session_state 读取小部件的当前值
        question = st.session_state.add_question_text
        answer = st.session_state.add_answer_text
        category = st.session_state.add_category_str
        tags = st.session_state.add_tags_multiselect

        # 验证输入
        if question and answer and category:
            self.manager.add_card(question, answer, category, tags)
            st.success("卡片添加成功！")

            # 更新默认类别以便连续添加
            st.session_state.default_category = category

            # 清空输入框的值
            st.session_state.add_question_text = ""
            st.session_state.add_answer_text = ""
        else:
            st.error("问题、答案和类别不能为空。")

    def _render_add_single_card_tab(self):
        """渲染“单个添加”子标签页"""
        st.subheader("单个添加卡片")

        categories = [""] + self.manager.get_all_categories()  # TODO
        if 'default_category' not in st.session_state:
            st.session_state.default_category = ""

        st.selectbox(
            "选择或输入一个默认类别（用于本次连续添加）：",
            options=categories,
            index=categories.index(
                st.session_state.default_category) if st.session_state.default_category in categories else 0,
            key='default_category'  # 绑定 key
        )
        st.info("设定默认类别后，下方表单中的类别字段会自动填充。")
        st.markdown("---")

        st.markdown("##### 问题&答案")
        st.text_area("问题 (Question)", key="add_question_text")
        st.markdown("在此输入答案...")
        st_jodit(AppConfig.JODIT_CONFIG, key=f"add_answer_text")
        st.text_input("类别 (Category)",
                      key="add_category_str",
                      value=st.session_state.get('default_category', ''))  # 使用 .get() 更安全

        st.multiselect("标签 (Tags)",
                       options=list(AppConfig.TAG_COLORS.keys()),
                       key="add_tags_multiselect")

        # 将 st.form_submit_button 替换为 st.button
        st.button(
            "添加卡片",
            on_click=self._add_card_callback  # 回调逻辑保持不变
        )


    def _render_edit_delete_card_tab(self):
        """渲染“编辑/删除卡片”子标签页 (已支持Markdown和图片上传)"""
        st.subheader("编辑或删除卡片")
        if not self.manager.cards:
            st.info("当前没有可编辑的卡片。")
            return

        card_options = {f"{c['question'][:30]}... (ID: {c['id'][:8]})": c['id'] for c in self.manager.cards}
        selected_card_display = st.selectbox("选择要编辑的卡片", options=card_options.keys())

        if selected_card_display:
            card_id = card_options[selected_card_display]
            card_to_edit = self.manager.get_card_by_id(card_id)

            with st.form("edit_card_form"):
                question = st.text_area("问题", value=card_to_edit['question'])

                st.markdown("答案")
                answer = st_jodit(AppConfig.JODIT_CONFIG, value=card_to_edit['answer'], key=f"edit_answer_text")


                category_str = st.text_input("类别", value='-'.join(card_to_edit.get('category_path', [])))
                tags = st.multiselect("标签", options=list(AppConfig.TAG_COLORS.keys()),
                                      default=card_to_edit.get('tags', []))

                col1, col2 = st.columns([5, 1])
                update_submitted = col1.form_submit_button("更新", use_container_width=True)
                delete_submitted = col2.form_submit_button("删除", type="primary", use_container_width=True)

                if update_submitted:
                    new_data = {"question": question, "answer": answer, "category_path": category_str.split('-'),
                                "tags": tags}
                    self.manager.update_card(card_id, new_data)
                    st.success(f"卡片 (ID: {card_id[:8]}) 更新成功！")
                    st.rerun()
                if delete_submitted:
                    self.manager.delete_card(card_id)
                    st.warning(f"卡片 (ID: {card_id[:8]}) 已被删除！")
                    st.rerun()

    def _render_usage_guide_tab(self):
        """渲染"使用说明"标签页"""
        st.header("📖 使用说明")
        st.markdown("""
        欢迎使用 Streamlit Anki 应用！这是一个帮助你记忆和复习知识点的工具。

        ### 1. 核心概念
        - **卡片 (Card)**：应用的基本单位，每张卡片包含一个**问题**和一个**答案**。
        - **类别 (Category)**：用于组织卡片的层级结构，使用 `-` 分隔。例如，`编程-Python-Streamlit` 表示 `Streamlit` 是 `Python` 的子类，而 `Python` 又是 `编程` 的子类。这种结构让你可以在复习时选择一个大的父类（如 `编程`）来复习其下所有的卡片。
        - **标签 (Tag)**：为卡片添加的非层级式关键词，用于快速筛选和识别。例如 `算法`、`重要` 等。
        - **困难度 (Difficulty)**：系统根据你的复习历史（正确、模糊、错误）自动计算的一个数值。在复习时，困难度越高的卡片会优先出现。

        ### 2. 主要功能区

        #### 🧠 复习 (Review)
        这是应用的核心区域。
        1.  **选择类别**：从下拉菜单中选择你想复习的卡片类别。选择父类别会包含所有子类别的卡片。
        2.  **开始复习**：点击按钮后，系统会根据卡片的困难度（从高到低）为你排序并加载卡片。
        3.  **富文本编辑器**：答案区域使用强大的富文本编辑器，支持：
            - **图文混排**：可以插入图片、表格、代码块等
            - **格式编辑**：支持加粗、斜体、下划线、字体颜色、背景色等
            - **数学公式**：支持 LaTeX 数学公式
            - **直接粘贴图片**：可以从剪贴板直接粘贴图片到编辑器中
        4.  **即时编辑**：在复习过程中，如果发现卡片的问题或答案有误，**可以直接修改并保存**，无需跳转页面。
        5.  **回答与导航**：
            - **我知道 / 我不确定 / 我不知道**：根据你的记忆情况点击对应的按钮。这会记录你的复习历史并更新卡片的困难度。
            - **上一个 / 下一个 / 跳过**：用于在卡片间自由导航。

        #### 📊 统计分析 (Statistics)
        这里展示了你的学习数据。
        - **最小子类统计**：选择一个具体的子类别，查看该类别下的卡片总数和各类复习结果的次数统计。
        - **趋势分析 (学习日历)**：通过交互式热力图直观地看到你每天新增的卡片数量和复习的次数，支持按年份和月份筛选。
        - **所有卡片总览**：一个包含所有卡片详细信息的数据表格，支持按类别和标签进行筛选。

        #### 🗂️ 卡片管理 (Card Management)
        在这里管理你的所有卡片、类别和标签。
        1.  **类别/标签管理**：
            - **重命名类别**：选择一个已有的类别，输入新名称，即可批量更新所有相关卡片。
            - **重命名标签**：选择一个标签，输入新名称，即可更新所有包含该标签的卡片。
            - **删除标签**：选择一个标签并点击"删除"，该标签将从所有卡片中移除。
        2.  **单个添加**：
            - **默认类别功能**：在添加卡片前，可以先在顶部的选择框设定一个"默认类别"。这样在下方表单中添加卡片时，类别字段会自动填充，极大提高了连续添加同一类别卡片的效率。
            - **富文本答案**：答案字段使用强大的富文本编辑器，支持图文混排和复杂格式。
            - **标签选择**：可以从预定义的标签中选择，标签带有颜色标识。
        3.  **编辑/删除卡片**：从下拉框中选择一张卡片，然后可以修改其所有信息（同样使用富文本编辑器）或将其彻底删除。
        4.  **批量添加**：(开发中) 未来将支持通过上传文件来一次性导入大量卡片。

        ### 3. 使用技巧
        - **利用类别层级**：建立清晰的类别层级结构，便于分类管理和针对性复习。
        - **善用标签**：给卡片添加合适的标签，便于在统计分析和查找时快速筛选。
        - **及时记录**：遇到需要记忆的知识点，立即添加到对应的类别中。
        - **定期复习**：利用困难度排序功能，优先复习掌握不好的卡片。
        - **活用富文本**：在答案中使用图片、代码块、数学公式等，让记忆更直观高效。
        """)


# --- 主应用逻辑 (Main Application Logic) ---
def main():
    """
    主函数，是整个 Streamlit 应用的入口。
    """
    if 'card_manager' not in st.session_state:
        st.session_state.card_manager = CardDataManager(AppConfig.DATA_FILE)
    manager = st.session_state.card_manager

    ui = AnkiUI(manager)
    ui.render()


# --- 程序入口点 ---
if __name__ == "__main__":
    main()