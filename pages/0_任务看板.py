import streamlit as st
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数
st_autorefresh(interval=1000, key="clock_refresher")
create_common_sidebar()

# 定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))


# 1. 任务类定义 (Task Class Definition)
class Task:
    """
    一个类，用于表示和管理单个任务。
    """

    def __init__(self, task_name, task_type):
        """
        初始化一个新任务。
        """
        self.task_name = task_name
        self.task_type = task_type  # '主线任务' 或 '副线任务'
        self.creation_time = datetime.now(beijing_tz)
        # 使用高精度的Unix时间戳作为唯一ID
        self.task_id = f"task_{self.creation_time.timestamp()}"
        self.task_progress = 0  # 0 到 100

        self.completion_time = None  # 任务完成的时间
        self.task_duration = None  # timedelta 对象

        self.task_comments = []  # 存储评论字典的列表

    def get_status(self):
        """
        根据进度派生任务状态。
        """
        if self.task_progress == 0:
            return "未开始"
        elif self.task_progress == 100:
            return "已完成"
        else:
            return "进行中"

    def add_comment(self, content, comment_type):
        """
        为任务添加评论。
        comment_type: '感悟' 或 '问题' 或 '备注'
        """
        comment = {
            "content": content,
            "type": comment_type,
            "time": datetime.now(beijing_tz)
        }
        self.task_comments.append(comment)
        st.toast(f"任务 '{self.task_name}' 添加了新评论！", icon="💬")


    def update_progress(self, new_progress):
        """
        更新任务进度，并自动处理相关逻辑（如完成时间）。
        """
        # 防止不必要的更新
        if self.task_progress == new_progress:
            return

        # 获取旧状态，用于比较
        old_status = self.get_status()

        self.task_progress = new_progress

        # 获取新状态
        new_status = self.get_status()

        if new_status == "已完成":
            if old_status != "已完成":
                self.completion_time = datetime.now(beijing_tz)
                self.task_duration = self.completion_time - self.creation_time
                st.balloons()

        elif new_status == "进行中":
            # 如果是从“已完成”或“未开始”变来的，重置完成时间
            if old_status != "进行中":
                self.completion_time = None
                self.task_duration = None

        elif new_status == "未开始":
            # 如果是从其他状态变来的，重置完成时间
            if old_status != "未开始":
                self.completion_time = None
                self.task_duration = None

    def get_duration_str(self):
        """
        使用 self.get_status() 代替 self.task_status
        """
        duration = None
        current_status = self.get_status()  # [!! 变更 !!]

        if current_status == "已完成" and self.task_duration:
            duration = self.task_duration
        elif current_status == "进行中":
            duration = datetime.now(beijing_tz) - self.creation_time
        elif current_status == "未开始":
            return "尚未开始"

        if duration is None:
            return "N/A"

        total_seconds = int(duration.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"


# --- Streamlit 界面 ---

# 页面配置 (Page Configuration)
st.set_page_config(
    page_title="每日任务看板",
    page_icon="📋",
    layout="wide"
)

st.title("📋 每日任务看板")
st.markdown("---")

# 初始化 session_state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- 创建新任务 (Sidebar: Create New Task) ---
with st.expander("🚀 点击创建新任务"):
    with st.form(key="new_task_form", clear_on_submit=True):
        new_task_name = st.text_input("任务名称", placeholder="例如：完成项目报告")
        new_task_type = st.selectbox("任务类型", ["主线任务", "副线任务"])

        submit_button = st.form_submit_button(label="添加任务")

        if submit_button and new_task_name:
            new_task = Task(task_name=new_task_name, task_type=new_task_type)
            st.session_state.tasks.append(new_task)
            st.success(f"任务 '{new_task_name}' 已添加！")
            st.rerun()  # 添加 Rerun 以便立即刷新看板


def get_task_by_id(task_id):
    """
    辅助函数：根据ID从 session_state 中查找任务对象。
    """
    for task in st.session_state.tasks:
        if task.task_id == task_id:
            return task
    return None


def handle_progress_change(task_id):
    """
    [!! 变更 !!] 回调函数：当进度 slider 发生变化时调用。
    """
    task = get_task_by_id(task_id)
    if not task:
        return

    # 1. 从 session_state 中获取 slider 的新值
    new_progress = st.session_state[f"progress_{task_id}"]

    # 2. 更新 task 对象 (这也会自动更新完成时间等)
    task.update_progress(new_progress)


# ---------------------


# --- 任务卡片显示函数 (Task Card Display Function) ---
def display_task_card(task):
    """
    在UI上显示一个任务卡片。
    """

    with st.expander(f"{task.task_type}", expanded=True):

        # 1. 任务详情与控制
        st.subheader(task.task_name, divider="rainbow")

        # 用时信息
        current_status = task.get_status()
        duration_str = task.get_duration_str()

        if current_status == "已完成":
            # 对于已完成任务，使用 st.metric 显示总用时
            # help 参数可以在鼠标悬停时显示提示信息
            st.metric(
                label="✅ 总用时",
                value=duration_str,
                help="任务已完成，这是记录的总耗时。"
            )
        elif current_status == "进行中":
            # 对于进行中任务，同样使用 st.metric，但标签不同
            st.metric(
                label="⏳ 已用时",
                value=duration_str,
                help="任务正在进行中，这是目前已花费的时间。"
            )

        st.slider(
            "当前进度（0-100%）",
            min_value=0,
            max_value=100,
            value=task.task_progress,  # 'value' 同样只在初次渲染时起作用
            step=10,
            format="%d%%",
            key=f"progress_{task.task_id}",  # key 是必须的
            help="拖动滑块来更新任务进度",
            on_change=handle_progress_change,  # 指定回调
            args=(task.task_id,)  # 传递参数给回调
        )

        # --- [!! 评论区优化 !!] --- (保持不变)
        st.subheader("任务评论", divider='rainbow')

        # 1. 使用 st.popover 来隐藏“添加评论”表单
        with st.popover("💬 创建评论"):
            with st.form(key=f"comment_form_{task.task_id}", clear_on_submit=True):
                comment_type = st.selectbox("评论类型", ["感悟", "问题", "备注"], key=f"ctype_{task.task_id}")
                comment_content = st.text_area("评论内容...", key=f"ctext_{task.task_id}", height=100)

                if st.form_submit_button("提交"):
                    if comment_content:
                        task.add_comment(comment_content, comment_type)
                        st.rerun()
                    else:
                        st.warning("评论内容不能为空")

        # 2. 优化“暂无评论”的提示
        if not task.task_comments:
            pass
        else:
            # 倒序显示，最新评论在最上面
            for comment in reversed(task.task_comments):
                if comment['type'] == "感悟":
                    comment_icon = "💡"
                    content_color = "green"
                elif comment['type'] == "问题":
                    comment_icon = "❓"
                    content_color = "red"
                elif comment['type'] == "备注":  # 新增的类型
                    comment_icon = "📌"
                    content_color = "blue"

                with st.chat_message(name=comment['type'], avatar=comment_icon):
                    # 使用 markdown 语法来显示带颜色的内容
                    st.markdown(f":{content_color}[{comment['content']}]")
                    st.caption(f"_{comment['time'].strftime('%Y-%m-%d %H:%M')}_")

        # 附加信息 (不变)
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"ID: {task.task_id}")
        with col4:
            st.markdown(f"创建时间: {task.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")


# --- 主看板布局 (Main Kanban Layout) ---
col_todo, col_doing, col_done = st.columns(3)

sorted_tasks = sorted(st.session_state.tasks, key=lambda x: x.creation_time, reverse=False)

# [!! 变更 !!] 使用 task.get_status() 来分类
tasks_todo = [t for t in sorted_tasks if t.get_status() == "未开始"]
tasks_doing = [t for t in sorted_tasks if t.get_status() == "进行中"]
tasks_done = [t for t in sorted_tasks if t.get_status() == "已完成"]

with col_todo:
    st.header(f"📥 未开始 ({len(tasks_todo)})")
    for task in tasks_todo:
        display_task_card(task)

with col_doing:
    st.header(f"💻 进行中 ({len(tasks_doing)})")
    for task in tasks_doing:
        display_task_card(task)

with col_done:
    st.header(f"✅ 已完成 ({len(tasks_done)})")
    for task in tasks_done:
        display_task_card(task)
