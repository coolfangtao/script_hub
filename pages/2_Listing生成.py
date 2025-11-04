import streamlit as st
import pandas as pd
import google.generativeai as genai
import textwrap

# --- 导入共享模块 ---
# 1. 从共享配置文件中导入 GlobalConfig 基类
from shared.config import GlobalConfig
# 假设这些模块存在于您的项目结构中 (如果不存在，可以暂时注释掉)
# from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar


# --- 本地配置类 ---
# 2. ListingConfig 继承自 GlobalConfig
class ListingConfig(GlobalConfig):
    """
    Listing 智能生成器的配置类。
    继承 GlobalConfig 以获取共享配置，如 RUN_MODE 和 GEMINI_API_KEY 名称。
    """

    def __init__(self):
        # 初始化父类，以设置 RUN_MODE 等属性
        super().__init__()

        # 应用配置
        self.PAGE_TITLE = "Listing 智能生成器"
        self.PAGE_ICON = "📝"
        self.LAYOUT = "wide"

        # API 配置
        # GEMINI_API_KEY 属性已从 GlobalConfig 继承
        # 覆盖父类的默认模型以使用更具体的版本
        self.DEFAULT_MODEL = "gemini-2.5-pro"

        # --- 新增：可选的 Gemini 模型列表 ---
        self.GEMINI_MODEL_OPTIONS = [
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-robotics-er-1.5-preview",
        ]

        # 数据配置
        self.KEYWORD_COLUMNS = ['流量词', '关键词翻译', '流量占比', '月搜索量', '购买率', 'ASIN']
        self.TOP_N_KEYWORDS = 20

        # 提示词模板 (保持不变)
        self.TITLE_PROMPT_TEMPLATE = """
            你是一名专业的亚马逊美国站的电商运营专家，尤其擅长撰写吸引人的产品标题。
            请根据以下关键词数据，为一款"{product_name}" ({product_english_name}) 撰写 {title_count} 个符合亚马逊平台规则且具有高吸引力的产品标题。

            **关键词数据参考:**
            - **流量占比最高的 TOP {top_n} 关键词:**
            ```csv
            {traffic_keywords_csv}
            ```

            - **月搜索量最高的 TOP {top_n} 关键词:**
            ```csv
            {search_volume_keywords_csv}
            ```

            **标题要求:**
            1.  **核心关键词优先**: 必须包含最核心的关键词，如 {core_keywords} 等。
            2.  **突出特性和优势**: 结合关键词，提炼产品的主要卖点，例如 {key_features}。
            3.  **可读性强**: 标题结构清晰，易于消费者快速理解产品是什么。
            4.  **长度适中**: 标题总长度建议在 150-200 个字符之间。
            5.  **格式规范**: 每个单词的首字母大写（除了 a, an, the, and, but, for, in, on, at 等虚词）。

            请直接给出你认为最佳的 {title_count} 个产品标题，并用数字编号。
        """

        self.BULLET_POINTS_PROMPT_TEMPLATE = """
            你是一名专业的亚马逊美国站的文案专家，擅长撰写能够提升转化率的五点描述 (Bullet Points)。
            请根据以下关键词数据，为一款"{product_name}" ({product_english_name}) 撰写 {bullet_points_count} 点描述。

            **关键词数据参考:**
            - **流量占比最高的 TOP {top_n} 关键词:**
            ```csv
            {traffic_keywords_csv}
            ```

            - **月搜索量最高的 TOP {top_n} 关键词:**
            ```csv
            {search_volume_keywords_csv}
            ```

            **五点描述要求:**
            1.  **突出卖点**: 每一点都应该聚焦一个核心卖点或功能，并详细阐述它能为客户带来的好处。
            2.  **格式清晰**: 每一点的开头使用一个简短、醒目的短语或标题 (例如 "{bullet_point_example}")，并用大写字母和特殊符号突出，使其易于阅读。
            3.  **融入关键词**: 自然地将核心关键词和长尾关键词融入到描述中，以提高 SEO 权重。
            4.  **解决用户痛点**: 设想用户可能遇到的问题 (如{user_pain_points})，并在描述中给出解决方案。
            5.  **覆盖多种使用场景**: 描述产品可以用于{usage_scenarios}。

            请严格按照 {bullet_points_count} 点的格式，给出完整的五点描述。
        """

        # 产品特定配置 (保持不变)
        self.PRODUCT_NAME = "宠物脱毛手套"
        self.PRODUCT_ENGLISH_NAME = "pet hair removal glove"
        self.CORE_KEYWORDS = "'pet hair remover glove', 'dog grooming glove', 'cat hair glove'"
        self.KEY_FEATURES = "'gentle', 'efficient', 'for cats and dogs'"
        self.BULLET_POINT_EXAMPLE = "【Efficient Hair Removal】"
        self.USER_PAIN_POINTS = "宠物毛发满天飞、普通梳子效果不佳、宠物不喜欢梳毛等"
        self.USAGE_SCENARIOS = "猫、狗、长毛或短毛宠物，以及用于沙发、地毯等场景"

        # 生成数量配置 (保持不变)
        self.TITLE_COUNT = 4
        self.BULLET_POINTS_COUNT = 5


