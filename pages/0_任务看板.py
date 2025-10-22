import streamlit as st
from datetime import datetime, timedelta, timezone
import pandas as pd
import io

# --- [!! 新增 !!] ---
# 定义北京时间 (UTC+8)
beijing_tz = timezone(timedelta(hours=8))


# ---------------------

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
        # [!! 修改 !!] 使用北京时间
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
            # [!! 修改 !!] 使用北京时间
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
                # [!! 修改 !!] 使用北京时间
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
        elif new_progress > 0 and self.task_status == "未开始":
            self.update_status("进行中")
        elif new_progress == 0 and self.task_status != "未开始":
            self.update_status("未开始")
        elif 0 < new_progress < 100 and self.task_status != "进行中":
            self.update_status("进行中")

    def get_duration_str(self):
        """
        将 task_duration (timedelta) 格式化为可读字符串。
        """
        duration = None

        if self.task_status == "已完成" and self.task_duration:
            duration = self.task_duration
        elif self.task_status == "进行中":
            # [!! 修改 !!] 使用北京时间
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

# 初始化 session_state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- [!! 保持不变 !!] 创建新任务功能区移到主页顶部 ---
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

# --- [!! 新增 !!] 工具栏 ---
st.markdown("---")  # 添加分隔线
col_tools_1, col_tools_2, _ = st.columns([1, 1, 3])  # 布局

with col_tools_1:
    if st.button("🔄 刷新用时", help="手动刷新“进行中”任务的已用时间"):
        st.rerun()


# (Excel 按钮在下面，因为它需要 helper 函数)


# --- 回调函数和辅助函数 ---
# [!! 保持不变 !!]
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


# --- [!! 新增 !!] Excel 导出辅助函数 ---
def generate_excel_export():
    """
    将 session_state 中的任务数据转换为 Excel 文件的内存字节流。
    """
    if not st.session_state.tasks:
        return None

    tasks_list = []
    for task in st.session_state.tasks:
        # 将评论合并为单个字符串
        comments_str = ""
        if task.task_comments:
            comment_lines = []
            for c in task.task_comments:
                time_str = c['time'].strftime('%Y-%m-%d %H:%M')
                comment_lines.append(f"[{c['type']} @ {time_str}]: {c['content']}")
            comments_str = "\n------------------\n".join(comment_lines)

        tasks_list.append({
            "任务ID": task.task_id,
            "任务名称": task.task_name,
            "任务类型": task.task_type,
            "任务状态": task.task_status,
            "任务进度(%)": task.task_progress,
            "创建时间": task.creation_time.strftime('%Y-%m-%d %H:%M:%S'),
            "完成时间": task.completion_time.strftime('%Y-%m-%d %H:%M:%S') if task.completion_time else "N/A",
            "当前用时": task.get_duration_str(),
            "评论详情": comments_str
        })

    df = pd.DataFrame(tasks_list)

    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='任务列表', engine='openpyxl')
    output.seek(0)  # 将指针移回开头
    return output.getvalue()


# ---------------------

# --- [!! 新增 !!] 工具栏的继续部分 (Excel 按钮) ---
with col_tools_2:
    if not st.session_state.tasks:
        # 如果没有任务，禁用按钮
        st.download_button(
            label="📥 导出Excel",
            data="",
            file_name="tasks_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="暂无任务可导出",
            disabled=True
        )
    else:
        # 准备 Excel 数据
        excel_data = generate_excel_export()
        # 获取当前时间
        now_str = datetime.now(beijing_tz).strftime("%Y%m%d_%H%M%S")

        st.download_button(
            label="📥 导出Excel",
            data=excel_data,
            file_name=f"tasks_export_{now_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="点击下载所有任务的Excel报告"
        )


# ---------------------

# --- 任务卡片显示函数 (Task Card Display Function) ---
# [!! 保持不变 !!]
def display_task_card(task):
    """
    在UI上显示一个任务卡片。
    """
    icon = "👔" if task.task_type == "主线任务" else "🤸"

    with st.expander(f"{icon} {task.task_name} (进度: {task.task_progress}%)", expanded=True):

        # 1. 任务详情与控制
        col1, col2 = st.columns(2)

        with col1:
            # 状态选择 (使用 on_change)
            status_options = ["未开始", "进行中", "已完成"]
            current_status_index = status_options.index(task.task_status)

            st.selectbox(
                "状态",
                options=status_options,
                index=current_status_index,
                key=f"status_{task.task_id}",
                on_change=handle_status_change,
                args=(task.task_id,)
            )

        with col2:
            # 进度条 (使用 on_change)
            st.slider(
                "进度 (0-100%)",
                min_value=0,
                max_value=100,
                value=task.task_progress,
                step=10,
                key=f"progress_{task.task_id}",
                on_change=handle_progress_change,
                args=(task.task_id,),
                format="%d%%",  # 美化：添加百分号
                help="拖动滑块更新进度，状态会自动同步"
            )

        # 用时信息
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

                    # --- [!! 修改 !!] 根据类型显示不同颜色 ---
                    if comment['type'] == "感悟":
                        # 使用 markdown 语法 :green[...] 来显示绿色
                        st.markdown(f":green[{comment['content']}]")
                    else:
                        # "问题" 或其他类型为红色
                        st.markdown(f":red[{comment['content']}]")
                    # -------------------------------------

                    st.caption(f"_{comment['time'].strftime('%Y-%m-%d %H:%M')}_")

        # 附加信息
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"ID: {task.task_id}")
        with col4:
            st.markdown(f"创建时间: {task.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")


# --- 主看板布局 (Main Kanban Layout) ---
st.markdown("---")  # 添加分隔线
col_todo, col_doing, col_done = st.columns(3)

# 按创建时间倒序排序任务 (最新的在最前面)
sorted_tasks = sorted(st.session_state.tasks, key=lambda x: x.creation_time, reverse=True)

# 过滤任务到对应的列
tasks_todo = [t for t in sorted_tasks if t.task_status == "未开始"]
tasks_doing = [t for t in sorted_tasks if t.task_status == "进行中"]
tasks_done = [t for t in sorted_tasks if t.task_status == "已完成"]

# 渲染 "未开始" 列
with col_todo:
    st.header(f"📥 未开始 ({len(tasks_todo)})")
    for task in tasks_todo:
        display_task_card(task)

# 渲染 "进行中" 列
with col_doing:
    st.header(f"💻 进行中 ({len(tasks_todo)})")
    for task in tasks_doing:
        display_task_card(task)

# 渲染 "已完成" 列
with col_done:
    st.header(f"✅ 已完成 ({len(tasks_done)})")
    for task in tasks_done:
        display_task_card(task)

