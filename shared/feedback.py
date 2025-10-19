import streamlit as st
# 错误修正：Turso Python 客户端的正确包名是 libsql_client
import libsql_client as turso_client
import datetime
import asyncio  # 导入 asyncio 库来处理异步操作


# --- 数据库连接函数 ---
def connect_to_db():
    """
    建立并返回一个Turso数据库客户端连接。
    优先从st.secrets中获取凭证，如果失败则使用硬编码的备用值。
    """
    try:
        url = st.secrets.get("TURSO_DATABASE_URL")
        auth_token = st.secrets.get("TURSO_AUTH_TOKEN")

        if not url:
            url = "libsql://your-feedback-db-coolfangtao.aws-ap-northeast-1.turso.io"
        if not auth_token:
            auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjA4NzM5MjUsImlkIjoiODJlZjRkOTctMTEwYy00MjFiLTk1ZTQtNjViNzFkMjQ4ZjgzIiwicmlkIjoiODYxNTdhM2EtYjM4Yi00NzFkLWJjNzAtMDRlZmM0YjVjZTY3In0.k7MFDokocMs-Mhk0reor8i3YLu0Jr3KoES8oawi7UcDx6tVh0xVRiEWLu1iZOmH0kPIh-qHWJiMYtGRjNVv7Dw"

        # 解决方案：移除 in_thread 参数，我们将通过 asyncio 手动管理异步调用
        return turso_client.create_client(url=url, auth_token=auth_token)
    except Exception as e:
        st.error(f"数据库连接失败，请检查配置。错误: {e}")
        return None


# --- 初始化数据库 (异步版本) ---
async def init_db_async(client):
    """
    (异步) 检查并创建feedback表（如果它不存在）。
    """
    if client:
        try:
            # 使用 await 关键字等待异步操作完成
            await client.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    feedback_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        except Exception as e:
            st.error(f"数据库表初始化失败: {e}")


# --- 渲染反馈提交表单 ---
def render_feedback_form(client):
    """
    在页面上渲染一个用于提交新反馈的表单。
    表单提交的数据库操作将是异步的。
    """
    st.subheader("💬 提点建议或反馈")
    st.write("你的每个建议都是我们前进的动力！无论是功能建议、Bug报告还是使用体验，都欢迎你告诉我们。")

    with st.form(key="feedback_form", clear_on_submit=True):
        name = st.text_input("你的称呼 (选填)")
        feedback_type = st.selectbox(
            "反馈类型",
            options=["💡 功能建议", "🐞 Bug 反馈", "🤔 使用体验", "💬 其他"],
            index=0, help="请选择最贴合你想法的类型。"
        )
        message = st.text_area("详细内容", placeholder="请在这里写下你的想法...", height=150)
        submitted = st.form_submit_button("🚀 提交反馈")

        if submitted:
            if not message or not message.strip():
                st.warning("反馈内容不能为空哦！")
            else:
                try:
                    # 创建一个嵌套的异步函数来执行数据库插入
                    async def submit_data():
                        await client.execute(
                            "INSERT INTO feedback (name, feedback_type, message) VALUES (?, ?, ?)",
                            (name if name else "匿名用户", feedback_type, message)
                        )

                    # 使用 asyncio.run() 来执行这个异步任务
                    asyncio.run(submit_data())
                    st.success("感谢你的反馈！我们已经收到了，会尽快查看。")
                except Exception as e:
                    st.error(f"提交失败，请稍后再试。错误: {e}")


# --- 展示历史反馈 (异步版本) ---
async def display_feedback_wall_async(client):
    """
    (异步) 从数据库查询并以可展开列表的形式显示所有历史反馈。
    """
    st.subheader("📣 大家的建议墙")
    try:
        # 使用 await 关键字等待异步查询完成
        results = await client.execute(
            "SELECT name, feedback_type, message, created_at FROM feedback ORDER BY created_at DESC")

        if not results.rows:
            st.info("还没有人提出建议，快来抢占第一个沙发！")
            return

        for row in results.rows:
            name, feedback_type, message, created_at = row
            try:
                dt_object = datetime.datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                formatted_time = dt_object.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                formatted_time = str(created_at) if created_at else "未知时间"

            with st.expander(f"**{feedback_type}** 来自 **{name}** - *{formatted_time}*"):
                st.write(message)

    except Exception as e:
        st.error(f"加载历史反馈失败: {e}")


# --- 主渲染函数 ---
def render_feedback_section():
    """
    渲染整个反馈区的主函数，包括表单和历史记录墙。
    """
    client = connect_to_db()
    if client:
        try:
            # 在同步函数中使用 asyncio.run() 来调用异步的初始化和数据展示函数
            asyncio.run(init_db_async(client))
            render_feedback_form(client)
            st.markdown("---")
            asyncio.run(display_feedback_wall_async(client))
        finally:
            # 确保客户端连接在使用后被关闭
            client.close()

