import streamlit as st
import pandas as pd
import google.generativeai as genai
import textwrap


# --- 本地配置类 ---
class ListingConfig:
    """Listing 智能生成器的配置类"""

    # 应用配置
    PAGE_TITLE = "Listing 智能生成器"
    PAGE_ICON = "🚀"
    LAYOUT = "wide"

    # API 配置
    GEMINI_API_KEY = "GEMINI_API_KEY"
    DEFAULT_MODEL = "gemini-pro"

    # 数据配置
    KEYWORD_COLUMNS = ['流量词', '关键词翻译', '流量占比', '月搜索量', '购买率']
    TOP_N_KEYWORDS = 20

    # 提示词模板
    TITLE_PROMPT_TEMPLATE = """
        你是一名专业的亚马逊美国站的电商运营专家，尤其擅长撰写吸引人的产品标题。
        请根据以下 TOP {top_n} 的关键词数据，为一款"{product_name}" ({product_english_name}) 撰写 {title_count} 个符合亚马逊平台规则且具有高吸引力的产品标题。

        **标题要求:**
        1.  **核心关键词优先**: 必须包含最核心的关键词，如 {core_keywords} 等。
        2.  **突出特性和优势**: 结合关键词，提炼产品的主要卖点，例如 {key_features}。
        3.  **可读性强**: 标题结构清晰，易于消费者快速理解产品是什么。
        4.  **长度适中**: 标题总长度建议在 150-200 个字符之间。
        5.  **格式规范**: 每个单词的首字母大写（除了 a, an, the, and, but, for, in, on, at 等虚词）。

        **关键词数据参考:**
        ```csv
        {keywords_csv}
        ```

        请直接给出你认为最佳的 {title_count} 个产品标题，并用数字编号。
    """

    BULLET_POINTS_PROMPT_TEMPLATE = """
        你是一名专业的亚马逊美国站的文案专家，擅长撰写能够提升转化率的五点描述 (Bullet Points)。
        请根据以下 TOP {top_n} 的关键词数据，为一款"{product_name}" ({product_english_name}) 撰写 {bullet_points_count} 点描述。

        **五点描述要求:**
        1.  **突出卖点**: 每一点都应该聚焦一个核心卖点或功能，并详细阐述它能为客户带来的好处。
        2.  **格式清晰**: 每一点的开头使用一个简短、醒目的短语或标题 (例如 "{bullet_point_example}")，并用大写字母和特殊符号突出，使其易于阅读。
        3.  **融入关键词**: 自然地将核心关键词和长尾关键词融入到描述中，以提高 SEO 权重。
        4.  **解决用户痛点**: 设想用户可能遇到的问题 (如{user_pain_points})，并在描述中给出解决方案。
        5.  **覆盖多种使用场景**: 描述产品可以用于{usage_scenarios}。

        **关键词数据参考:**
        ```csv
        {keywords_csv}
        ```

        请严格按照 {bullet_points_count} 点的格式，给出完整的五点描述。
    """

    # 产品特定配置
    PRODUCT_NAME = "宠物脱毛手套"
    PRODUCT_ENGLISH_NAME = "pet hair removal glove"
    CORE_KEYWORDS = "'pet hair remover glove', 'dog grooming glove', 'cat hair glove'"
    KEY_FEATURES = "'gentle', 'efficient', 'for cats and dogs'"
    BULLET_POINT_EXAMPLE = "【Efficient Hair Removal】"
    USER_PAIN_POINTS = "宠物毛发满天飞、普通梳子效果不佳、宠物不喜欢梳毛等"
    USAGE_SCENARIOS = "猫、狗、长毛或短毛宠物，以及用于沙发、地毯等场景"

    # 生成数量配置
    TITLE_COUNT = 3
    BULLET_POINTS_COUNT = 5


# --- 导入共享模块 ---
# 假设这些模块存在于您的项目结构中
from shared.sidebar import create_common_sidebar
from shared.config import Config

# --- 页面配置 ---
cfg = ListingConfig()
st.set_page_config(
    page_title=cfg.PAGE_TITLE,
    page_icon=cfg.PAGE_ICON,
    layout=cfg.LAYOUT
)

# 加载共享侧边栏
create_common_sidebar()


# --- 主要功能函数 ---

def load_data(uploaded_file):
    """
    从用户上传的 Excel 文件中加载数据。

    Args:
        uploaded_file (UploadedFile): Streamlit 文件上传组件返回的对象。

    Returns:
        pd.DataFrame or None: 如果成功，返回包含数据的 DataFrame；否则返回 None。
    """
    st.info(f"正在读取文件: `{uploaded_file.name}`")
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        st.success("✅ 文件读取成功！")
        return df
    except Exception as e:
        st.error(f"❌ 文件读取失败: {e}")
        return None


