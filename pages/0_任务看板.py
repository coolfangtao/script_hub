# 0_任务看板.py
import streamlit as st
import json
import os
import tempfile
import pandas as pd
import plotly.express as px
from itertools import groupby
from datetime import datetime, timedelta, date, time
from streamlit_autorefresh import st_autorefresh
from shared.sidebar import create_common_sidebar
from shared.config import GlobalConfig
from github import Github, UnknownObjectException, GithubException


# =========================================================================================
# 1. 配置模块 (Configuration)
# =========================================================================================

class Config(GlobalConfig):
    """
    [重构] 精简后的配置类。
    只包含多处复用或定义核心行为的常量，一次性的UI文本已被移入其使用位置。
    """

    def __init__(self):
        super().__init__()
        self.BEIJING_TZ = self.APP_TIMEZONE

        # --- 核心文件与路径配置 ---
        self.LOCAL_DATA_FILE_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../private_data/', 'local_tasks_data.json')
        )
        self.DATA_FILE_NAME = "cloud_tasks_data.json"

        # --- 核心应用行为配置 ---
        self.AUTO_REFRESH_INTERVAL_MS = 1000 * 60
        self.PAGE_TITLE = "每日任务看板"
        self.PAGE_ICON = "📋"

        # --- 核心数据模型常量 (多处使用) ---
        self.STATUS_TODO = "未开始"
        self.STATUS_DOING = "进行中"
        self.STATUS_PAUSED = "挂起"
        self.STATUS_DONE = "已完成"
        self.TASK_TYPES = ["主线任务", "副线任务"]
        self.COMMENT_TYPES = ["备注", "问题", "心得"]
        self.COMMENT_ICON_MAP = {"心得": "💡", "问题": "❓", "备注": "📌"}
        self.COMMENT_COLOR_MAP = {"心得": "green", "问题": "red", "备注": "blue"}


config = Config()


# =========================================================================================
# 2. 数据模型 (Data Model)
# =========================================================================================

class Task:
    """
    表示单个任务的数据结构及其相关操作。
    """

    def __init__(self, task_name, task_type):
        self.task_name = task_name
        self.task_type = task_type
        self.creation_time = datetime.now(config.BEIJING_TZ)
        self.task_id = f"task_{self.creation_time.timestamp()}"
        self.status = config.STATUS_TODO
        self.completion_time = None
        self.task_duration = None
        self.task_comments = []
        self.total_active_time = timedelta(0)
        self.last_start_active_time = None
        self.active_time_segments = []

    def to_dict(self):
        """将任务对象序列化为字典，以便存储为JSON。"""
        return {
            "task_name": self.task_name,
            "task_type": self.task_type,
            "creation_time": self.creation_time.isoformat(),
            "task_id": self.task_id,
            "status": self.status,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "task_duration_seconds": self.task_duration.total_seconds() if self.task_duration else None,
            "task_comments": [
                {
                    "id": c.get("id"), "content": c.get("content"), "type": c.get("type"),
                    "time": c.get("time").isoformat(), "status": c.get("status")
                } for c in self.task_comments
            ],
            "total_active_time_seconds": self.total_active_time.total_seconds(),
            "last_start_active_time": self.last_start_active_time.isoformat() if self.last_start_active_time else None,
            "active_time_segments": [
                {
                    "id": s.get("id"),
                    "start_time": s["start_time"].isoformat(),
                    "end_time": s["end_time"].isoformat(),
                    "duration_seconds": s["duration"].total_seconds(),
                    "stopped_as": s["stopped_as"]
                } for s in self.active_time_segments
            ]
        }

    @classmethod
    def from_dict(cls, data):
        """从字典反序列化创建任务对象。"""
        task = cls(data.get("task_name", "无标题任务"), data.get("task_type", "未分类"))
        task.creation_time = datetime.fromisoformat(data["creation_time"])
        task.task_id = data.get("task_id", f"task_{task.creation_time.timestamp()}")
        task.status = data.get("status", config.STATUS_TODO)
        task.completion_time = datetime.fromisoformat(data["completion_time"]) if data.get("completion_time") else None
        if data.get("task_duration_seconds") is not None:
            task.task_duration = timedelta(seconds=data["task_duration_seconds"])
        task.total_active_time = timedelta(seconds=data.get("total_active_time_seconds", 0))
        if data.get("last_start_active_time"):
            task.last_start_active_time = datetime.fromisoformat(data["last_start_active_time"])
        task.task_comments = [
            {
                "id": c.get("id"), "content": c.get("content"), "type": c.get("type"),
                "time": datetime.fromisoformat(c.get("time")), "status": c.get("status")
            } for c in data.get("task_comments", [])
        ]
        task.active_time_segments = [
            {
                "id": s.get("id", f"segment_{datetime.fromisoformat(s['start_time']).timestamp()}"),
                "start_time": datetime.fromisoformat(s["start_time"]),
                "end_time": datetime.fromisoformat(s["end_time"]),
                "duration": timedelta(seconds=s["duration_seconds"]),
                "stopped_as": s["stopped_as"]
            } for s in data.get("active_time_segments", [])
        ]
        return task

    def set_status(self, new_status):
        """更新任务状态并处理计时逻辑。"""
        if self.status == new_status: return
        old_status, self.status, now = self.status, new_status, datetime.now(config.BEIJING_TZ)

        is_starting = new_status == config.STATUS_DOING
        is_stopping = old_status == config.STATUS_DOING and new_status != config.STATUS_DOING

        if is_starting:
            self.last_start_active_time = now
            st.toast("计时开始 ⏱️")
        elif is_stopping and self.last_start_active_time:
            duration = now - self.last_start_active_time
            self.total_active_time += duration
            self.active_time_segments.append({
                "id": f"segment_{now.timestamp()}",
                "start_time": self.last_start_active_time, "end_time": now, "duration": duration,
                "stopped_as": new_status
            })
            self.last_start_active_time = None
            st.toast("本段计时结束...")

        if new_status == config.STATUS_DONE:
            if old_status != config.STATUS_DONE:
                self.completion_time = now
                self.task_duration = self.completion_time - self.creation_time
                st.balloons()
        elif old_status == config.STATUS_DONE:
            self.completion_time, self.task_duration = None, None

    def _recalculate_total_active_time(self):
        """私有方法，根据所有工时段重新计算总有效工作时间。"""
        self.total_active_time = sum((s['duration'] for s in self.active_time_segments), timedelta())

    def edit_time_segment(self, segment_id, new_start_time, new_end_time):
        """
        编辑指定ID的工时段，并自动更新相关时长。
        """
        if new_start_time >= new_end_time:
            st.error("更新失败：结束时间必须晚于开始时间。")
            return False

        target_segment = next((s for s in self.active_time_segments if s.get('id') == segment_id), None)
        if target_segment:
            target_segment['start_time'] = new_start_time
            target_segment['end_time'] = new_end_time
            target_segment['duration'] = new_end_time - new_start_time
            self._recalculate_total_active_time()
            st.toast("工时记录已更新！", icon="✅")
            return True
        return False

    def add_comment(self, content, comment_type):
        """向任务添加一条评论。"""
        now = datetime.now(config.BEIJING_TZ)
        comment = {
            "id": f"comment_{now.timestamp()}", "content": content, "type": comment_type,
            "time": now, "status": "未解决" if comment_type == "问题" else None
        }
        self.task_comments.append(comment)
        st.toast(f"任务 '{self.task_name}' 添加了新评论！", icon="💬")

    def get_total_lifespan_duration(self):
        """计算任务从创建至今的总生命周期。"""
        return self.task_duration if self.completion_time else datetime.now(config.BEIJING_TZ) - self.creation_time

    def get_total_active_duration(self):
        """计算任务的总有效工作时长（包括当前正在进行的计时）。"""
        current_active = datetime.now(
            config.BEIJING_TZ) - self.last_start_active_time if self.status == config.STATUS_DOING and self.last_start_active_time else timedelta(
            0)
        return self.total_active_time + current_active

    def get_first_start_time(self):
        if not self.active_time_segments: return None
        earliest_segment = min(self.active_time_segments, key=lambda segment: segment['start_time'])
        return earliest_segment['start_time']

    def get_doing_efficiency(self):
        first_start = self.get_first_start_time()
        if self.status != config.STATUS_DONE or not first_start or not self.completion_time:
            return None
        total_active_duration = self.get_total_active_duration()
        total_work_span = self.completion_time - first_start
        if total_work_span.total_seconds() <= 0: return 1.0
        efficiency = total_active_duration.total_seconds() / total_work_span.total_seconds()
        return min(efficiency, 1.0)


