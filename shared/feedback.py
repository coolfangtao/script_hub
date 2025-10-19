# 文件路径: shared/feedback.py

import streamlit as st
import json
from datetime import datetime

# 定义存储反馈的文件路径
FEEDBACK_FILE = "feedback.json"


def load_feedback():
    """从JSON文件中加载历史反馈"""
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 如果文件不存在或为空，返回一个空列表
        return []


def save_feedback(feedback_list):
    """将反馈列表保存到JSON文件"""
    with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 确保中文字符能正确写入
        json.dump(feedback_list, f, indent=4, ensure_ascii=False)


def render_feedback_section():
    """
    渲染完整的反馈功能区，包括提交表单和历史建议列表。
    """
    st.subheader("🙋‍♂️ 建议与反馈箱")

    # 使用st.form来创建一个表单
    with st.form("feedback_form", clear_on_submit=True):
        name = st.text_input("您的称呼 (选填)")
        suggestion = st.text_area("请在此处留下您的建议或遇到的问题...", height=150, placeholder="例如：希望增加一个XX功能，或者某个按钮反应有点慢。")

        # 表单的提交按钮
        submitted = st.form_submit_button("提交建议")

        # 当按钮被点击后，处理表单数据
        if submitted:
            if not suggestion:
                st.warning("建议内容不能为空哦！")
            else:
                # 1. 加载现有的所有反馈
                all_feedback = load_feedback()

                # 2. 准备新的反馈条目
                new_entry = {
                    "name": name if name else "匿名用户",
                    "suggestion": suggestion,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # 3. 将新的反馈添加到列表的最前面
                all_feedback.insert(0, new_entry)

                # 4. 保存更新后的反馈列表
                save_feedback(all_feedback)

                st.success("感谢您的反馈！我们会尽快查看。")

    st.markdown("---")

    # 展示所有已提交的反馈
    st.subheader("📜 大家的建议")

    all_feedback = load_feedback()

    if not all_feedback:
        st.info("目前还没有人提出建议，快来抢占第一个沙发吧！")
    else:
        # 遍历并显示每一条反馈
        for item in all_feedback:
            with st.container(border=True):
                # 使用HTML来让时间戳变成灰色小字
                st.markdown(f"""
                **{item['name']}** <span style='color: grey; font-size: 0.9em;'> · {item['timestamp']}</span>
                """, unsafe_allow_html=True)
                st.write(item['suggestion'])