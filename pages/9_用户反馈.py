import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(page_title="用户反馈系统", layout="wide")


def fix_db_url(url):
    """修复数据库URL格式"""
    if url.startswith('libsql://'):
        return url.replace('libsql://', 'https://')
    return url


def execute_sql(sql, params=None):
    """执行SQL语句"""
    try:
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
                    data.append({
                        "name": row[0],
                        "message": row[1] if len(row) > 1 else "",
                        "created_at": row[2] if len(row) > 2 else ""
                    })
                return pd.DataFrame(data)

    return pd.DataFrame(columns=["name", "message", "created_at"])


def add_feedback(name, message):
    """添加新反馈"""
    if not name.strip():
        st.warning("姓名不能为空")
        return False

    if not message.strip():
        st.warning("反馈内容不能为空")
        return False

    # 处理空值
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
            st.success("反馈已成功提交！")
            return True

    return False


# --- 页面布局 ---
st.title("💬 用户反馈系统")
st.markdown("---")

# 侧边栏 - 数据库信息
st.sidebar.header("数据库设置")
if st.sidebar.button("🔄 测试数据库连接"):
    result = execute_sql("SELECT 1")
    if result:
        st.sidebar.success("✅ 数据库连接成功！")
    else:
        st.sidebar.error("❌ 数据库连接失败")

if st.sidebar.button("🗃️ 初始化数据库表"):
    if setup_database():
        st.sidebar.success("✅ 数据库表初始化成功！")
    else:
        st.sidebar.error("❌ 数据库表初始化失败")

# 留言区部分
st.header("📝 留言区")

with st.form("feedback_form", clear_on_submit=True):
    col1, col2 = st.columns([1, 2])

    with col1:
        user_name = st.text_input("姓名 *", placeholder="请输入您的姓名", key="name_input")
    with col2:
        user_message = st.text_area("反馈内容 *", placeholder="请输入您的反馈意见", height=100, key="message_input")

    submitted = st.form_submit_button("✅ 提交反馈")

    if submitted:
        if user_name and user_message:
            if add_feedback(user_name, user_message):
                st.rerun()
        else:
            st.warning("请填写姓名和反馈内容！")

st.markdown("---")

# 反馈区部分
st.header("💭 用户反馈区")

if st.button("🔄 刷新反馈"):
    st.rerun()

# 加载并显示数据
feedback_df = load_feedback()

if not feedback_df.empty:
    st.write(f"**共 {len(feedback_df)} 条反馈**")

    # 格式化显示
    display_df = feedback_df.copy()
    display_df.columns = ["用户姓名", "反馈内容", "提交时间"]

    # 美化显示
    for index, row in display_df.iterrows():
        with st.container():
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #1f77b4;">{row['用户姓名']}</h4>
                    <span style="color: #666; font-size: 0.9em;">{row['提交时间']}</span>
                </div>
                <p style="margin: 10px 0 0 0; line-height: 1.5;">{row['反馈内容']}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
else:
    st.info("📝 暂无用户反馈，快来留下第一条反馈吧！")