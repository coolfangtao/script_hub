import streamlit as st
from datetime import datetime, timedelta, timezone
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数
create_common_sidebar()
# 定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))


# 1. 任务类定义 (Task Class Definition)
# [!! 保持不变 !!]
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
        self.task_status = "未开始"  # '未开始', '进行中', '已完成'
        self.task_progress = 0  # 0 到 100

        self.completion_time = None  # 任务完成的时间
        self.task_duration = None  # timedelta 对象

        self.task_comments = []  # 存储评论字典的列表

    def add_comment(self, content, comment_type):
        """
        为任务添加评论。
        comment_type: '感悟' 或 '问题'
        """
        comment = {
            "content": content,
            "type": comment_type,
            "time": datetime.now(beijing_tz)
        }
        self.task_comments.append(comment)
        st.toast(f"任务 '{self.task_name}' 添加了新评论！", icon="💬")

    def update_status(self, new_status):
        """
        更新任务状态，并处理相关逻辑。
        """
        # 防止不必要的更新
        if self.task_status == new_status:
            return

        self.task_status = new_status

        if new_status == "已完成":
            if not self.completion_time:  # 只有在第一次标记为完成时才记录
                self.completion_time = datetime.now(beijing_tz)
                self.task_duration = self.completion_time - self.creation_time
            self.task_progress = 100  # 自动将进度设为100
            st.balloons()  # 完成时庆祝一下

        elif new_status == "进行中":
            self.completion_time = None  # 如果从“已完成”改回，则重置
            self.task_duration = None
            if self.task_progress == 0 or self.task_progress == 100:
                self.task_progress = 10  # 自动设置一个启动进度

        elif new_status == "未开始":
            self.completion_time = None
            self.task_duration = None
            self.task_progress = 0  # 自动将进度归零

    def update_progress(self, new_progress):
        """
        更新任务进度，并自动同步状态。
        """
        # 防止不必要的更新
        if self.task_progress == new_progress:
            return

        self.task_progress = new_progress

        if new_progress == 100:
            self.update_status("已完成")
        elif new_progress > 0:
            self.update_status("进行中")
        elif new_progress == 0:
            self.update_status("未开始")
        elif 0 < new_progress < 100:
            self.update_status("进行中")

    def get_duration_str(self):
        """
        将 task_duration (timedelta) 格式化为可读字符串。
        """
        duration = None

        if self.task_status == "已完成" and self.task_duration:
            duration = self.task_duration
        elif self.task_status == "进行中":
            duration = datetime.now(beijing_tz) - self.creation_time
        elif self.task_status == "未开始":
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
    page_title="个人任务看板",
    page_icon="📋",
    layout="wide"
)

st.title("📋 个人任务看板")
st.markdown("---")

# 初始化 session_state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- 侧边栏：创建新任务 (Sidebar: Create New Task) ---
# [!! 保持不变 !!]
with st.expander("🚀 点击创建新任务"):
    with st.form(key="new_task_form", clear_on_submit=True):
        new_task_name = st.text_input("任务名称", placeholder="例如：完成项目报告")
        new_task_type = st.selectbox("任务类型", ["主线任务", "副线任务"])

        submit_button = st.form_submit_button(label="添加任务")

        if submit_button and new_task_name:
            new_task = Task(task_name=new_task_name, task_type=new_task_type)
            st.session_state.tasks.append(new_task)
            st.success(f"任务 '{new_task_name}' 已添加！")
            st.rerun() # 添加 Rerun 以便立即刷新看板


# --- [!! 优化 !!] ---
# 1. 将回调函数和辅助函数放在主逻辑区

def get_task_by_id(task_id):
    """
    辅助函数：根据ID从 session_state 中查找任务对象。
    """
    for task in st.session_state.tasks:
        if task.task_id == task_id:
            return task
    return None


def handle_status_change(task_id):
    """
    回调函数：当状态 selectbox 发生变化时调用。
    """
    task = get_task_by_id(task_id)
    if not task:
        return

    # 从 session_state 中获取 selectbox 的新值
    new_status = st.session_state[f"status_{task_id}"]
    task.update_status(new_status)


def handle_progress_change(task_id):
    """
    回调函数：当进度 slider 发生变化时调用。
    """
    task = get_task_by_id(task_id)
    if not task:
        return

    # 从 session_state 中获取 slider 的新值
    new_progress = st.session_state[f"progress_{task_id}"]
    task.update_progress(new_progress)


# ---------------------


# --- 任务卡片显示函数 (Task Card Display Function) ---
def display_task_card(task):
    """
    在UI上显示一个任务卡片。
    """
    icon = "👔" if task.task_type == "主线任务" else "🤸"

    with st.expander(f"{icon} {task.task_name} (进度: {task.task_progress}%)", expanded=True):

        # 1. 任务详情与控制
        st.subheader("任务进度", divider='rainbow')
        col1, col2 = st.columns(2)

        with col1:
            # 状态选择
            status_options = ["未开始", "进行中", "已完成"]
            current_status_index = status_options.index(task.task_status)

            # --- [!! 优化 !!] ---
            # 使用 on_change 回调函数
            # 不再需要 if new_status != ... 的判断
            st.selectbox(
                "状态",
                options=status_options,
                index=current_status_index,
                key=f"status_{task.task_id}",  # key 是必须的
                on_change=handle_status_change,  # 指定回调
                args=(task.task_id,)  # 传递参数给回调
            )
            # ---------------------

        with col2:
            # 进度条
            st.slider(
                "进度",
                min_value=0,
                max_value=100,
                value=task.task_progress,  # 'value' 确保滑块在“进行中”时显示 10%
                step=10,
                format="%d%%",
                key=f"progress_{task.task_id}",  # key 是必须的
                help="拖动滑块来更新任务进度",
                on_change=handle_progress_change,  # 指定回调
                args=(task.task_id,)  # 传递参数给回调
            )
            # ---------------------

        # 用时信息 (不变)
        if task.task_status == "已完成":
            st.success(f"**总用时:** {task.get_duration_str()}")
        elif task.task_status == "进行中":
            st.info(f"**已用时:** {task.get_duration_str()}")

        # --- [!! 评论区优化 !!] ---
        st.subheader("任务评论", divider='rainbow')

        # 1. 使用 st.popover 来隐藏“添加评论”表单
        with st.popover("💬 添加新评论"):
            with st.form(key=f"comment_form_{task.task_id}", clear_on_submit=True):
                comment_type = st.selectbox("评论类型", ["感悟", "问题"], key=f"ctype_{task.task_id}")
                comment_content = st.text_area("评论内容...", key=f"ctext_{task.task_id}", height=100)

                if st.form_submit_button("提交"):
                    if comment_content:
                        task.add_comment(comment_content, comment_type)
                        st.rerun()
                    else:
                        st.warning("评论内容不能为空")

        # 2. 优化“暂无评论”的提示
        if not task.task_comments:
            st.info("还没有评论，快来添加第一条感悟或问题吧！", icon="📝")
        else:
            # 倒序显示，最新评论在最上面
            for comment in reversed(task.task_comments):
                comment_icon = "💡" if comment['type'] == "感悟" else "❓"
                with st.chat_message(name=comment['type'], avatar=comment_icon):
                    st.write(comment['content'])
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

tasks_todo = [t for t in sorted_tasks if t.task_status == "未开始"]
tasks_doing = [t for t in sorted_tasks if t.task_status == "进行中"]
tasks_done = [t for t in sorted_tasks if t.task_status == "已完成"]

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
