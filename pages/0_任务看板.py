import streamlit as st
import json
from itertools import groupby
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from shared.sidebar import create_common_sidebar


# 自动刷新，每分钟一次，用于更新时间显示
st_autorefresh(interval=1000 * 5, key="clock_refresher")
create_common_sidebar() # 暂时注释掉，以便代码独立运行

# 定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))


# 1. 任务类定义 (Task Class Definition)
class Task:
    """
    一个类，用于表示和管理单个任务。
    (已更新时间跟踪逻辑 和 独立的状态管理、以及导入导出功能)
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
        # 独立的状态，决定任务所在的列
        self.status = "未开始"

        self.completion_time = None  # 任务完成的时间点
        self.task_duration = None  # 任务的【总生命周期】 (创建 -> 完成)

        self.task_comments = []

        # (时间跟踪属性)
        self.total_active_time = timedelta(0)  # 仅存储已完成的总时长
        self.last_start_active_time = None  # 当前活动时段的开始时间

        # --- [!! 新增属性 !!] ---
        # 详细记录每一次“进行中”的时间段
        # 列表，存储格式为:
        # { 'start_time': datetime, 'end_time': datetime, 'duration': timedelta, 'stopped_as': str }
        self.active_time_segments = []
        # --- [!! 结束 !!] ---

        # --- [!! 新增方法：序列化与反序列化 !!] ---

    def to_dict(self):
        """将 Task 对象转换为可序列化为 JSON 的字典。"""
        return {
            "task_name": self.task_name,
            "task_type": self.task_type,
            # 将 datetime 对象转换为 ISO 8601 格式的字符串
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "task_id": self.task_id,
            "task_progress": self.task_progress,
            "status": self.status,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            # 将 timedelta 对象转换为总秒数 (浮点数)
            "task_duration_seconds": self.task_duration.total_seconds() if self.task_duration else None,
            "task_comments": [
                {
                    "content": c["content"],
                    "type": c["type"],
                    "time": c["time"].isoformat()
                } for c in self.task_comments
            ],
            "total_active_time_seconds": self.total_active_time.total_seconds(),
            "last_start_active_time": self.last_start_active_time.isoformat() if self.last_start_active_time else None,
            "active_time_segments": [
                {
                    "start_time": s["start_time"].isoformat(),
                    "end_time": s["end_time"].isoformat(),
                    "duration_seconds": s["duration"].total_seconds(),
                    "stopped_as": s["stopped_as"]
                } for s in self.active_time_segments
            ]
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建 Task 对象。"""
        # 先创建一个基础的 Task 对象
        task = cls(data["task_name"], data["task_type"])

        # 逐个恢复属性
        task.creation_time = datetime.fromisoformat(data["creation_time"]) if data.get("creation_time") else None
        task.task_id = data.get("task_id", f"task_{task.creation_time.timestamp()}")  # 兼容旧数据
        task.task_progress = data["task_progress"]
        task.status = data["status"]
        task.completion_time = datetime.fromisoformat(data["completion_time"]) if data.get("completion_time") else None

        if data.get("task_duration_seconds") is not None:
            task.task_duration = timedelta(seconds=data["task_duration_seconds"])

        task.task_comments = [
            {
                "content": c["content"],
                "type": c["type"],
                "time": datetime.fromisoformat(c["time"])
            } for c in data.get("task_comments", [])
        ]

        task.total_active_time = timedelta(seconds=data.get("total_active_time_seconds", 0))

        if data.get("last_start_active_time"):
            task.last_start_active_time = datetime.fromisoformat(data["last_start_active_time"])

        task.active_time_segments = [
            {
                "start_time": datetime.fromisoformat(s["start_time"]),
                "end_time": datetime.fromisoformat(s["end_time"]),
                "duration": timedelta(seconds=s["duration_seconds"]),
                "stopped_as": s["stopped_as"]
            } for s in data.get("active_time_segments", [])
        ]
        return task

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
            st.toast("计时开始 ⏱️")

        # 2. 刚离开“进行中”状态 (例如变为“未开始”或“已完成”)
        elif new_status != "进行中" and old_status == "进行中":
            if self.last_start_active_time:
                active_segment_duration = now - self.last_start_active_time
                self.total_active_time += active_segment_duration

                # --- [!! 新增逻辑：记录时间段 !!] ---
                new_segment = {
                    "start_time": self.last_start_active_time,
                    "end_time": now,
                    "duration": active_segment_duration,
                    # 记录是因何而停止 (挂起 还是 完成)
                    "stopped_as": new_status
                }
                self.active_time_segments.append(new_segment)
                # --- [!! 结束 !!] ---

                self.last_start_active_time = None
                st.toast(f"本段计时结束...")

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
            # (离开“进行中”的逻辑已在上面处理)

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

    def get_total_active_duration(self):
        """返回任务的【总有效工作时长】"""
        current_active_duration = timedelta(0)

        # 加上当前正在进行的活动时间
        if self.status == "进行中" and self.last_start_active_time:
            current_active_duration = datetime.now(beijing_tz) - self.last_start_active_time

        # 总时长 = 已完成的总时长 + 当前进行中的时长
        return self.total_active_time + current_active_duration


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
    # 仅当总时长小于1分钟时才显示秒
    if seconds > 0 and total_seconds < 60:
        parts.append(f"{seconds}秒")
    elif total_seconds >= 60 and seconds > 0:
        # 如果有分钟，秒数会显得累赘，可以注释掉下面这行
        # parts.append(f"{seconds}秒")
        pass

    if not parts:
        return "0秒"

    # 优化显示，例如 "X天X时X分"
    return "".join(parts)


