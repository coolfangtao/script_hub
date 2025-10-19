# --- 2. Streamlit 页面主函数 (修改后) ---

def main():
    """
    Streamlit应用的主函数。
    """
    st.set_page_config(page_title="ASIN反查关键词分析面板", layout="wide")

    st.title("📊 ASIN反查关键词分析面板")

    st.header("上传数据文件")
    uploaded_file = st.file_uploader("请在此处上传您的ASIN反查关键词Excel文件以开始分析", type=["xlsx"])

    # --- 核心修改：使用 st.session_state ---

    # 1. 当有新文件上传时，处理并存入 session_state
    if uploaded_file is not None:
        # 加载数据
        df = load_data(uploaded_file)
        if df is not None:
            # 解析文件名
            country, asin, keyword_count, date = parse_filename(uploaded_file.name)

            # 将数据和文件信息存储到 session_state 中
            # 这样即使用户离开页面再回来，这些数据也会被保留
            st.session_state['processed_data'] = df
            st.session_state['file_info'] = {
                'name': uploaded_file.name,
                'country': country,
                'asin': asin,
                'keyword_count': keyword_count,
                'date': date
            }
            # 清除 uploaded_file 变量，防止重复处理，但这不是必须的
            # uploaded_file = None

    # 2. 检查 session_state 中是否有已处理的数据，如果有，则显示内容
    if 'processed_data' in st.session_state:
        # 从 session_state 中获取数据
        df = st.session_state['processed_data']
        info = st.session_state['file_info']

        # --- 文件处理与数据展示 ---
        if info['asin']:
            st.success(
                f"文件解析成功！当前分析的文件: **{info['name']}** | 国家: **{info['country']}**, ASIN: **{info['asin']}**, 关键词总数: **{info['keyword_count']}**, 导出日期: **{info['date']}**")
        else:
            st.warning("无法从文件名中解析信息，请检查文件名格式是否为 'ReverseASIN-国家-ASIN(数量)-日期.xlsx'")

        # 显示核心指标
        display_metrics(df.copy())  # 传入一个副本以避免修改缓存中的数据

        st.markdown("---")  # 分隔线

        # 创建两个并排的列用于放置图表
        col1, col2 = st.columns(2)
        with col1:
            plot_top_keywords_by_traffic(df.copy())  # 传入副本
        with col2:
            plot_keyword_type_distribution(df.copy())  # 传入副本

        # 词云图
        generate_word_cloud(df.copy())  # 传入副本

        st.markdown("---")  # 分隔线

        # 显示可交互的完整数据表
        st.subheader("详细数据表")
        st.dataframe(df)

    # 3. 如果没有任何缓存数据，显示欢迎信息
    else:
        st.info("👋 欢迎使用！请上传文件以开始分析。")


# --- 3. 应用启动 ---

if __name__ == "__main__":
    main()