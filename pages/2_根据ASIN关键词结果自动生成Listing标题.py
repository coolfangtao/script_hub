import streamlit as st
import pandas as pd
import google.generativeai as genai
from shared.sidebar import create_common_sidebar  # <-- 1. 导入函数
from shared.config import Config
cfg = Config()

create_common_sidebar()  # <-- 2. 调用函数，确保每个页面都有侧边栏


def load_data(uploaded_file):
    """
    从上传的Excel文件中加载数据.
    只读取第一个sheet.
    """
    try:
        # 使用pandas的ExcelFile来处理可能的多sheet文件
        xls = pd.ExcelFile(uploaded_file)
        # 读取第一个sheet
        df = pd.read_excel(xls, sheet_name=0)
        return df
    except Exception as e:
        st.error(f"文件读取失败: {e}")
        return None


def create_prompts(df):
    """
    根据DataFrame中的关键词数据创建用于生成标题和五点描述的提示词.
    """
    # 为了让提示词更有效，我们选取'流量占比'最高的TOP 20的关键词
    # 首先确保'流量占比'列是数值类型
    if '流量占比' in df.columns:
        df['流量占比'] = pd.to_numeric(df['流量占比'], errors='coerce')
        # 丢弃转换失败的行
        df.dropna(subset=['流量占比'], inplace=True)
        # 按'流量占比'降序排序并选取Top 20
        top_keywords_df = df.sort_values(by='流量占比', ascending=False).head(20)
    else:
        # 如果没有'流量占比'列，就取前20行
        top_keywords_df = df.head(20)

    # 将关键词数据转换为CSV格式的字符串
    # 只选择和关键词相关的列，避免无关信息干扰
    keyword_columns = ['流量词', '关键词翻译', '流量占比', '月搜索量', '购买率']
    # 筛选出DataFrame中存在的列
    existing_columns = [col for col in keyword_columns if col in top_keywords_df.columns]

    keywords_csv = top_keywords_df[existing_columns].to_csv(index=False)

    # --- 标题的提示词 ---
    # 根据您的要求，默认提示词会要求生成3个标题，您可以在页面上修改这个数字
    title_prompt = f"""
    你是一名专业的亚马逊美国站的电商运营专家，尤其擅长撰写吸引人的产品标题。
    请根据以下TOP 20的关键词数据，为一款宠物脱毛手套（pet hair removal glove）撰写3个符合亚马逊平台规则且具有高吸引力的产品标题。

    **标题要求:**
    1.  **核心关键词优先**: 必须包含最核心的关键词，如 'pet hair remover glove', 'dog grooming glove', 'cat hair glove' 等。
    2.  **突出特性和优势**: 结合关键词，提炼产品的主要卖点，例如 'gentle', 'efficient', 'for cats and dogs'。
    3.  **可读性强**: 标题结构清晰，易于消费者快速理解产品是什么。
    4.  **长度适中**: 标题总长度建议在150-200个字符之间。
    5.  **格式规范**: 每个单词的首字母大写（除了a, an, the, and, but, for, in, on, at等虚词）。

    **关键词数据参考:**
    ```csv
    {keywords_csv}
    ```

    请直接给出你认为最佳的3个产品标题，并用数字编号。
    """

    # --- 五点描述的提示词 ---
    bullet_points_prompt = f"""
    你是一名专业的亚马逊美国站的文案专家，擅长撰写能够提升转化率的五点描述（Bullet Points）。
    请根据以下TOP 20的关键词数据，为一款宠物脱毛手套（pet hair removal glove）撰写5点描述。

    **五点描述要求:**
    1.  **突出卖点**: 每一点都应该聚焦一个核心卖点或功能，并详细阐述它能为客户带来的好处。
    2.  **格式清晰**: 每一点的开头使用一个简短、醒目的短语或标题（例如 "【Efficient Hair Removal】"），并用大写字母和特殊符号突出，使其易于阅读。
    3.  **融入关键词**: 自然地将核心关键词和长尾关键词融入到描述中，以提高SEO权重。
    4.  **解决用户痛点**: 设想用户可能遇到的问题（如宠物毛发满天飞、普通梳子效果不佳、宠物不喜欢梳毛等），并在描述中给出解决方案。
    5.  **覆盖多种使用场景**: 描述产品可以用于猫、狗、长毛或短毛宠物，以及用于沙发、地毯等场景。

    **关键词数据参考:**
    ```csv
    {keywords_csv}
    ```

    请严格按照5点的格式，给出完整的五点描述。
    """

    return {"title": title_prompt, "bullet_points": bullet_points_prompt}