# --- [!! 新函数：初始化应用 !!] ---
def initialize_app():
    """
    设置页面配置、标题和初始化 session_state。
    """
    st.set_page_config(
        page_title="每日任务看板",
        page_icon="📋",
        layout="wide"
    )
    st.title("📋 每日任务看板")
    st.markdown("---")

    if 'tasks' not in st.session_state:
        st.session_state.tasks = []


# --- [!! 新函数：处理任务导入 !!] ---
def handle_tasks_import(uploaded_file):
    """
    处理上传的 JSON 文件，将其中的任务加载到 session_state。
    """
    if uploaded_file is None:
        return
    try:
        # 使用 .read() 来获取文件内容
        tasks_data = json.load(uploaded_file)

        # 为了避免重复导入，我们可以基于 task_id 进行检查
        existing_task_ids = {task.task_id for task in st.session_state.tasks}
        new_tasks_added = 0

        for task_dict in tasks_data:
            if task_dict.get("task_id") not in existing_task_ids:
                task = Task.from_dict(task_dict)
                st.session_state.tasks.append(task)
                new_tasks_added += 1

        if new_tasks_added > 0:
            st.success(f"成功导入 {new_tasks_added} 个新任务！")
            st.rerun()
        else:
            st.info("文件中没有发现新任务。")
    except json.JSONDecodeError:
        st.error("导入失败：文件格式不是有效的 JSON。")
    except Exception as e:
        st.error(f"导入时发生未知错误: {e}")


# --- [!! 新函数：获取导出数据 !!] ---
def get_export_data():
    """
    将 session_state 中的所有任务转换为 JSON 字符串。
    """
    if not st.session_state.tasks:
        return "{}"  # 返回一个空的 JSON 对象

    tasks_as_dicts = [task.to_dict() for task in st.session_state.tasks]
    # indent=2 使得 JSON 文件更具可读性
    return json.dumps(tasks_as_dicts, indent=2)


# --- [!! 重构函数：显示主控制区 (原 display_new_task_form) !!] ---
def display_main_controls():
    """
    显示三栏布局的顶部控制区域：创建、导入、导出。
    """
    st.header("控制面板", divider="gray")
    col1, col2, col3 = st.columns(3)
    # 设置统一的高度
    container_height = 325  # 根据你的内容调整这个值

    # --- 第1栏：创建新任务 ---
    with col1:
        with st.container(border=True, height=container_height):
            st.subheader("🚀 创建新任务", anchor=False)
            with st.form(key="new_task_form", clear_on_submit=True):
                new_task_name = st.text_input("任务名称", placeholder="例如：完成项目报告")
                new_task_type = st.selectbox("任务标签", ["主线任务", "副线任务"])
                if st.form_submit_button("添加任务", use_container_width=True):
                    if new_task_name:
                        new_task = Task(task_name=new_task_name, task_type=new_task_type)
                        st.session_state.tasks.append(new_task)
                        st.success(f"任务 '{new_task_name}' 已添加！")
                        st.rerun()
                    else:
                        st.warning("任务名称不能为空！")

    # --- 第2栏：从文件导入 ---
    with col2:
        with st.container(border=True, height=container_height):
            st.subheader("📥 导入任务", anchor=False)
            uploaded_file = st.file_uploader(
                "选择一个 .json 任务文件",
                type=["json"],
                help="请上传之前从本应用导出的任务文件。"
            )
            if uploaded_file is not None:
                # 当用户上传文件后，立即处理
                handle_tasks_import(uploaded_file)

    # --- 第3栏：导出到文件 ---
    with col3:
        with st.container(border=True, height=container_height):
            st.subheader("📤 导出任务", anchor=False)

            # 准备导出数据
            json_data = get_export_data()

            # 生成文件名
            timestamp = datetime.now(beijing_tz).strftime("%Y%m%d_%H%M%S")
            file_name = f"tasks_export_{timestamp}.json"

            st.download_button(
                label="📥 下载任务到本地",
                data=json_data,
                file_name=file_name,
                mime="application/json",
                help="将当前看板上的所有任务保存为一个 JSON 文件。",
                use_container_width=True,
                # 如果没有任务，则禁用按钮
                disabled=not st.session_state.tasks
            )
            st.caption(f"文件名: {file_name}")


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
    task.update_progress(new_progress)


