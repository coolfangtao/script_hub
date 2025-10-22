import streamlit as st
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数

# 自动刷新，每分钟一次，用于更新时间显示
st_autorefresh(interval=1000 * 30, key="clock_refresher")
create_common_sidebar() # 暂时注释掉，以便代码独立运行

# 定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))


# 1. 任务类定义 (Task Class Definition)
class Task:
    """
    一个类，用于表示和管理单个任务。
    (已更新时间跟踪逻辑)
    """

    def __init__(self, task_name, task_type):
        """
        初始化一个新任务。
        """
        self.task_name = task_name
        self.task_type = task_type
        self.creation_time = datetime.now(beijing_tz)
        self.task_id = f"task_{self.creation_time.timestamp()}"
        self.task_progress = 0  # 0 到 100

        self.completion_time = None  # 任务完成的时间
        self.task_duration = None  # 任务的【总生命周期】 (创建 -> 完成)

        self.task_comments = []

        # --- [!! 新增 !!] ---
        # 1. 用于累积所有“进行中”时段的总和
        self.total_active_time = timedelta(0)
        # 2. 标记最近一次进入“进行中”状态的时间点
        self.last_start_active_time = None
        # --- [!! 结束 !!] ---

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
        """
        comment = {
            "content": content,
            "type": comment_type,
            "time": datetime.now(beijing_tz)
        }
        self.task_comments.append(comment)
        st.toast(f"任务 '{self.task_name}' 添加了新评论！", icon="💬")

    # --- [!! 核心变更 !!] ---
    def update_progress(self, new_progress):
        """
        更新任务进度，并智能跟踪“有效工作时长”。
        """
        if self.task_progress == new_progress:
            return

        old_status = self.get_status()
        self.task_progress = new_progress
        new_status = self.get_status()
        now = datetime.now(beijing_tz)

        # 状态机：处理有效时长的累积

        # 1. 刚进入“进行中”状态 (从“未开始”或“已完成”)
        if new_status == "进行中" and old_status != "进行中":
            self.last_start_active_time = now
            # st.toast("计时开始 ⏱️")

        # 2. 刚离开“进行中”状态 (变为“未开始”或“已完成”)
        elif new_status != "进行中" and old_status == "进行中":
            if self.last_start_active_time:
                # 计算刚刚结束的这段时长，并累加
                active_segment = now - self.last_start_active_time
                self.total_active_time += active_segment
                self.last_start_active_time = None
                # st.toast(f"本段计时结束，累积 {active_segment.total_seconds() // 60} 分钟")

        # --- 原有的完成逻辑 ---
        if new_status == "已完成":
            if old_status != "已完成":
                self.completion_time = now
                # task_duration 存储的是【总生命周期】
                self.task_duration = self.completion_time - self.creation_time
                st.balloons()

        # 如果从“已完成”状态改回“未完成”
        elif old_status == "已完成" and new_status != "已完成":
            self.completion_time = None
            self.task_duration = None

        # 如果重置为“未开始”
        elif new_status == "未开始":
            self.completion_time = None
            self.task_duration = None
            # 注意：这里我们【不】重置 self.total_active_time
            # 允许任务在“未开始”和“进行中”之间切换

    # --- [!! 新增 !!] ---
    def get_total_lifespan_duration(self):
        """返回任务的【总生命周期】 (从创建到现在，或到完成)"""
        if self.completion_time:
            # 已完成：创建 -> 完成
            return self.task_duration  # 已在 update_progress 中计算
        else:
            # 未完成：创建 -> 现在
            return datetime.now(beijing_tz) - self.creation_time

    # --- [!! 新增 !!] ---
    def get_total_active_duration(self):
        """返回任务的【总有效工作时长】"""
        current_active_duration = timedelta(0)

        # 如果任务当前“进行中”，计算当前时段的时长
        if self.get_status() == "进行中" and self.last_start_active_time:
            current_active_duration = datetime.now(beijing_tz) - self.last_start_active_time

        # 总有效时长 = 历史上已保存的时长 + 当前时段的时长
        return self.total_active_time + current_active_duration

    # [!! 删除 !!] get_duration_str(self) 方法不再需要，
    # 因为我们现在有两个更精确的方法


# --- [!! 新增 !!] 辅助函数 ---
def format_timedelta_to_str(duration):
    """
    将 timedelta 对象格式化为 "X天 X小时 X分钟 X秒" 的字符串
    """
    if not isinstance(duration, timedelta) or duration.total_seconds() <= 0:
        return "0秒"

    total_seconds = int(duration.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    # 为了简洁，可以只显示有值的部分
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if seconds > 0 and not parts:  # 仅当没有天/小时/分钟时才显示秒
        parts.append(f"{seconds}秒")

    if not parts:
        return "0秒"

    # 返回原始的完整格式
    return f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"


# --- Streamlit 界面 ---

# 页面配置
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
            st.rerun()


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
    回调函数：当进度 slider 发生变化时调用。
    """
    task = get_task_by_id(task_id)
    if not task:
        return

    new_progress = st.session_state[f"progress_{task_id}"]

    # 调用我们重写的 update_progress
    task.update_progress(new_progress)

    # (不需要 st.rerun()，on_change 会自动触发)


# --- 任务卡片显示函数 (Task Card Display Function) ---
def display_task_card(task):
    """
    在UI上显示一个任务卡片。
    """

    with st.expander(f"{task.task_type}", expanded=True):

        st.subheader(task.task_name, divider="rainbow")

        # --- [!! 变更 !!] ---
        # 1. 获取总生命周期 (从创建到现在的总时间)
        lifespan_duration = task.get_total_lifespan_duration()
        lifespan_str = format_timedelta_to_str(lifespan_duration)

        # 2. 获取总有效工作时长 (只计算“进行中”的时间)
        active_duration = task.get_total_active_duration()
        active_str = format_timedelta_to_str(active_duration)

        # 3. 使用两列来显示这两个时间
        col_time1, col_time2 = st.columns(2)
        with col_time1:
            st.metric(
                label="⏱️ 任务总耗时 (有效工作)",
                value=active_str,
                help="这是任务在“进行中”状态下所花费的实际时间总和。每分钟刷新。"
            )
        with col_time2:
            st.metric(
                label="🗓️ 任务生命周期 (自创建)",
                value=lifespan_str,
                help="这是从任务创建开始的总时长。如果任务已完成，则为创建到完成的总时长。每分钟刷新。"
            )
        # --- [!! 结束变更 !!] ---

        # 进度条
        st.slider(
            "当前进度（0-100%）",
            min_value=0,
            max_value=100,
            value=task.task_progress,
            step=10,
            format="%d%%",
            key=f"progress_{task.task_id}",
            help="拖动滑块来更新任务进度",
            on_change=handle_progress_change,
            args=(task.task_id,)
        )

        # --- 评论区 (保持不变) ---
        st.subheader("任务评论", divider='rainbow')

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

        if not task.task_comments:
            pass
        else:
            for comment in reversed(task.task_comments):
                icon_map = {"感悟": "💡", "问题": "❓", "备注": "📌"}
                color_map = {"感悟": "green", "问题": "red", "备注": "blue"}

                comment_icon = icon_map.get(comment['type'], "💬")
                content_color = color_map.get(comment['type'], "gray")

                with st.chat_message(name=comment['type'], avatar=comment_icon):
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
