import streamlit as st
import pandas as pd
import requests


# -------------------------------------------------------------------
# 数据库操作函数 (您提供的代码)
# -------------------------------------------------------------------

def fix_db_url(url):
    """修复数据库URL格式"""
    if url.startswith('libsql://'):
        return url.replace('libsql://', 'https://')
    return url


def execute_sql(sql, params=None):
    """执行SQL语句"""
    try:
        # 从Streamlit secrets中获取数据库URL和认证令牌
        url = fix_db_url(st.secrets["feedback_db_url"]).rstrip('/')
        auth_token = st.secrets["feedback_db_token"]

        api_url = f"{url}/v2/pipeline"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

        # 构建正确的参数格式
        if params is None:
            args = []
        else:
            args = []
            for param in params:
                if param is None:
                    args.append({"type": "null"})
                else:
                    # 使用正确的参数格式
                    args.append({"type": "text", "value": str(param)})

        payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": args
                    }
                }
            ]
        }

        response = requests.post(api_url, json=payload, headers=headers)

        if response.status_code != 200:
            st.error(f"HTTP {response.status_code}: {response.text}")
            return None

        return response.json()

    except Exception as e:
        st.error(f"数据库错误: {e}")
        return None


def setup_database():
    """初始化数据库表"""
    result = execute_sql("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return result is not None


def load_feedback():
    """加载所有反馈"""
    result = execute_sql("""
        SELECT name, message, created_at 
        FROM feedback 
        ORDER BY created_at DESC
    """)

    if result and "results" in result and result["results"]:
        first_result = result["results"][0]
        if "response" in first_result and "result" in first_result["response"]:
            rows = first_result["response"]["result"].get("rows", [])
            if rows:
                data = []
                for row in rows:
                    if isinstance(row, list):
                        processed_row = []
                        for item in row:
                            if isinstance(item, dict) and 'value' in item:
                                processed_row.append(item['value'])
                            else:
                                processed_row.append(item)

                        if len(processed_row) >= 3:
                            data.append({
                                "称呼": processed_row[0] if processed_row[0] is not None else "",
                                "反馈内容": processed_row[1] if processed_row[1] is not None else "",
                                "提交时间": processed_row[2] if processed_row[2] is not None else ""
                            })
                return pd.DataFrame(data)

    return pd.DataFrame(columns=["称呼", "反馈内容", "提交时间"])


def add_feedback(name, message):
    """添加新反馈"""
    if not name.strip():
        st.warning("姓名不能为空")
        return False

    if not message.strip():
        st.warning("反馈内容不能为空")
        return False

    name_str = name.strip()
    message_str = message.strip()

    result = execute_sql(
        "INSERT INTO feedback (name, message) VALUES (?, ?)",
        [name_str, message_str]
    )

    if result is None:
        return False

    if "results" in result and result["results"]:
        first_result = result["results"][0]
        if "error" in first_result and first_result["error"]:
            error_msg = str(first_result["error"])
            st.error(f"提交失败: {error_msg}")
            return False
        else:
            st.success("反馈已成功提交！感谢您的宝贵意见！")
            return True

    return False


# -------------------------------------------------------------------
# Streamlit 界面函数
# -------------------------------------------------------------------

def show_feedback_module():
    """
    在Streamlit页面上显示完整的用户反馈模块。
    这个函数将被主应用导入和调用。
    """

    # --- 显示历史反馈 (美化版本) ---
    st.header("✍️ 用户反馈")
    feedback_df = load_feedback()

    if feedback_df.empty:
        st.info("暂无反馈记录，期待您的第一条建议！")
    else:
        # 遍历DataFrame中的每一行，为每一条反馈创建一个卡片
        for index, row in feedback_df.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    # 显示称呼，并加粗
                    st.markdown(f"**{row['称呼']}**")
                with col2:
                    # 显示提交时间，设为灰色、小字体并右对齐
                    st.markdown(f"<p style='text-align: right; color: grey; font-size: 0.9em;'>{row['提交时间']}</p>",
                                unsafe_allow_html=True)

                # 显示反馈内容
                st.write(row['反馈内容'])

            # 在卡片之间增加一点小间距
            st.empty()

    st.subheader("提交你的反馈")
    st.write("我们非常重视您的意见，请在这里留下您的反馈和建议。")

    # 使用表单来收集用户输入 (保持不变)
    with st.form(key='feedback_form', clear_on_submit=True):
        name = st.text_input("您的称呼")
        message = st.text_area("您的反馈内容", height=150)
        submitted = st.form_submit_button("提交反馈")
        if submitted:
            add_feedback(name, message)