# =========================================================================================
# 3. 数据管理模块 (Data Management)
# =========================================================================================

class DataManager:
    """
    负责数据的加载、保存和同步（本地与GitHub）。
    """

    def __init__(self, app_config: Config):
        self.config = app_config

    @st.cache_resource
    def _get_github_repo(_self, token=None, repo_name=None):
        g_token = token or _self.config.GITHUB_TOKEN
        g_repo = repo_name or _self.config.GITHUB_PRIVATE_REPO
        if not g_token or not g_repo: return None
        try:
            return Github(g_token).get_repo(g_repo)
        except GithubException as e:
            st.error(f"连接到 GitHub 仓库失败: {e}。请检查你的 secrets.toml 文件配置。")
            return None

    def _load_from_github(self, token=None, repo_name=None):
        repo = self._get_github_repo(token, repo_name)
        if repo is None: return None
        try:
            content_file = repo.get_contents(self.config.DATA_FILE_NAME)
            content = content_file.decoded_content.decode("utf-8")
            st.toast("✅ 已从 GitHub 成功加载任务！", icon="🎉")
            return [Task.from_dict(task_data) for task_data in json.loads(content)]
        except UnknownObjectException:
            st.info("在仓库中未找到任务文件。当你第一次推送时，将自动创建。")
            return []
        except Exception as e:
            st.error(f"从 GitHub 加载任务时发生未知错误: {e}")
            return []

    def _save_to_github(self, tasks, token=None, repo_name=None):
        repo = self._get_github_repo(token, repo_name)
        if repo is None:
            st.error("无法保存，因为未能连接到 GitHub 仓库。")
            return
        content = json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False)
        commit_message = f"Tasks updated at {datetime.now(config.BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            file = repo.get_contents(self.config.DATA_FILE_NAME)
            repo.update_file(file.path, commit_message, content, file.sha)
            st.toast("✅ 任务已成功同步到 GitHub！", icon="⬆️")
        except UnknownObjectException:
            repo.create_file(self.config.DATA_FILE_NAME, commit_message, content)
            st.toast("✅ 在 GitHub 上创建了新的任务文件并已同步！", icon="☁️")
        except Exception as e:
            st.error(f"同步到 GitHub 失败: {e}")

    def _load_from_local(self):
        path = self.config.LOCAL_DATA_FILE_PATH
        if not os.path.exists(path): return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content: return []
            st.toast("✅ 已从本地文件成功加载任务！", icon="🏠")
            return [Task.from_dict(td) for td in json.loads(content)]
        except Exception as e:
            st.error(f"从本地文件加载任务失败: {e}")
            return []

    def _save_to_local(self, tasks):
        path = self.config.LOCAL_DATA_FILE_PATH
        try:
            content = json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False)
            temp_dir = os.path.dirname(path)
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=temp_dir, delete=False) as tmp_file:
                tmp_file.write(content)
                temp_path = tmp_file.name
            os.replace(temp_path, path)
            st.toast("✅ 任务已成功保存到本地文件！", icon="💾")
        except Exception as e:
            st.error(f"保存到本地文件失败: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

    def initial_load(self):
        if self.config.RUN_MODE == "local":
            tasks = self._load_from_local()
            if not tasks and self.config.GITHUB_TOKEN:
                tasks = self._load_from_github()
            return tasks
        else:
            return []

    def sync_state(self):
        tasks = st.session_state.get('tasks', [])
        if self.config.RUN_MODE == "local":
            self._save_to_local(tasks)
            if self.config.GITHUB_TOKEN:
                self._save_to_github(tasks)
        else:
            if 'github_token' in st.session_state and 'github_repo' in st.session_state:
                self._save_to_github(tasks, st.session_state.github_token, st.session_state.github_repo)

    def import_from_file(self, uploaded_file):
        if uploaded_file is None: return
        try:
            tasks_data = json.load(uploaded_file)
            existing_ids = {task.task_id for task in st.session_state.tasks}
            new_tasks = [Task.from_dict(td) for td in tasks_data if td.get("task_id") not in existing_ids]
            if new_tasks:
                st.session_state.tasks.extend(new_tasks)
                st.success(f"成功导入 {len(new_tasks)} 个新任务！")
                self.sync_state()
                st.rerun()
            else:
                st.info("文件中没有发现新任务。")
        except json.JSONDecodeError:
            st.error("导入失败：文件格式不是有效的 JSON。")
        except Exception as e:
            st.error(f"导入时发生未知错误: {e}")

    def get_export_data(self):
        tasks = st.session_state.get('tasks', [])
        return json.dumps([task.to_dict() for task in tasks], indent=2, ensure_ascii=False) if tasks else "{}"

    def connect_and_load_from_github(self, g_token, g_repo):
        tasks = self._load_from_github(g_token, g_repo)
        if tasks is not None:
            st.session_state.github_token = g_token
            st.session_state.github_repo = g_repo
            st.session_state.tasks = tasks
            st.rerun()


# =========================================================================================
# 4. UI 渲染模块 (UI Rendering)
# =========================================================================================

class KanbanUI:
    """
    [重构] 负责渲染应用的所有UI组件。
    内部方法已按照“主入口 -> 标签页 -> 组件”的层次结构重新组织。
    """

    def __init__(self, app_config: Config, data_manager: DataManager):
        self.config = app_config
        self.data_manager = data_manager

    # -------------------------------------------------------------------------------------
    # 1. 主渲染入口 (Main Rendering Entrypoints)
    # -------------------------------------------------------------------------------------

    def render_page_setup(self):
        """初始化页面配置，如标题、图标和自动刷新。"""
        st.set_page_config(page_title=self.config.PAGE_TITLE, page_icon=self.config.PAGE_ICON, layout="wide")
        st.title(f"{self.config.PAGE_ICON} {self.config.PAGE_TITLE}")
        st.markdown("---")
        st_autorefresh(interval=self.config.AUTO_REFRESH_INTERVAL_MS, key="clock_refresher")
        create_common_sidebar()

    def render_main_layout(self):
        """渲染主应用布局，包括所有标签页及其内容。"""
        tasks = st.session_state.get('tasks', [])
        existing_task_types = sorted(list(set(t.task_type for t in tasks)))

        tab1, tab2, tab3, tab4 = st.tabs(["📌 任务看板", "📅 日历视图", "📊 统计分析", "💬 评论知识库"])

        with tab1:
            self._render_kanban_tab(existing_task_types)
        with tab2:
            self._render_timeline_tab(tasks)
        with tab3:
            self._render_statistics_tab(tasks)
        with tab4:
            self._render_comments_tab()

    # -------------------------------------------------------------------------------------
    # 2. 标签页渲染模块 (Tab-Specific Rendering Modules)
    # -------------------------------------------------------------------------------------

    def _render_kanban_tab(self, existing_task_types):
        """渲染“任务看板”标签页的全部内容。"""
        self._render_main_controls(existing_task_types)
        st.markdown("---")
        self._render_kanban_layout(existing_task_types)

    def _render_timeline_tab(self, tasks):
        """渲染“日历视图”标签页的全部内容。"""
        st.header("任务时间线视图 📅", divider="rainbow")
        today = datetime.now(config.BEIJING_TZ).date()
        # --- [修改1] 默认展示过去一周 ---
        one_week_ago = today - timedelta(days=6)
        selected_range = st.date_input(
            "请选择要查看的日期范围",
            value=(one_week_ago, today),
            help="选择一个开始和结束日期来查看该时间段内的任务活动。"
        )

        start_date, end_date = (selected_range[0], selected_range[1]) if isinstance(selected_range,
                                                                                    (tuple, list)) and len(
            selected_range) == 2 else (today, today)

        if start_date > end_date:
            st.warning("开始日期不能晚于结束日期。")
            return

        st.markdown("---")

        timeline_data = []
        for task in tasks:
            for segment in task.active_time_segments:
                duration_str = self.format_timedelta_to_str(segment['duration'])
                timeline_data.append({
                    "Task": task.task_name, "Start": segment['start_time'], "Finish": segment['end_time'],
                    "Duration_Str": duration_str
                })
            if task.status == self.config.STATUS_DOING and task.last_start_active_time:
                duration = datetime.now(config.BEIJING_TZ) - task.last_start_active_time
                timeline_data.append({
                    "Task": task.task_name, "Start": task.last_start_active_time,
                    "Finish": datetime.now(config.BEIJING_TZ),
                    "Duration_Str": self.format_timedelta_to_str(duration)
                })

        if not timeline_data:
            st.info("没有任务活动记录，请先开始并完成一些任务以生成时间线。")
            return

        df = pd.DataFrame(timeline_data)
        range_start_dt = datetime.combine(start_date, time.min, tzinfo=config.BEIJING_TZ)
        range_end_dt = datetime.combine(end_date, time.max, tzinfo=config.BEIJING_TZ)

        filtered_df = df[(df['Start'] < range_end_dt) & (df['Finish'] > range_start_dt)].copy()
        if filtered_df.empty:
            st.info(f"在 **{start_date}** 到 **{end_date}** 期间没有找到任何任务活动记录。")
            return

        filtered_df['Clipped_Start'] = filtered_df['Start'].clip(lower=range_start_dt)
        filtered_df['Clipped_Finish'] = filtered_df['Finish'].clip(upper=range_end_dt)

        title = f"任务活动甘特图 ({start_date.strftime('%Y-%m-%d')})"
        if start_date != end_date:
            title += f" 至 {end_date.strftime('%Y-%m-%d')}"

        fig = px.timeline(
            filtered_df, x_start="Clipped_Start", x_end="Clipped_Finish", y="Task", color="Task",
            hover_data={"Duration_Str": True}, title=title
        )
        fig.update_yaxes(categoryorder='total ascending')
        fig.update_layout(xaxis_range=[range_start_dt, range_end_dt], xaxis_tickformat="%m-%d\n%H:%M")

        # --- [修改2] 添加天分隔线和午间分隔线 ---
        shapes = []
        current_day = start_date
        while current_day <= end_date:
            # 每日中午12点的灰色虚线
            noon_dt = datetime.combine(current_day, time(12, 0), tzinfo=config.BEIJING_TZ)
            shapes.append(
                {'type': 'line', 'x0': noon_dt, 'x1': noon_dt, 'y0': -0.5, 'y1': len(filtered_df['Task'].unique()),
                 'line': {'color': 'grey', 'width': 1, 'dash': 'dash'}})
            # 第二天0点的绿色实线 (从第一天开始画)
            if current_day > start_date:
                midnight_dt = datetime.combine(current_day, time.min, tzinfo=config.BEIJING_TZ)
                shapes.append({'type': 'line', 'x0': midnight_dt, 'x1': midnight_dt, 'y0': -0.5,
                               'y1': len(filtered_df['Task'].unique()), 'line': {'color': 'green', 'width': 2}})
            current_day += timedelta(days=1)
        fig.update_layout(shapes=shapes)
        # --------------------------------------------

        st.plotly_chart(fig, use_container_width=True)

    def _render_statistics_tab(self, all_tasks):
        """渲染“统计分析”标签页的全部内容。"""
        st.header("任务统计分析", divider="rainbow")
        if not all_tasks:
            st.info("看板上还没有任务，快去创建一个吧！")
            return

        # --- [修改3] 添加日期范围选择器 ---
        today = datetime.now(config.BEIJING_TZ).date()
        one_week_ago = today - timedelta(days=6)
        selected_range = st.date_input(
            "请选择要统计的时间范围",
            value=(one_week_ago, today),
            key="stats_date_range",
            help="所有统计数据将基于此时间范围内的任务活动进行计算。"
        )
        st.markdown("---")

        start_date, end_date = (selected_range[0], selected_range[1]) if isinstance(selected_range,
                                                                                    (tuple, list)) and len(
            selected_range) == 2 else (today, today)
        if start_date > end_date:
            st.warning("开始日期不能晚于结束日期。")
            return

        range_start_dt = datetime.combine(start_date, time.min, tzinfo=config.BEIJING_TZ)
        range_end_dt = datetime.combine(end_date, time.max, tzinfo=config.BEIJING_TZ)

        # --- [修改4] 根据日期范围过滤任务 ---
        filtered_tasks = []
        for task in all_tasks:
            is_relevant = False
            # 条件1: 创建时间在范围内
            if range_start_dt <= task.creation_time <= range_end_dt:
                is_relevant = True
            # 条件2: 完成时间在范围内
            if not is_relevant and task.completion_time and (range_start_dt <= task.completion_time <= range_end_dt):
                is_relevant = True
            # 条件3: 有活动时间段与范围重叠
            if not is_relevant:
                for segment in task.active_time_segments:
                    if segment['start_time'] < range_end_dt and segment['end_time'] > range_start_dt:
                        is_relevant = True
                        break
            if is_relevant:
                filtered_tasks.append(task)
        # ------------------------------------

        if not filtered_tasks:
            st.info(f"在 **{start_date}** 到 **{end_date}** 期间没有找到任何任务活动。")
            return

        st.success(
            f"正在显示 **{start_date.strftime('%Y-%m-%d')}** 到 **{end_date.strftime('%Y-%m-%d')}** 期间的 **{len(filtered_tasks)}** 个相关任务的统计数据。")

        main_df = pd.DataFrame([
            {
                "task_name": t.task_name, "creation_time": t.creation_time, "completion_time": t.completion_time,
                "status": t.status, "task_type": t.task_type,
                "total_active_time_seconds": t.get_total_active_duration().total_seconds(),
                "task_duration_seconds": t.task_duration.total_seconds() if t.task_duration else None,
                "efficiency": t.get_doing_efficiency()
            } for t in filtered_tasks
        ])

        # --- [修改5] 将过滤后的任务传递给子模块 ---
        self._render_daily_utilization_section(filtered_tasks)
        self._render_task_efficiency_section(main_df)
        self._render_tasks_overview_section(main_df)
        # -----------------------------------------

    def _render_comments_tab(self):
        """渲染“评论知识库”标签页的全部内容。"""
        st.header("💬 问题跟踪与知识库", divider="rainbow")
        tasks_with_comments = [task for task in st.session_state.get('tasks', []) if task.task_comments]
        if not tasks_with_comments:
            st.info("目前还没有任何任务有评论记录。")
            return

        all_comments = [cmt for task in tasks_with_comments for cmt in task.task_comments]

        st.subheader("关键指标", anchor=False)
        total_problems = len([c for c in all_comments if c['type'] == '问题'])
        unsolved_problems = len([c for c in all_comments if c.get('status') == '未解决'])
        total_insights = len([c for c in all_comments if c['type'] == '心得'])
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("待解决问题", f"{unsolved_problems} 个")
        kpi_cols[1].metric("问题总数", f"{total_problems} 个")
        kpi_cols[2].metric("心得总数", f"{total_insights} 条")

        st.markdown("---")
        st.subheader("筛选与搜索", anchor=False)
        all_comment_types = sorted(list(set(c['type'] for c in all_comments)))
        task_names = sorted(list(set(t.task_name for t in tasks_with_comments)))
        filter_cols = st.columns([2, 2, 1, 1])
        search_query = filter_cols[0].text_input("全文搜索评论内容", placeholder="输入关键词...")
        selected_tasks = filter_cols[1].multiselect("按任务筛选", options=task_names)
        selected_types = filter_cols[2].multiselect("按类型筛选", options=all_comment_types)
        selected_status = filter_cols[3].selectbox("按问题状态筛选", options=["全部", "未解决", "已解决"], index=1)
        st.markdown("---")

        filtered_tasks = []
        for task in tasks_with_comments:
            comments_to_display = list(task.task_comments)
            if selected_tasks and task.task_name not in selected_tasks: continue
            if search_query: comments_to_display = [c for c in comments_to_display if
                                                    search_query.lower() in c['content'].lower()]
            if selected_types: comments_to_display = [c for c in comments_to_display if c['type'] in selected_types]
            if selected_status != "全部": comments_to_display = [c for c in comments_to_display if
                                                               c['type'] == '问题' and c.get('status') == selected_status]
            if comments_to_display: filtered_tasks.append({'task': task, 'comments': comments_to_display})

        if not filtered_tasks:
            st.warning("根据您的筛选条件，没有找到匹配的评论。")
            return

        st.subheader(f"找到 {len(filtered_tasks)} 个相关任务", anchor=False)
        for item in filtered_tasks:
            task, comments = item['task'], sorted(item['comments'], key=lambda c: c['time'])
            with st.expander(f"**{task.task_name}** (`{task.task_type}`) - 包含 {len(comments)} 条相关评论"):
                for c in comments:
                    icon = self.config.COMMENT_ICON_MAP.get(c['type'], "💬")
                    with st.container(border=True):
                        st.markdown(f"##### {icon} {c['type']}")
                        if c['type'] == '问题':
                            status = c.get('status', '未解决')
                            color = "red" if status == "未解决" else "green"
                            st.markdown(f"状态: :{color}[**{status}**]")
                        st.markdown(c['content'])
                        st.caption(f"记录于: {c['time'].strftime('%Y-%m-%d %H:%M')}")

    # -------------------------------------------------------------------------------------
    # 3. 组件渲染模块 (Component Rendering Modules)
    # -------------------------------------------------------------------------------------

    def _render_main_controls(self, existing_types):
        """渲染页面顶部的控制面板（创建任务、导入/导出等）。"""
        st.header("控制面板", divider="rainbow")
        if self.config.RUN_MODE == "local":
            st.info("🚀 **本地开发模式**: 数据实时保存到本地文件。")
        else:
            self._render_github_connection_panel()

        col1, col2 = st.columns(2)
        with col1, st.container(border=True, height=360):
            st.subheader("🚀 创建新任务", anchor=False)
            all_types = sorted(list(set(self.config.TASK_TYPES + existing_types)))
            options = all_types + ["➕ 添加新类型..."]
            selected_option = st.selectbox(label="任务标签", options=options)
            new_type_name = st.text_input("请输入新的类型名称:", key="new_type_name") if selected_option == "➕ 添加新类型..." else ""
            with st.form(key="new_task_form"):
                name = st.text_input("任务名称", placeholder="例如：完成项目报告")
                if st.form_submit_button("添加任务", use_container_width=True):
                    if name:
                        task_type = new_type_name if new_type_name else (
                            selected_option if selected_option != "➕ 添加新类型..." else None)
                        if task_type:
                            st.session_state.tasks.append(Task(task_name=name, task_type=task_type))
                            st.success(f"任务 '{name}' 已添加！")
                            self.data_manager.sync_state()
                            st.rerun()
                        else:
                            st.warning("您选择了添加新类型，但未输入类型名称。")
                    else:
                        st.warning("任务名称不能为空！")

        with col2, st.container(border=True, height=360):
            st.subheader("📥 本地导入/导出", anchor=False)
            uploaded = st.file_uploader("选择一个 .json 任务文件", type=["json"], help="从本地文件恢复任务。")
            if uploaded:
                self.data_manager.import_from_file(uploaded)

            fname = f"tasks_export_{datetime.now(config.BEIJING_TZ).strftime('%Y%m%d_%H%M%S')}.json"
            st.download_button(
                "📥 下载任务到本地", self.data_manager.get_export_data(), fname, "application/json",
                help="将当前看板上的所有任务保存为一个 JSON 文件。", use_container_width=True,
                disabled=not st.session_state.get('tasks', [])
            )
            if self.config.RUN_MODE == "cloud":
                st.button("⬆️ 手动同步到 GitHub", on_click=self.data_manager.sync_state, use_container_width=True,
                          disabled='github_token' not in st.session_state)

    def _render_github_connection_panel(self):
        """渲染用于连接到GitHub仓库的UI组件。"""
        with st.container(border=True):
            st.subheader("🔗 连接到 GitHub", anchor=False)
            if 'github_token' not in st.session_state or 'github_repo' not in st.session_state:
                st.info("☁️ **云端模式**: 请连接到你的 GitHub 仓库以加载或保存任务。")
                g_token = st.text_input("GitHub 个人访问令牌", type="password")
                g_repo = st.text_input("GitHub 仓库地址", placeholder="your-username/your-repo")
                if st.button("连接并加载数据", use_container_width=True):
                    if g_token and g_repo:
                        self.data_manager.connect_and_load_from_github(g_token, g_repo)
                    else:
                        st.warning("请输入完整的 GitHub 令牌和仓库地址。")
            else:
                st.success(f"✅ 已连接到仓库: **{st.session_state.github_repo}**")

                def disconnect():
                    st.session_state.pop('github_token', None)
                    st.session_state.pop('github_repo', None)
                    st.session_state.tasks = []
                    st.toast("已断开连接", icon="🔗")

                st.button("🔌 断开连接", on_click=disconnect, use_container_width=True, type="secondary")

    def _render_kanban_layout(self, existing_types):
        """渲染看板的主体布局，包含四个状态列和其中的任务卡片。"""
        tasks = st.session_state.get('tasks', [])
        sorted_tasks = sorted(tasks, key=lambda x: x.creation_time, reverse=True)

        status_map = {
            self.config.STATUS_TODO: (f"📥 {self.config.STATUS_TODO}", []),
            self.config.STATUS_DOING: (f"💻 {self.config.STATUS_DOING}", []),
            self.config.STATUS_PAUSED: (f"⏸️ {self.config.STATUS_PAUSED}", []),
            self.config.STATUS_DONE: (f"✅ {self.config.STATUS_DONE}", [])
        }
        for t in sorted_tasks:
            if t.status in status_map:
                status_map[t.status][1].append(t)

        cols = st.columns(len(status_map))
        for col, (header, task_list) in zip(cols, status_map.values()):
            with col:
                st.header(f"{header} ({len(task_list)})", divider="rainbow")
                for task in task_list:
                    self._render_task_card(task, existing_types)

    def _render_task_card(self, task, existing_types):
        """渲染单个任务卡片的全部内容。"""
        with st.expander(f"`{task.task_type}` {task.task_name}", expanded=False):
            st.subheader(task.task_name, divider="rainbow")
            self._render_task_metrics(task)
            self._render_task_controls(task)
            self._render_task_time_logs(task)
            self._render_task_comments_section(task)
            self._render_task_management_popover(task, existing_types)

    def _render_task_metrics(self, task):
        """渲染任务卡片中的核心指标：总耗时和生命周期。"""
        col1, col2 = st.columns(2)
        col1.metric("⏱️ 任务总耗时 (有效工作)", self.format_timedelta_to_str(task.get_total_active_duration()),
                    help="这是任务在“进行中”状态下所花费的实际时间总和。")
        col2.metric("🗓️ 任务生命周期 (自创建)", self.format_timedelta_to_str(task.get_total_lifespan_duration()),
                    help="这是从任务创建开始的总时长。")

    def _render_task_controls(self, task):
        """根据任务当前状态渲染操作按钮（开始、挂起、完成等）。"""

        def handle_status_change(t, new_status):
            t.set_status(new_status)
            self.data_manager.sync_state()

        cols = st.columns(4)
        if task.status in [self.config.STATUS_TODO, self.config.STATUS_PAUSED]:
            cols[0].button("▶️ 开始", key=f"start_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.config.STATUS_DOING), use_container_width=True)
        if task.status == self.config.STATUS_DOING:
            cols[1].button("⏸️ 挂起", key=f"pause_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.config.STATUS_PAUSED), help="将任务移至“挂起”并暂停计时。", use_container_width=True)
            cols[2].button("✅ 完成", key=f"done_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.config.STATUS_DONE), use_container_width=True)
        if task.status == self.config.STATUS_DONE:
            cols[3].button("🔄 重新打开", key=f"reopen_{task.task_id}", on_click=handle_status_change,
                           args=(task, self.config.STATUS_DOING), use_container_width=True)
        st.write("")

    def _render_task_time_logs(self, task):
        """渲染任务的工时记录列表，并提供编辑功能。"""
        st.subheader("工时记录", divider='rainbow')
        if task.status == self.config.STATUS_DOING and task.last_start_active_time:
            duration_str = self.format_timedelta_to_str(datetime.now(config.BEIJING_TZ) - task.last_start_active_time)
            st.success(
                f"**当前:** 正在计时... ({duration_str})\n开始于: {task.last_start_active_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not task.active_time_segments and task.status != self.config.STATUS_DOING:
            st.caption("暂无完整的工时记录。")
            return

        sorted_segments = sorted(task.active_time_segments, key=lambda s: s['start_time'], reverse=True)
        for date_val, group in groupby(sorted_segments, key=lambda s: s['start_time'].date()):
            group_list = list(group)
            total_duration_str = self.format_timedelta_to_str(sum((s['duration'] for s in group_list), timedelta()))
            with st.expander(f"**{date_val.strftime('%Y-%m-%d')}** - 总计: **{total_duration_str}**"):
                for i, s in enumerate(group_list):
                    icon_map = {self.config.STATUS_DONE: "✅", self.config.STATUS_PAUSED: "⏸️"}
                    icon = icon_map.get(s['stopped_as'], "⏹️")
                    cols = st.columns([4, 1])
                    cols[0].info(
                        f"**{self.format_timedelta_to_str(s['duration'])}** (从 {s['start_time'].strftime('%H:%M:%S')} 到 {s['end_time'].strftime('%H:%M:%S')}) {icon}")

                    with cols[1], st.popover("✏️ 编辑", use_container_width=True):
                        form_key = f"edit_segment_{task.task_id}_{s.get('id')}_{i}"
                        with st.form(key=form_key):
                            st.markdown("##### 编辑工时段")
                            c1, c2 = st.columns(2)
                            new_start_date = c1.date_input("开始日期", value=s['start_time'].date(), key=f"{form_key}_sd")
                            new_start_time = c2.time_input("开始时间", value=s['start_time'].time(), key=f"{form_key}_st")
                            c3, c4 = st.columns(2)
                            new_end_date = c3.date_input("结束日期", value=s['end_time'].date(), key=f"{form_key}_ed")
                            new_end_time = c4.time_input("结束时间", value=s['end_time'].time(), key=f"{form_key}_et")

                            if st.form_submit_button("保存更改", use_container_width=True):
                                new_start = datetime.combine(new_start_date, new_start_time).replace(
                                    tzinfo=config.BEIJING_TZ)
                                new_end = datetime.combine(new_end_date, new_end_time).replace(tzinfo=config.BEIJING_TZ)
                                if task.edit_time_segment(s.get('id'), new_start, new_end):
                                    self.data_manager.sync_state()
                                    st.rerun()

    def _render_task_comments_section(self, task):
        header_cols = st.columns([2, 1])
        with header_cols[0]:
            st.subheader(self.config.T_CARD_COMMENTS_HEADER, divider='rainbow')
        with header_cols[1]:
            with st.popover(f"{self.config.T_POPOVER_CREATE_COMMENT}", use_container_width=True):
                with st.form(key=f"comment_form_{task.task_id}", clear_on_submit=True):
                    ctype = st.selectbox(self.config.T_COMMENT_TYPE_LABEL, self.config.COMMENT_TYPES)
                    content = st.text_area(self.config.T_COMMENT_CONTENT_LABEL, height=100)
                    if st.form_submit_button(self.config.T_COMMENT_SUBMIT_BUTTON):
                        if content:
                            task.add_comment(content, ctype)
                            self.data_manager.sync_state()
                            st.rerun()
                        else:
                            st.warning(self.config.T_WARN_EMPTY_COMMENT)
        problems = [c for c in task.task_comments if c['type'] == '问题']
        other_comments = [c for c in task.task_comments if c['type'] != '问题']

        def on_status_change(t, c_id, key):
            comment = next((c for c in t.task_comments if c.get('id') == c_id), None)
            if comment:
                comment['status'] = st.session_state[key]
                self.data_manager.sync_state()

        if problems:
            unsolved_count = len([p for p in problems if p.get('status', '未解决') == '未解决'])
            st.markdown(f"**待解决问题 ({unsolved_count})**")
            for p in sorted(problems, key=lambda c: c['time']):
                with st.container(border=True):
                    comment_id = p.get('id', str(p['time'].timestamp()))
                    st.markdown(p['content'])
                    footer_cols = st.columns([3, 2])
                    with footer_cols[0]:
                        st.caption(f"记录于: {p['time'].strftime('%Y-%m-%d %H:%M')}")
                    with footer_cols[1]:
                        options = ["未解决", "已解决"]
                        current_status = p.get('status', '未解决')
                        try:
                            current_index = options.index(current_status)
                        except ValueError:
                            current_index = 0
                        st.selectbox("状态", options=options, index=current_index,
                                     key=f"status_select_{comment_id}_card", on_change=on_status_change,
                                     args=(task, comment_id, f"status_select_{comment_id}_card"),
                                     label_visibility="collapsed")
            st.markdown("---")
        if other_comments:
            st.markdown("**其他评论记录 (备注/心得)**")
            container_height = 150 if problems else 250
            with st.container(height=container_height):
                for c in reversed(other_comments):
                    icon = self.config.COMMENT_ICON_MAP.get(c['type'], "💬")
                    color = self.config.COMMENT_COLOR_MAP.get(c['type'], "gray")
                    with st.chat_message(name=c['type'], avatar=icon):
                        st.markdown(f":{color}[{c['content']}]")
                        st.caption(f"_{c['time'].strftime('%Y-%m-%d %H:%M')}_")

    def _render_task_management_popover(self, task, existing_types):
        st.divider()
        col_info, col_manage = st.columns([3, 1])
        with col_info:
            st.caption(f"ID: {task.task_id}")
            st.caption(f"创建于: {task.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")
        with col_manage, st.popover("⚙️ 管理"):
            with st.form(key=f"edit_form_{task.task_id}"):
                st.subheader("编辑任务", anchor=False)
                edited_name = st.text_input("任务名称", value=task.task_name)
                all_types = sorted(list(set(self.config.TASK_TYPES + existing_types + [task.task_type])))
                index = all_types.index(task.task_type)
                edited_type = st.selectbox("任务标签", options=all_types, index=index)
                if st.form_submit_button("💾 保存更改", use_container_width=True):
                    task.task_name, task.task_type = edited_name, edited_type
                    st.toast(f"任务 '{task.task_name}' 已更新!", icon="✅")
                    self.data_manager.sync_state()
                    st.rerun()
            st.divider()
            if st.button("🗑️ 删除任务", key=f"delete_{task.task_id}", type="primary", use_container_width=True,
                         help="此操作不可撤销！"):
                st.session_state.tasks = [t for t in st.session_state.tasks if t.task_id != task.task_id]
                st.toast(f"任务 '{task.task_name}' 已删除。", icon="🗑️")
                self.data_manager.sync_state()
                st.rerun()

    def _calculate_daily_utilization(self, tasks, window_start_hour, window_end_hour, crosses_midnight=False):
        daily_stats = {}
        for task in tasks:
            for segment in task.active_time_segments:
                day = segment['start_time'].date()
                window_start_dt = datetime.combine(day, time.min, tzinfo=config.BEIJING_TZ).replace(
                    hour=window_start_hour)
                if crosses_midnight:
                    window_end_dt = datetime.combine(day + timedelta(days=1), time.min,
                                                     tzinfo=config.BEIJING_TZ).replace(hour=window_end_hour)
                else:
                    window_end_dt = datetime.combine(day, time.min, tzinfo=config.BEIJING_TZ).replace(
                        hour=window_end_hour)

                overlap_start = max(segment['start_time'], window_start_dt)
                overlap_end = min(segment['end_time'], window_end_dt)

                if overlap_end > overlap_start:
                    if day not in daily_stats:
                        daily_stats[day] = {"window_seconds": 0}
                    daily_stats[day]["window_seconds"] += (overlap_end - overlap_start).total_seconds()

        if not daily_stats: return pd.DataFrame()

        df = pd.DataFrame.from_dict(daily_stats, orient='index')
        df.index = pd.to_datetime(df.index)
        available_hours = (
                                  24 - window_start_hour) + window_end_hour if crosses_midnight else window_end_hour - window_start_hour
        available_seconds = available_hours * 3600
        df['window_utilization_pct'] = (df['window_seconds'] / available_seconds * 100) if available_seconds > 0 else 0
        return df.sort_index(ascending=False)

    def _display_utilization_kpis(self, df, prefix=""):
        today = datetime.now(config.BEIJING_TZ).date()
        today_series = df[df.index.date == today]
        today_util = today_series['window_utilization_pct'].iloc[0] if not today_series.empty else 0

        historical_df = df[df.index.date < today]
        last_day_util = historical_df['window_utilization_pct'].iloc[0] if not historical_df.empty else 0
        delta = today_util - last_day_util if last_day_util > 0 else None

        df_for_avg = historical_df.head(5)
        num_days_for_avg = len(df_for_avg)
        last_n_days_avg = df_for_avg['window_utilization_pct'].mean() if not df_for_avg.empty else 0
        avg_label = f"近{num_days_for_avg}日{prefix}平均" if num_days_for_avg > 0 else f"历史{prefix}平均"

        kpi_cols = st.columns(3)
        kpi_cols[0].metric(label=f"今日{prefix}利用率", value=f"{today_util:.1f}%",
                           delta=f"{delta:.1f}%" if delta is not None else "—", help="与上一个有记录的工作日相比的变化。")
        kpi_cols[1].metric(label=f"上一活动日{prefix}利用率", value=f"{last_day_util:.1f}%")
        kpi_cols[2].metric(label=avg_label, value=f"{last_n_days_avg:.1f}%")

    def _render_daily_utilization_section(self, tasks):
        with st.container(border=True):
            st.subheader("📊 每日时间利用率分析", anchor=False)
            st.caption("通过自定义工作与非工作时间，分析你在不同时间段的专注度和产出效率。")
            time_options = [f"{h:02d}:00" for h in range(24)] + [f"{h:02d}:00 (次日)" for h in range(6)]
            col1, col2 = st.columns(2, gap="large")
            with col1:
                st.markdown("##### 🏢 工作时间")
                with st.expander("⚙️ 设置工作时间 (支持跨天)", expanded=False):
                    work_start_str, work_end_str = st.select_slider("选择工作时间范围", options=time_options,
                                                                    value=("09:00", "17:00"), key="work_time_range")
                work_start, work_end = int(work_start_str.split(':')[0]), int(work_end_str.split(':')[0])
                work_crosses_midnight = "(次日)" in work_end_str
                if not work_crosses_midnight and work_start >= work_end:
                    st.warning("工作开始时间必须早于结束时间。")
                else:
                    work_df = self._calculate_daily_utilization(tasks, work_start, work_end,
                                                                crosses_midnight=work_crosses_midnight)
                    self._display_utilization_kpis(work_df, prefix="工作")
                    if not work_df.empty:
                        fig = px.line(work_df.head(30), x=work_df.head(30).index, y='window_utilization_pct',
                                      title=f"工作时间利用率 ({work_start_str} - {work_end_str})",
                                      labels={'x': '日期', 'window_utilization_pct': '利用率 (%)'}, markers=True)
                        fig.update_layout(yaxis=dict(range=[0, 105]));
                        fig.update_xaxes(tickformat="%m月%d日", dtick="D1")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("在定义的工作时间内暂无工时记录。")
            with col2:
                st.markdown("##### 🏡 非工作时间")
                with st.expander("⚙️ 设置非工作/学习时间 (支持跨天)", expanded=False):
                    free_start_str, free_end_str = st.select_slider("选择时间范围", options=time_options,
                                                                    value=("18:00", "23:00"), key="free_time_range")
                free_start, free_end = int(free_start_str.split(':')[0]), int(free_end_str.split(':')[0])
                free_crosses_midnight = "(次日)" in free_end_str
                if not free_crosses_midnight and free_start >= free_end:
                    st.warning("非工作开始时间必须早于结束时间。")
                else:
                    free_df = self._calculate_daily_utilization(tasks, free_start, free_end,
                                                                crosses_midnight=free_crosses_midnight)
                    self._display_utilization_kpis(free_df, prefix="非工作")
                    if not free_df.empty:
                        fig = px.line(free_df.head(30), x=free_df.head(30).index, y='window_utilization_pct',
                                      title=f"非工作时间利用率 ({free_start_str} - {free_end_str})",
                                      labels={'x': '日期', 'window_utilization_pct': '利用率 (%)'}, markers=True,
                                      color_discrete_sequence=['#EF553B'])
                        fig.update_layout(yaxis=dict(range=[0, 105]));
                        fig.update_xaxes(tickformat="%m月%d日", dtick="D1")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("在定义的非工作时间内暂无工时记录。")

    def _render_task_efficiency_section(self, df):
        with st.container(border=True):
            st.subheader("🎯 单任务执行效率分析 (仅限已完成)", anchor=False)
            st.caption("效率越高，表示任务完成过程中的拖延时间越少。100% 表示任务从开始到结束一直在进行中。")
            efficiency_df = df.dropna(subset=['efficiency']).copy()
            if not efficiency_df.empty:
                efficiency_df['efficiency_pct'] = efficiency_df['efficiency'] * 100
                avg_eff = efficiency_df['efficiency_pct'].mean()
                max_eff_row, min_eff_row = efficiency_df.loc[efficiency_df['efficiency_pct'].idxmax()], \
                                           efficiency_df.loc[efficiency_df['efficiency_pct'].idxmin()]
                kpi_cols = st.columns(3)
                kpi_cols[0].metric("平均执行效率", f"{avg_eff:.1f}%")
                kpi_cols[1].metric("最高效率任务", f"{max_eff_row['efficiency_pct']:.1f}%",
                                   help=f"任务: {max_eff_row['task_name']}")
                kpi_cols[2].metric("最低效率任务", f"{min_eff_row['efficiency_pct']:.1f}%",
                                   help=f"任务: {min_eff_row['task_name']}")
                st.markdown("---")
                fig_efficiency = px.bar(efficiency_df.sort_values('efficiency', ascending=True), x='efficiency_pct',
                                        y='task_name', orientation='h', title='各任务执行效率对比',
                                        labels={'task_name': '任务名称', 'efficiency_pct': '效率 (%)'},
                                        text=efficiency_df['efficiency_pct'].apply(lambda x: f'{x:.1f}%'),
                                        color='task_name')
                fig_efficiency.update_layout(showlegend=False);
                fig_efficiency.update_layout(xaxis=dict(range=[0, 105]))
                st.plotly_chart(fig_efficiency, use_container_width=True)
            else:
                st.info("暂无已完成且有计时记录的任务可供分析效率。")

    def _render_tasks_overview_section(self, df):
        with st.container(border=True):
            st.subheader("🗂️ 任务总览", anchor=False)
            total_tasks = len(df)
            completed_tasks = df[df['status'] == self.config.STATUS_DONE].shape[0]
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            avg_active_time_sec = df[df['status'] == self.config.STATUS_DONE]['total_active_time_seconds'].mean()
            avg_lifespan_sec = df[df['status'] == self.config.STATUS_DONE]['task_duration_seconds'].mean()
            kpi_cols = st.columns(4)
            kpi_cols[0].metric("总任务数", f"{total_tasks} 个");
            kpi_cols[1].metric("完成率", f"{completion_rate:.1f}%")
            kpi_cols[2].metric("平均活跃时长",
                               self.format_timedelta_to_str(timedelta(seconds=avg_active_time_sec)) if pd.notna(
                                   avg_active_time_sec) else "N/A", help="仅计算已完成任务")
            kpi_cols[3].metric("平均生命周期", self.format_timedelta_to_str(timedelta(seconds=avg_lifespan_sec)) if pd.notna(
                avg_lifespan_sec) else "N/A", help="仅计算已完成任务")
            st.markdown("---")
            dist_col1, dist_col2 = st.columns(2)
            with dist_col1:
                status_counts = df['status'].value_counts();
                fig = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title="按状态分布",
                             hole=0.3)
                st.plotly_chart(fig, use_container_width=True)
            with dist_col2:
                type_counts = df['task_type'].value_counts();
                fig = px.pie(type_counts, values=type_counts.values, names=type_counts.index, title="按类型分布", hole=0.3)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")
            trend_col1, trend_col2 = st.columns(2)
            with trend_col1:
                st.markdown("##### 任务创建趋势");
                df_creation = df.copy()
                if df_creation['creation_time'].dt.tz is None: df_creation['creation_time'] = df_creation[
                    'creation_time'].dt.tz_localize('UTC').dt.tz_convert(config.BEIJING_TZ)
                df_creation['creation_date'] = df_creation['creation_time'].dt.date
                tasks_per_day = df_creation.groupby('creation_date').size().reset_index(name='count')
                fig_trend = px.bar(tasks_per_day, x='creation_date', y='count',
                                   labels={'creation_date': '日期', 'count': '任务数量'}, color='creation_date',
                                   color_continuous_scale=px.colors.sequential.Viridis)
                fig_trend.update_layout(coloraxis_showscale=False);
                fig_trend.update_xaxes(tickformat="%m月%d日", dtick="D1")
                st.plotly_chart(fig_trend, use_container_width=True)
            with trend_col2:
                st.markdown("##### 任务耗时分析 (仅限已完成)");
                df_timing = df.copy()
                df_timing['total_active_time_hours'] = df_timing['total_active_time_seconds'] / 3600;
                df_timing['task_duration_hours'] = df_timing['task_duration_seconds'] / 3600
                completed_df = df_timing[df_timing['status'] == self.config.STATUS_DONE].copy()
                if not completed_df.empty:
                    avg_time_by_type = completed_df.groupby('task_type')[
                        ['total_active_time_hours', 'task_duration_hours']].mean().reset_index().rename(
                        columns={'total_active_time_hours': '平均活跃时长 (小时)', 'task_duration_hours': '平均生命周期 (小时)'})
                    fig_avg_time = px.bar(avg_time_by_type, x='task_type', y=['平均活跃时长 (小时)', '平均生命周期 (小时)'],
                                          barmode='group',
                                          color_discrete_map={'平均活跃时长 (小时)': '#636EFA', '平均生命周期 (小时)': '#FFA15A'},
                                          labels={'task_type': '任务类型', 'value': '平均小时数', 'variable': '指标'})
                    st.plotly_chart(fig_avg_time, use_container_width=True)
                else:
                    st.info("暂无已完成的任务可供分析。")

    @staticmethod
    def format_timedelta_to_str(duration):
        """将timedelta对象格式化为易读的字符串。"""
        if not isinstance(duration, timedelta) or duration.total_seconds() <= 0: return "0秒"
        total_seconds = int(duration.total_seconds())
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        parts = []
        if days > 0: parts.append(f"{days}天")
        if hours > 0: parts.append(f"{hours}小时")
        if minutes > 0: parts.append(f"{minutes}分钟")
        return "".join(parts) if parts else f"{total_seconds}秒"


# =========================================================================================
# 5. 主程序 (Main App)
# =========================================================================================

def initialize_app(data_manager):
    """
    初始化会话状态，如果 'tasks' 不存在，则从数据源加载。
    """
    if 'tasks' not in st.session_state:
        st.session_state.tasks = data_manager.initial_load()


def main():
    """
    应用的主入口点。
    """
    data_manager = DataManager(config)
    ui = KanbanUI(config, data_manager)

    initialize_app(data_manager)

    ui.render_page_setup()
    ui.render_main_layout()


if __name__ == "__main__":
    main()