def create_prompts(df: pd.DataFrame, config: ListingConfig):
    """
    根据 DataFrame 中的关键词数据，创建用于生成标题和五点描述的提示词。

    Args:
        df (pd.DataFrame): 包含关键词数据的 DataFrame。
        config (ListingConfig): 配置类实例。

    Returns:
        dict: 包含 'title' 和 'bullet_points' 两个提示词的字典。
    """
    # 1. 数据预处理：选取流量占比最高的 TOP N 关键词
    if '流量占比' in df.columns:
        df['流量占比'] = pd.to_numeric(df['流量占比'], errors='coerce')
        df.dropna(subset=['流量占比'], inplace=True)
        top_keywords_df = df.sort_values(by='流量占比', ascending=False).head(config.TOP_N_KEYWORDS)
    else:
        # 如果没有'流量占比'列，默认取前 N行
        top_keywords_df = df.head(config.TOP_N_KEYWORDS)

    # 2. 筛选出实际存在的列，并转换为 CSV 字符串
    existing_columns = [col for col in config.KEYWORD_COLUMNS if col in top_keywords_df.columns]
    keywords_csv = top_keywords_df[existing_columns].to_csv(index=False)

    # 3. 构建提示词模板
    title_prompt = textwrap.dedent(config.TITLE_PROMPT_TEMPLATE.format(
        top_n=config.TOP_N_KEYWORDS,
        product_name=config.PRODUCT_NAME,
        product_english_name=config.PRODUCT_ENGLISH_NAME,
        title_count=config.TITLE_COUNT,
        core_keywords=config.CORE_KEYWORDS,
        key_features=config.KEY_FEATURES,
        keywords_csv=keywords_csv
    )).strip()

    bullet_points_prompt = textwrap.dedent(config.BULLET_POINTS_PROMPT_TEMPLATE.format(
        top_n=config.TOP_N_KEYWORDS,
        product_name=config.PRODUCT_NAME,
        product_english_name=config.PRODUCT_ENGLISH_NAME,
        bullet_points_count=config.BULLET_POINTS_COUNT,
        bullet_point_example=config.BULLET_POINT_EXAMPLE,
        user_pain_points=config.USER_PAIN_POINTS,
        usage_scenarios=config.USAGE_SCENARIOS,
        keywords_csv=keywords_csv
    )).strip()

    return {"title": title_prompt, "bullet_points": bullet_points_prompt}


def generate_listing_info(api_key: str, prompt: str, config: ListingConfig):
    """
    使用 Google Gemini API 根据提示词生成内容。

    Args:
        api_key (str): Google Gemini API 密钥。
        prompt (str): 用于生成内容的提示词。
        config (ListingConfig): 配置类实例。

    Returns:
        str or None: 成功则返回生成的文本，失败则返回错误信息或 None。
    """
    if not api_key:
        st.error("Google Gemini API 密钥未配置，请在 secrets.toml 中设置。")
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(config.DEFAULT_MODEL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"调用 API 时发生错误: {e}")
        return f"调用API时发生错误: {e}"


# --- 主函数与页面渲染 ---

def main():
    """
    Streamlit 应用的主函数，负责渲染整个页面。
    """
    st.title(cfg.PAGE_TITLE)
    st.markdown("上传关键词反查报告，AI 助您一键生成高质量的亚马逊商品标题和五点描述。")

    # 从 secrets 中安全地获取 API Key
    api_key = st.secrets.get(cfg.GEMINI_API_KEY)

    # --- 步骤 1: 上传文件 ---
    with st.container(border=True):
        st.header("⚙️ 第 1 步: 上传关键词文件")
        uploaded_file = st.file_uploader(
            "上传您的关键词反查 Excel 文件",
            type=['xlsx'],
            help="请确保文件中包含流量词、流量占比等关键信息。"
        )

        if 'generated_prompts' not in st.session_state:
            st.session_state.generated_prompts = None

        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                with st.expander("点击查看已上传数据的前 5 行", expanded=True):
                    st.dataframe(df.head(), use_container_width=True)

                if st.button("📝 分析数据并生成提示词", type="primary"):
                    with st.spinner("正在分析关键词并创建提示词..."):
                        st.session_state.generated_prompts = create_prompts(df, cfg)
                    st.success("✅ 提示词已在下方生成！您可以进行修改。")
        else:
            st.info("请先上传您的 Excel 文件以开始。")

    # --- 步骤 2: 编辑提示词 ---
    if st.session_state.generated_prompts:
        with st.container(border=True):
            st.header("✏️ 第 2 步: 审核并优化提示词")
            st.markdown("您可以在此微调AI的指令。例如，您可以要求生成 5 个而不是 3 个标题，或者改变文案的语气。")

            col1, col2 = st.columns(2)
            with col1:
                title_prompt_text = st.text_area(
                    label="**标题生成提示词 (Title Prompt)**",
                    value=st.session_state.generated_prompts['title'],
                    height=500
                )
            with col2:
                bullet_points_prompt_text = st.text_area(
                    label="**五点描述生成提示词 (Bullet Points Prompt)**",
                    value=st.session_state.generated_prompts['bullet_points'],
                    height=500
                )

            # --- 步骤 3: 生成 Listing ---
            st.header("✨ 第 3 步: 生成 Listing")
            if st.button("🚀 点击生成 Listing", type="primary", use_container_width=True):
                if not api_key:
                    st.error("未在 st.secrets 中配置 Google Gemini API 密钥，无法生成内容。")
                else:
                    with st.spinner("AI 正在努力创作中，请稍候..."):
                        # 使用文本框中最新的内容来生成
                        generated_title = generate_listing_info(api_key, title_prompt_text, cfg)
                        generated_bullets = generate_listing_info(api_key, bullet_points_prompt_text, cfg)

                        # 将生成结果存入 session_state，避免重复生成
                        st.session_state.generated_title = generated_title
                        st.session_state.generated_bullets = generated_bullets

    # --- 结果展示 ---
    # 将结果展示区独立出来，只要 session_state 中有结果就显示
    if 'generated_title' in st.session_state and st.session_state.generated_title:
        st.subheader("✅ 生成结果")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**建议标题:**")
            st.code(st.session_state.generated_title, language=None)

        with col2:
            st.markdown("**建议五点描述:**")
            st.code(st.session_state.generated_bullets, language=None)


if __name__ == "__main__":
    main()