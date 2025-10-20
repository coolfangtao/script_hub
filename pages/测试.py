import streamlit as st
import pandas as pd
import libsql_client
import os

# --- 配置 ---
st.set_page_config(page_title="我的云端生词本 (Turso版)", layout="wide")


# --- Turso 数据库函数 ---

def create_db_connection():
    """使用 Streamlit Secrets 创建并返回一个 Turso 数据库连接"""
    url = st.secrets["turso"]["TURSO_DATABASE_URL"]
    auth_token = st.secrets["turso"]["TURSO_AUTH_TOKEN"]

    # 确保 URL 以 "libsql://" 开头，并且 sync_url 可能需要被设置
    # 对于生产环境，你可能需要更复杂的配置，但对于基础应用这足够了
    return libsql_client.create_client(url=url, auth_token=auth_token)


def setup_database(client):
    """检查并创建生词表（如果不存在）"""
    # 使用 execute() 方法执行 SQL 语句
    client.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            definition TEXT,
            example TEXT
        )
    """)


def load_data(client):
    """从 Turso 加载所有生词"""
    try:
        # Turso/libsql 返回的结果集可以直接转换为 Pandas DataFrame
        rs = client.execute("SELECT word, definition, example FROM vocabulary ORDER BY id DESC")
        # rs.columns 包含了列名, rs.rows 包含了数据
        df = pd.DataFrame(rs.rows, columns=[col for col in rs.columns])
        return df
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        return pd.DataFrame(columns=["word", "definition", "example"])


def add_word(client, word, definition, example):
    """向数据库中添加一个新单词，处理重复情况"""
    # 使用参数化查询 (?) 来防止 SQL 注入，这是最佳实践！
    sql = "INSERT INTO vocabulary (word, definition, example) VALUES (?, ?, ?)"
    params = (word, definition, example)

    try:
        client.execute(sql, params)
        st.success(f"单词 '{word}' 已成功添加到云端数据库！")
        return True
    except Exception as e:
        # 常见错误是 UNIQUE constraint failed，意味着单词已存在
        if "UNIQUE constraint failed" in str(e):
            st.warning(f"单词 '{word}' 已经存在于你的生词本中。")
        else:
            st.error(f"添加单词时出错: {e}")
        return False


# --- Streamlit 页面布局 ---

st.title("📚 我的云端生词本 (Turso 数据库版)")
st.markdown("---")

# 创建数据库连接
db_client = create_db_connection()

# 初始化数据库（创建表）
setup_database(db_client)

# --- 1. 添加新单词的区域 ---
st.header("添加新单词")
with st.form("new_word_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        new_word = st.text_input("新单词", key="word_input")
    with col2:
        new_definition = st.text_input("释义", key="def_input")
    with col3:
        new_example = st.text_input("例句", key="ex_input")

    submitted = st.form_submit_button("✅ 添加到生词本")

    if submitted and new_word:
        add_word(db_client, new_word, new_definition, new_example)
    elif submitted:
        st.warning("“新单词”为必填项！")

# --- 2. 展示所有单词的区域 ---
st.markdown("---")
st.header("我的单词列表")

# 从数据库加载数据
vocab_df = load_data(db_client)

if not vocab_df.empty:
    # 为了更好的显示，我们可以重命名列
    vocab_df.columns = ["单词", "释义", "例句"]
    st.dataframe(vocab_df, use_container_width=True, hide_index=True)
else:
    st.info("你的生词本还是空的，快去添加第一个单词吧！")