# --- [!! 新函数：显示状态控制按钮 !!] ---
def display_task_controls(task):
    """
    显示任务的状态控制按钮 (开始、挂起、完成、重新打开)。
    """
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


# --- [!! 新函数：显示评论区 !!] ---
def display_task_comments(task):
    """
    显示单个任务的评论区域 (评论列表在固定高度容器内滚动)。
    """
    st.subheader("任务评论", divider='rainbow')

    # --- 评论创建区域保持不变 ---
    with st.popover("💬 创建评论"):
        with st.form(key=f"comment_form_{task.task_id}", clear_on_submit=True):
            comment_type = st.selectbox("评论类型", ["备注", "问题", "新的"], key=f"ctype_{task.task_id}")
            comment_content = st.text_area("评论内容...", key=f"ctext_{task.task_id}", height=100)

            if st.form_submit_button("提交"):
                if comment_content:
                    st.success("评论已添加！")
                    task.add_comment(comment_content, comment_type)
                    st.rerun()
                else:
                    st.warning("评论内容不能为空")

    # --- 将评论列表放入一个固定高度的 Container ---
    if not task.task_comments:
        # st.info("暂无评论，点击上方“💬 创建评论”来添加第一条吧！")
        pass
    else:
        # 你可以根据需要调整 height 的值
        with st.container(height=250):
            for comment in reversed(task.task_comments):
                icon_map = {"心得": "💡", "问题": "❓", "备注": "📌"}
                color_map = {"心得": "green", "问题": "red", "备注": "blue"}

                comment_icon = icon_map.get(comment['type'], "💬")
                content_color = color_map.get(comment['type'], "gray")

                with st.chat_message(name=comment['type'], avatar=comment_icon):
                    st.markdown(f":{content_color}[{comment['content']}]")
                    st.caption(f"_{comment['time'].strftime('%Y-%m-%d %H:%M')}_")