# --- 页面配置 ---
cfg = ListingConfig()
st.set_page_config(
    page_title=cfg.PAGE_TITLE,
    page_icon=cfg.PAGE_ICON,
    layout=cfg.LAYOUT
)

# 加载共享侧边栏
create_common_sidebar(current_label="📝 Listing生成")


# --- 主要功能函数 (部分已修改) ---

def load_data(uploaded_file):
    """从用户上传的 Excel 文件中加载数据。"""
    st.info(f"正在读取文件: `{uploaded_file.name}`")
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        st.success("✅ 文件读取成功！")
        return df
    except Exception as e:
        st.error(f"❌ 文件读取失败: {e}")
        return None


def preprocess_keyword_data(df: pd.DataFrame, config: ListingConfig):
    """预处理关键词数据，处理多ASIN的情况。"""
    if 'ASIN' not in df.columns:
        st.warning("数据中未找到'ASIN'列，将使用原始数据进行处理。")
        return df

    unique_asins = df['ASIN'].nunique()
    unique_keywords = df['流量词'].nunique()
    st.info(f"📊 数据概览: 共 {len(df)} 行数据，涉及 {unique_asins} 个ASIN，{unique_keywords} 个唯一关键词")

    aggregation_rules = {}
    if '流量占比' in df.columns:
        df['流量占比'] = pd.to_numeric(df['流量占比'], errors='coerce')
        aggregation_rules['流量占比'] = 'max'
    if '月搜索量' in df.columns:
        df['月搜索量'] = pd.to_numeric(df['月搜索量'], errors='coerce')
        aggregation_rules['月搜索量'] = 'first'
    if '购买率' in df.columns:
        df['购买率'] = pd.to_numeric(df['购买率'], errors='coerce')
        aggregation_rules['购买率'] = 'mean'

    text_columns = ['流量词', '关键词翻译']
    for col in text_columns:
        if col in df.columns:
            aggregation_rules[col] = 'first'

    if aggregation_rules:
        processed_df = df.groupby('流量词', as_index=False).agg(aggregation_rules)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("处理前数据行数", len(df))
        with col2:
            st.metric("处理后唯一关键词数", len(processed_df))
        return processed_df
    else:
        return df


def get_top_keywords_by_traffic(df: pd.DataFrame, config: ListingConfig):
    """获取流量占比最高的关键词。"""
    if '流量占比' in df.columns:
        df_copy = df.copy()
        df_copy['流量占比'] = pd.to_numeric(df_copy['流量占比'], errors='coerce')
        df_copy.dropna(subset=['流量占比'], inplace=True)
        top_traffic_df = df_copy.sort_values(by='流量占比', ascending=False).head(config.TOP_N_KEYWORDS)
        return top_traffic_df
    else:
        st.warning("数据中未找到'流量占比'列，将使用前20行数据作为流量关键词。")
        return df.head(config.TOP_N_KEYWORDS)


