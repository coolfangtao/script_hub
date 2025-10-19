# 文件路径: shared/feedback.py

import streamlit as st
from datetime import datetime
import pandas as pd

# 初始化数据库连接
conn = st.connection('turso', type='sql')


def init_db():
    """初始化数据库，如果 feedback 表不存在则创建它"""
    with conn.session as s:
        s.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                suggestion TEXT,
                timestamp TEXT
            );
        """)
        s.commit()


def load_feedback_from_db():
    """从数据库加载所有反馈，并按时间倒序排列"""
    df = conn.query('SELECT * FROM feedback ORDER BY timestamp DESC;')
    # 将DataFrame转换为字典列表，方便遍历
    return df.to_dict('records')


def save_feedback_to_db(name, suggestion):
    """将新的反馈条目保存到数据库"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 使用参数化查询来防止SQL注入
    with conn.session as s:
        s.execute(
            'INSERT INTO feedback (name, suggestion, timestamp) VALUES (:name, :suggestion, :timestamp);',
            params=dict(name=name, suggestion=suggestion, timestamp=timestamp)
        )
        s.commit()


def render_feedback_section():
    """
    渲染完整的反馈功能区，现在使用数据库进行存储。
    """
    # 确保数据库和表已经创建
    init_db()

    st.subheader("🙋‍♂️ 建议与反馈箱")

    with st.form("feedback_form", clear_on_submit=True):
        name = st.text_input("您的称呼 (选填)")
        suggestion = st.text_area("请在此处留下您的建议或遇到的问题...", height=150)

        submitted = st.form_submit_button("提交建议")
        if submitted:
            if not suggestion:
                st.warning("建议内容不能为空哦！")
            else:
                # 调用新的保存函数
                save_feedback_to_db(name if name else "匿名用户", suggestion)
                st.success("感谢您的反馈！您的建议已永久保存。")

    st.markdown("---")
    st.subheader("📜 大家的建议")

    # 从数据库加载反馈
    all_feedback = load_feedback_from_db()

    if not all_feedback:
        st.info("目前还没有人提出建议，快来抢占第一个沙发吧！")
    else:
        for item in all_feedback:
            with st.container(border=True):
                st.markdown(f"""
                **{item['name']}** <span style='color: grey; font-size: 0.9em;'> · {item['timestamp']}</span>
                """, unsafe_allow_html=True)
                st.write(item['suggestion'])