# --- [!! 新函数：显示工时记录 !!] ---
def display_task_time_logs(task):
    """
    方案三：按日期对历史记录进行分组折叠，体验最佳。
    """
    st.subheader("工时记录", divider='rainbow')

    # 1. 当前计时部分保持不变
    if task.status == "进行中" and task.last_start_active_time:
        start_str = task.last_start_active_time.strftime('%Y-%m-%d %H:%M:%S')
        current_duration = datetime.now(beijing_tz) - task.last_start_active_time
        current_duration_str = format_timedelta_to_str(current_duration)
        st.success(f"**当前:** 正在计时... ({current_duration_str})\n"
                   f"开始于: {start_str}")

    # 2. 按日期对历史记录进行分组
    if not task.active_time_segments:
        if task.status != "进行中":
            st.caption("暂无完整的工时记录。")
    else:
        # vvvvvvvvvvvv 这是核心改动 vvvvvvvvvvvv
        # 使用 groupby 需要先排序，这里我们按倒序排，让最新的日期在最前面
        sorted_segments = sorted(task.active_time_segments, key=lambda s: s['start_time'], reverse=True)

        # 按日期（date）进行分组
        for date, group in groupby(sorted_segments, key=lambda s: s['start_time'].date()):
            group_list = list(group)
            # 计算当天的总时长
            total_duration_today = sum((s['duration'] for s in group_list), timedelta())
            total_duration_str = format_timedelta_to_str(total_duration_today)
            date_str = date.strftime('%Y-%m-%d')

            # 为每一天创建一个 Expander
            with st.expander(f"**{date_str}** - 总计: **{total_duration_str}** ({len(group_list)} 条记录)"):
                for segment in group_list:  # 组内已经是倒序的
                    start_str = segment['start_time'].strftime('%H:%M:%S')
                    end_str = segment['end_time'].strftime('%H:%M:%S')
                    duration_str = format_timedelta_to_str(segment['duration'])
                    status_icon = "⏸️" if segment['stopped_as'] == '未开始' else "✅"
                    st.info(f"**{duration_str}** (从 {start_str} 到 {end_str}) {status_icon}")
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# --- [!! 新增函数：显示任务管理区域 !!] ---
def display_task_management(task):
    """
    显示任务管理操作：编辑、删除等。
    """
    st.divider()
    col_info, col_manage = st.columns([3, 1])

    with col_info:
        st.caption(f"ID: {task.task_id}")
        st.caption(f"创建于: {task.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")

    with col_manage:
        with st.popover("⚙️ 管理"):
            # --- 1. 编辑表单 ---
            with st.form(key=f"edit_form_{task.task_id}"):
                st.subheader("编辑任务", anchor=False)
                edited_task_name = st.text_input("任务名称", value=task.task_name)

                # 获取当前 task_type 的索引，以便正确设置 selectbox 的默认值
                type_options = ["主线任务", "副线任务"]
                try:
                    current_type_index = type_options.index(task.task_type)
                except ValueError:
                    current_type_index = 0  # 如果找不到，默认为第一个

                edited_task_type = st.selectbox(
                    "任务标签",
                    options=type_options,
                    index=current_type_index,
                    key=f"task_type_{task.task_id}"
                )

                if st.form_submit_button("💾 保存更改", use_container_width=True):
                    task.task_name = edited_task_name
                    task.task_type = edited_task_type
                    st.toast(f"任务 '{task.task_name}' 已更新!", icon="✅")
                    st.rerun()

            # --- 2. 删除按钮 ---
            st.divider()
            if st.button("🗑️ 删除任务",
                         type="primary",
                         use_container_width=True,
                         help="此操作不可撤销！",
                         key=f"delete_btn_{task.task_id}"):  # 关键：为每个按钮添加唯一标识
                st.session_state.tasks = [t for t in st.session_state.tasks if t.task_id != task.task_id]
                st.toast(f"任务 '{task.task_name}' 已删除。", icon="🗑️")
                st.rerun()


# --- 任务卡片显示函数 (Task Card Display Function) ---
def display_task_card(task):
    """
    在UI上显示一个任务卡片。
    """

    with st.expander(f"{task.task_name}", expanded=True):

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

        # --- 状态控制按钮 ---
        display_task_controls(task)

        # 进度条
        st.slider(
            "当前进度（0-100%）",
            min_value=0,
            max_value=100,
            value=task.task_progress,
            step=10,
            format="%d%%",
            key=f"progress_{task.task_id}",
            help="拖动滑块来更新任务进度。拖到100%会自动完成，拖离100%会自动重新打开。",
            on_change=handle_progress_change,
            args=(task.task_id,)
        )

        # --- 工时记录 ---
        display_task_time_logs(task)

        # --- 评论区 (保持不变) ---
        display_task_comments(task)

        # --- [!! 调用独立的管理函数 !!] ---
        display_task_management(task)


# --- [!! 修改：优化主卡片布局 !!] ---
def display_kanban_layout():
    """
    显示主看板的三栏布局 (未开始, 进行中, 已完成)。
    """
    col_todo, col_doing, col_done = st.columns(3, gap="large")

    sorted_tasks = sorted(st.session_state.tasks, key=lambda x: x.creation_time, reverse=True)

    tasks_todo = [t for t in sorted_tasks if t.status == "未开始"]
    tasks_doing = [t for t in sorted_tasks if t.status == "进行中"]
    tasks_done = [t for t in sorted_tasks if t.status == "已完成"]

    with col_todo:
        st.header(f"📥 未开始/挂起 ({len(tasks_todo)})", divider="gray")
        with st.container(border=True):
            for task in tasks_todo:
                display_task_card(task)

    with col_doing:
        st.header(f"💻 进行中 ({len(tasks_doing)})", divider="gray")
        with st.container(border=True):
            for task in tasks_doing:
                display_task_card(task)

    with col_done:
        st.header(f"✅ 已完成 ({len(tasks_done)})", divider="gray")
        with st.container(border=True):
            for task in tasks_done:
                display_task_card(task)


# --- [!! 新函数：主函数 !!] ---
def main():
    """
    主函数：按顺序运行应用。
    """
    initialize_app()
    display_main_controls() # <--- 使用重构后的函数
    display_kanban_layout()


# --- 启动应用 ---
if __name__ == "__main__":
    main()