def get_top_keywords_by_search_volume(df: pd.DataFrame, config: ListingConfig):
    """获取月搜索量最高的关键词。"""
    if '月搜索量' in df.columns:
        df_copy = df.copy()
        df_copy['月搜索量'] = pd.to_numeric(df_copy['月搜索量'], errors='coerce')
        df_copy.dropna(subset=['月搜索量'], inplace=True)
        top_search_df = df_copy.sort_values(by='月搜索量', ascending=False).head(config.TOP_N_KEYWORDS)
        return top_search_df
    else:
        st.warning("数据中未找到'月搜索量'列，将使用流量占比数据替代。")
        return get_top_keywords_by_traffic(df, config)


def create_prompts(df: pd.DataFrame, config: ListingConfig):
    """根据 DataFrame 中的关键词数据，创建用于生成标题和五点描述的提示词。"""
    processed_df = preprocess_keyword_data(df, config)
    top_traffic_df = get_top_keywords_by_traffic(processed_df, config)
    top_search_df = get_top_keywords_by_search_volume(processed_df, config)

    existing_columns = [col for col in config.KEYWORD_COLUMNS if col in processed_df.columns and col != 'ASIN']
    traffic_keywords_csv = top_traffic_df[existing_columns].to_csv(index=False)
    search_volume_keywords_csv = top_search_df[existing_columns].to_csv(index=False)

    title_prompt = textwrap.dedent(config.TITLE_PROMPT_TEMPLATE.format(
        top_n=config.TOP_N_KEYWORDS, product_name=config.PRODUCT_NAME,
        product_english_name=config.PRODUCT_ENGLISH_NAME, title_count=config.TITLE_COUNT,
        core_keywords=config.CORE_KEYWORDS, key_features=config.KEY_FEATURES,
        traffic_keywords_csv=traffic_keywords_csv, search_volume_keywords_csv=search_volume_keywords_csv
    )).strip()

    bullet_points_prompt = textwrap.dedent(config.BULLET_POINTS_PROMPT_TEMPLATE.format(
        top_n=config.TOP_N_KEYWORDS, product_name=config.PRODUCT_NAME,
        product_english_name=config.PRODUCT_ENGLISH_NAME, bullet_points_count=config.BULLET_POINTS_COUNT,
        bullet_point_example=config.BULLET_POINT_EXAMPLE, user_pain_points=config.USER_PAIN_POINTS,
        usage_scenarios=config.USAGE_SCENARIOS, traffic_keywords_csv=traffic_keywords_csv,
        search_volume_keywords_csv=search_volume_keywords_csv
    )).strip()

    return {
        "title": title_prompt, "bullet_points": bullet_points_prompt, "top_traffic_df": top_traffic_df,
        "top_search_df": top_search_df, "processed_df": processed_df
    }


# --- 修改：generate_listing_info 函数现在接收 model_name 参数 ---
def generate_listing_info(api_key: str, prompt: str, model_name: str):
    """使用 Google Gemini API 根据提示词生成内容。"""
    if not api_key or not api_key.startswith("AI"):
        st.error("❌ Google Gemini API 密钥无效或未提供，请检查。")
        return None
    try:
        genai.configure(api_key=api_key)
        # 使用传入的 model_name 初始化模型
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"调用 API 时发生错误: {e}")
        return f"调用API时发生错误: {e}"


# --- 主函数与页面渲染 (已重构以支持页面持久化和模型选择) ---

