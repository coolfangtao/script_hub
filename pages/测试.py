import streamlit as st
import pandas as pd
import requests
import json

# --- 配置 ---
st.set_page_config(page_title="我的云端生词本 (Turso版)", layout="wide")


# --- Turso 数据库函数（使用 HTTP API）---

def execute_sql(sql, params=None):
    """使用 Turso HTTP API 执行 SQL 语句"""
    url = st.secrets["db_url"].rstrip('/')  # 移除末尾的斜杠
    auth_token = st.secrets["auth_token"]

    # Turso HTTP API 端点
    api_url = f"{url}/v2/pipeline"

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    # 构建请求体
    statements = [{
        "q": sql,
        "params": params if params else []
    }]

    payload = {
        "requests": statements
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"数据库操作失败: {e}")
        return None


def setup_database():
    """检查并创建生词表（如果不存在）"""
    execute_sql("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            definition TEXT,
            example TEXT
        )
    """)


def load_data():
    """从 Turso 加载所有生词"""
    result = execute_sql("SELECT word, definition, example FROM vocabulary ORDER BY id DESC")

    if result and "results" in result:
        # 解析响应格式
        if result["results"] and "response" in result["results"][0]:
            rows = result["results"][0]["response"].get("result", {}).get("rows", [])
            if rows:
                # 提取数据
                data = []
                for row in rows:
                    data.append({
                        "word": row[0] if len(row) > 0 else "",
                        "definition": row[1] if len(row) > 1 else "",
                        "example": row[2] if len(row) > 2 else ""
                    })
                df = pd.DataFrame(data)
                return df

    return pd.DataFrame(columns=["word", "definition", "example"])


def add_word(word, definition, example):
    """向数据库中添加一个新单词，处理重复情况"""
    sql = "INSERT INTO vocabulary (word, definition, example) VALUES (?, ?, ?)"
    params = [word, definition, example]

    result = execute_sql(sql, params)
    if result is not None:
        # 检查是否插入成功
        if "results" in result and result["results"]:
            if "error" in result["results"][0]:
                error_msg = str(result["results"][0]["error"])
                if "UNIQUE constraint failed" in error_msg:
                    st.warning(f"单词 '{word}' 已经存在于你的生词本中。")
                    return False
                else:
                    st.error(f"数据库错误: {error_msg}")
                    return False
            else:
                st.success(f"单词 '{word}' 已成功添加到云端数据库！")
                return True
    return False


# --- Streamlit 页面布局 ---

st.title("📚 我的云端生词本 (Turso 数据库版)")
st.markdown("---")

# 初始化数据库
setup_database()

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
        add_word(new_word, new_definition, new_example)
    elif submitted:
        st.warning("新单词为必填项！")

        st.markdown("---")
        st.header("我的单词列表")

        vocab_df = load_data()

        if not vocab_df.empty:
            vocab_df.columns = ["单词", "释义", "例句"]
            st.dataframe(vocab_df, use_container_width=True, hide_index=True)
        else:
            st.info("你的生词本还是空的，快去添加第一个单词吧！")