def generate_listing_info(api_key, prompt):
    """
    使用Gemini API根据提示词生成内容.
    """
    # 增加一个API Key是否存在的检查
    if not api_key:
        st.error("Google Gemini API 密钥未配置，请在 secrets.toml 中设置。")
        return None
    try:
        # 配置API密钥
        genai.configure(api_key=api_key)
        # 创建模型实例
        model = genai.GenerativeModel(cfg.LISTING_DEFAULT_MODEL)
        # 生成内容
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"调用API时发生错误: {e}"


def main():
    """
    Streamlit应用的主函数.
    """
    st.set_page_config(page_title="Listing智能生成器", layout="wide")
    st.title("🚀 Listing智能生成器")
    st.markdown("---")

    st.header("⚙️ 第1步: 上传文件")

    # 从secrets中获取API Key
    api_key = st.secrets.get(cfg.GEMINI_API_KEY)

    # 文件上传控件
    uploaded_file = st.file_uploader(
        "上传关键词反查Excel文件",
        type=['xlsx'],
        help="请上传包含关键词数据的Excel文件。"
    )
    st.markdown("---")

    # 初始化session_state以存储生成的提示词
    if 'generated_prompts' not in st.session_state:
        st.session_state.generated_prompts = None

    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.dataframe(df.head(), use_container_width=True)

            # --- 新增逻辑: 点击按钮来生成提示词 ---
            if st.button("📝 分析数据并生成提示词"):
                with st.spinner("正在分析关键词并创建提示词..."):
                    # 将生成的提示词存入session_state
                    st.session_state.generated_prompts = create_prompts(df)
                st.success("提示词已生成！您现在可以在下方文本框中进行修改。")
    else:
        st.info("请先上传您的Excel文件。")

    # --- 新增逻辑: 如果提示词已生成，则显示可编辑的文本框 ---
    if st.session_state.generated_prompts:
        st.header("✏️ 第2步: 编辑提示词")
        st.info("您可以在这里微调AI的指令。例如，您可以要求AI生成5个而不是3个标题，或者改变文案的语气。")

        # 从session_state中读取提示词作为文本框的默认值
        title_prompt_text = st.text_area(
            label="标题生成提示词 (Title Prompt)",
            value=st.session_state.generated_prompts['title'],
            height=600
        )

        bullet_points_prompt_text = st.text_area(
            label="五点描述生成提示词 (Bullet Points Prompt)",
            value=st.session_state.generated_prompts['bullet_points'],
            height=600
        )

        st.markdown("---")
        st.header("✨ 第3步: 生成Listing")

        # 点击此按钮时，会使用上面两个文本框中最新的内容
        if st.button("🚀 点击生成Listing", type="primary"):
            if not api_key:
                st.error("未在st.secrets中配置Google Gemini API密钥，无法生成内容。")
            else:
                with st.spinner("AI正在努力创作中，请稍候..."):
                    # 使用文本框中（可能已被修改的）提示词来生成内容
                    generated_title = generate_listing_info(api_key, title_prompt_text)
                    generated_bullets = generate_listing_info(api_key, bullet_points_prompt_text)

                    # 显示最终结果
                    st.subheader("✅ 生成结果")
                    if generated_title:
                        st.markdown("**建议标题:**")
                        # 使用markdown代码块来显示，它会自动适应内容高度并自带复制按钮
                        st.markdown(f"```\n{generated_title}\n```")

                    if generated_bullets:
                        st.markdown("**建议五点描述:**")
                        # 使用markdown代码块来显示，它会自动适应内容高度并自带复制按钮
                        st.markdown(f"```\n{generated_bullets}\n```")


if __name__ == "__main__":
    main()