def main():
    """
    Streamlit 应用的主函数，负责渲染整个页面。
    通过 session_state 实现了页面切换后的状态保持。
    """
    st.title(cfg.PAGE_TITLE)
    st.markdown("上传关键词反查报告，AI 助您一键生成高质量的亚马逊商品标题和五点描述。")

    # --- 初始化 Session State ---
    # 在应用开始时，确保所有需要的键都存在于 session_state 中
    if 'uploaded_filename' not in st.session_state:
        st.session_state.uploaded_filename = None
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'generated_prompts' not in st.session_state:
        st.session_state.generated_prompts = None
    if 'generated_title' not in st.session_state:
        st.session_state.generated_title = None
    if 'generated_bullets' not in st.session_state:
        st.session_state.generated_bullets = None
    # --- 新增：为选择的模型初始化 session_state ---
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = cfg.DEFAULT_MODEL

    # 根据运行模式处理 API Key
    api_key = None
    if cfg.RUN_MODE == "cloud":
        st.info("☁️ 您正在云端运行本应用，请输入您的 Google Gemini API 密钥以继续。")
        api_key = st.text_input(
            "在此输入您的 Google Gemini API Key",
            type="password",
            help="您的密钥不会被储存或分享。"
        )
    else:  # local mode
        st.info("🏡 您正在本地运行本应用，将从 secrets.toml 文件加载 API 密钥。")
        api_key = st.secrets.get(cfg.GEMINI_API_KEY)

    # 检查 API Key 是否有效，如果无效则阻止后续操作
    if not api_key:
        st.warning("请输入或配置您的 API 密钥以开始使用。")
        st.stop()

    # --- 步骤 1: 上传文件与数据处理 ---
    with st.container(border=True):
        st.header("⚙️ 第 1 步: 上传文件与配置")

        # --- 新增：模型选择器 ---
        # 使用 key 直接将选择器的值绑定到 session_state
        st.selectbox(
            label="选择您想使用的 AI 模型:",
            options=cfg.GEMINI_MODEL_OPTIONS,
            # 确保默认选项是配置文件中指定的模型
            index=cfg.GEMINI_MODEL_OPTIONS.index(st.session_state.selected_model),
            key='selected_model',
            help="模型越强大，生成速度可能越慢，成本也可能更高。"
        )

        uploaded_file = st.file_uploader(
            "上传您的关键词反查 Excel 文件",
            type=['xlsx'],
            help="上传新文件将会覆盖当前已加载的数据，并重置生成流程。"
        )

        # 核心逻辑：仅当上传了“新”文件时，才执行数据处理和状态重置
        if uploaded_file is not None and uploaded_file.name != st.session_state.uploaded_filename:
            df = load_data(uploaded_file)
            if df is not None:
                # 1. 缓存新数据和新文件名
                st.session_state.uploaded_data = df
                st.session_state.uploaded_filename = uploaded_file.name
                # 2. 重置所有下游状态，因为源数据已更改
                st.session_state.generated_prompts = None
                st.session_state.generated_title = None
                st.session_state.generated_bullets = None
                # 使用 st.rerun() 可以立即刷新页面，提供更流畅的体验
                st.rerun()

        # UI渲染逻辑：完全基于 session_state 中的数据状态
        if st.session_state.uploaded_data is not None:
            st.success(f"✅ 当前已加载数据文件: **{st.session_state.uploaded_filename}**")
            with st.expander("📊 点击查看完整数据"):
                df_display = st.session_state.uploaded_data
                st.dataframe(df_display, use_container_width=True)
                st.markdown(f"**数据总行数:** {len(df_display)} 行")
                if 'ASIN' in df_display.columns:
                    st.markdown(f"**涉及ASIN数量:** {df_display['ASIN'].nunique()} 个")

            # 仅当提示词尚未生成时，才显示“生成提示词”按钮
            if st.session_state.generated_prompts is None:
                if st.button("📝 分析数据并生成提示词", type="primary"):
                    with st.spinner("正在分析关键词并创建提示词..."):
                        prompts_data = create_prompts(st.session_state.uploaded_data, cfg)
                        st.session_state.generated_prompts = prompts_data
                    st.success("✅ 提示词已在下方生成！您可以进行修改。")
                    st.rerun()
        else:
            st.info("请先上传您的 Excel 文件以开始。")

    # --- 步骤 2: 编辑提示词 ---
    if st.session_state.generated_prompts:
        with st.container(border=True):
            st.header("✏️ 第 2 步: 审核并优化提示词")
            st.markdown("您可以在此微调AI的指令。例如，您可以要求生成 5 个而不是 4 个标题，或者改变文案的语气。")

            if 'processed_df' in st.session_state.generated_prompts:
                processed_df = st.session_state.generated_prompts['processed_df']
                st.info(f"🔧 数据已预处理：从 {len(st.session_state.uploaded_data)} 行原始数据聚合为 {len(processed_df)} 个唯一关键词")

            st.subheader("📋 提取的关键词数据")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**🔝 流量占比 TOP {cfg.TOP_N_KEYWORDS} 关键词**")
                top_traffic_df = st.session_state.generated_prompts.get('top_traffic_df')
                if top_traffic_df is not None:
                    display_columns = [col for col in cfg.KEYWORD_COLUMNS if
                                       col in top_traffic_df.columns and col != 'ASIN']
                    st.dataframe(top_traffic_df[display_columns], use_container_width=True, height=400)
                    st.markdown(f"*共 {len(top_traffic_df)} 个关键词*")

            with col2:
                st.markdown(f"**🔍 月搜索量 TOP {cfg.TOP_N_KEYWORDS} 关键词**")
                top_search_df = st.session_state.generated_prompts.get('top_search_df')
                if top_search_df is not None:
                    display_columns = [col for col in cfg.KEYWORD_COLUMNS if
                                       col in top_search_df.columns and col != 'ASIN']
                    st.dataframe(top_search_df[display_columns], use_container_width=True, height=400)
                    st.markdown(f"*共 {len(top_search_df)} 个关键词*")

            st.divider()
            st.subheader("🛠️ 提示词编辑")
            col1, col2 = st.columns(2)
            with col1:
                title_prompt_text = st.text_area(
                    label="**标题生成提示词 (Title Prompt)**",
                    value=st.session_state.generated_prompts['title'],
                    height=500,
                    key='title_prompt_editor'
                )
            with col2:
                bullet_points_prompt_text = st.text_area(
                    label="**五点描述生成提示词 (Bullet Points Prompt)**",
                    value=st.session_state.generated_prompts['bullet_points'],
                    height=500,
                    key='bullets_prompt_editor'
                )

            st.header("✨ 第 3 步: 生成 Listing")
            if st.button("🚀 点击生成 Listing", type="primary", use_container_width=True):
                # --- 修改：更新 spinner 提示信息 ---
                spinner_message = f"AI 正在使用 `{st.session_state.selected_model}` 模型努力创作中，请稍候..."
                with st.spinner(spinner_message):
                    # 从编辑框获取最新文本
                    final_title_prompt = st.session_state.title_prompt_editor
                    final_bullets_prompt = st.session_state.bullets_prompt_editor

                    # --- 修改：将选择的模型名称传入生成函数 ---
                    selected_model = st.session_state.selected_model
                    generated_title = generate_listing_info(api_key, final_title_prompt, selected_model)
                    generated_bullets = generate_listing_info(api_key, final_bullets_prompt, selected_model)

                    st.session_state.generated_title = generated_title
                    st.session_state.generated_bullets = generated_bullets
                st.rerun()

    # --- 结果展示 ---
    if 'generated_title' in st.session_state and st.session_state.generated_title:
        with st.container(border=True):
            st.header("✅ 第 4 步: 查看并复制结果")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**建议标题:**")
                st.code(st.session_state.generated_title, language=None)
            with col2:
                st.markdown("**建议五点描述:**")
                st.code(st.session_state.generated_bullets, language=None)


if __name__ == "__main__":
    main()