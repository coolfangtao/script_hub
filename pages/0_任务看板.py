import streamlit as st
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数

# 自动刷新，每分钟一次，用于更新时间显示
st_autorefresh(interval=1000 * 1, key="clock_refresher")
create_common_sidebar() # 暂时注释掉，以便代码独立运行

# 定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))


# 1. 任务类定义 (Task Class Definition)
class Task:
    """
    一个类，用于表示和管理单个任务。
    (已更新时间跟踪逻辑 和 独立的状态管理)
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
        # --- [!! 新增 !!] ---
        # 独立的状态，决定任务所在的列
        self.status = "未开始"
        # --- [!! 结束 !!] ---

        self.completion_time = None  # 任务完成的时间
        self.task_duration = None  # 任务的【总生命周期】 (创建 -> 完成)

        self.task_comments = []

        # (时间跟踪属性保持不变)
        self.total_active_time = timedelta(0)
        self.last_start_active_time = None

    # [!! 删除 !!] get_status(self) 方法已被 self.status 属性取代

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

    # [!! 新增 !!]
    def set_status(self, new_status):
        """
        显式设置任务状态 (列)，并处理时间跟踪和进度。
        由按钮点击调用。
        """
        if self.status == new_status:
            return

        old_status = self.status
        self.status = new_status
        now = datetime.now(beijing_tz)

        # 状态机：处理有效时长的累积

        # 1. 刚进入“进行中”状态
        if new_status == "进行中" and old_status != "进行中":
            self.last_start_active_time = now
            # st.toast("计时开始 ⏱️")

        # 2. 刚离开“进行中”状态 (例如变为“未开始”或“已完成”)
        elif new_status != "进行中" and old_status == "进行中":
            if self.last_start_active_time:
                active_segment = now - self.last_start_active_time
                self.total_active_time += active_segment
                self.last_start_active_time = None
                # st.toast(f"本段计时结束...")

        # --- 自动更新进度的逻辑 ---
        if new_status == "已完成":
            if old_status != "已完成":
                self.completion_time = now
                self.task_duration = self.completion_time - self.creation_time
                # 自动将进度设为100%
                if self.task_progress != 100:
                    self.task_progress = 100
                st.balloons()

        # 如果从“已完成”状态改回“未完成”
        elif old_status == "已完成" and new_status != "已完成":
            self.completion_time = None
            self.task_duration = None
            # 如果重新打开，且进度是100%，设为90%，以便用户可以调整
            if self.task_progress == 100:
                self.task_progress = 90

        # 如果设为 "未开始" (例如 "挂起")
        elif new_status == "未开始":
            self.completion_time = None
            self.task_duration = None
            # !! 关键：我们【不】修改 self.task_progress
            # 这就允许一个 90% 的任务被“挂起”到“未开始”列

        # st.rerun() # on_click 按钮会自动 rerun

    # [!! 变更 !!]
    def update_progress(self, new_progress):
        """
        由滑块调用：仅更新任务进度百分比。
        会自动触发状态变更(如果需要)。
        """
        if self.task_progress == new_progress:
            return

        self.task_progress = new_progress

        # 自动状态变更
        if new_progress == 100 and self.status != "已完成":
            self.set_status("已完成")
        elif new_progress < 100 and self.status == "已完成":
            # 如果用户从100%拖回，重新打开
            self.set_status("进行中")
        elif new_progress > 0 and self.status == "未开始":
            # 如果用户从0%拖起，自动开始
            self.set_status("进行中")
        elif new_progress == 0 and self.status != "未开始":
            # 如果用户拖到0%，自动设为未开始
            self.set_status("未开始")

    # --- (时间获取函数) ---

    def get_total_lifespan_duration(self):
        """返回任务的【总生命周期】 (从创建到现在，或到完成)"""
        if self.completion_time:
            return self.task_duration
        else:
            return datetime.now(beijing_tz) - self.creation_time

    # [!! 变更 !!]
    def get_total_active_duration(self):
        """返回任务的【总有效工作时长】"""
        current_active_duration = timedelta(0)

        # [!! 变更 !!] 使用 self.status
        if self.status == "进行中" and self.last_start_active_time:
            current_active_duration = datetime.now(beijing_tz) - self.last_start_active_time

        return self.total_active_time + current_active_duration


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

    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if seconds > 0 and not parts:
        parts.append(f"{seconds}秒")

    if not parts:
        return "0秒"

    return f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"


# --- Streamlit 界面 ---

st.set_page_config(
    page_title="每日任务看板",
    page_icon="📋",
    layout="wide"
)

st.title("📋 每日任务看板")
st.markdown("---")

if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- 创建新任务 ---
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

    # [!! 变更 !!] 调用我们重写的 update_progress
    task.update_progress(new_progress)

    # (不需要 st.rerun()，on_change 会自动触发)


# --- 任务卡片显示函数 (Task Card Display Function) ---
def display_task_card(task):
    """
    在UI上显示一个任务卡片。
    """

    with st.expander(f"{task.task_type}", expanded=True):

        st.subheader(task.task_name, divider="rainbow")

        # (时间显示不变)
        lifespan_duration = task.get_total_lifespan_duration()
        lifespan_str = format_timedelta_to_str(lifespan_duration)
        active_duration = task.get_total_active_duration()
        active_str = format_timedelta_to_str(active_duration)

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

        # --- [!! 新增 !!] 状态控制按钮 ---
        cols = st.columns(4)
        with cols[0]:
            if task.status == "未开始":
                st.button("▶️ 开始", key=f"start_{task.task_id}", on_click=task.set_status, args=("进行中",),
                          use_container_width=True)
        with cols[1]:
            if task.status == "进行中":
                st.button("⏸️ 挂起", key=f"pause_{task.task_id}", on_click=task.set_status, args=("未开始",),
                          help="将任务移回“未开始”并暂停计时，不改变当前进度。", use_container_width=True)
        with cols[2]:
            # "完成"按钮现在只在“进行中”时显示
            if task.status == "进行中":
                st.button("✅ 完成", key=f"done_{task.task_id}", on_click=task.set_status, args=("已完成",),
                          use_container_width=True)
        with cols[3]:
            if task.status == "已完成":
                st.button("🔄 重新打开", key=f"reopen_{task.task_id}", on_click=task.set_status, args=("进行中",),
                          use_container_width=True)

        st.write("")  # 增加一点间距

        # 进度条
        st.slider(
            "当前进度（0-100%）",
            min_value=0,
            max_value=100,
            # [!! 变更 !!] value 必须用 task.task_progress，以响应按钮的自动更改
            value=task.task_progress,
            step=10,
            format="%d%%",
            key=f"progress_{task.task_id}",
            help="拖动滑块来更新任务进度。拖到100%会自动完成，拖离100%会自动重新打开。",
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

# [!! 变更 !!] 使用 task.status 来分类
tasks_todo = [t for t in sorted_tasks if t.status == "未开始"]
tasks_doing = [t for t in sorted_tasks if t.status == "进行中"]
tasks_done = [t for t in sorted_tasks if t.status == "已完成"]

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

