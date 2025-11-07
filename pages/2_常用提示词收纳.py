# pages/Prompts.py

import streamlit as st
import os
import json
import uuid
from datetime import datetime, timezone
import base64
from github import Github, GithubException
from contextlib import contextmanager

# 导入你的配置类
# 假设 pages 目录和 shared 目录同级，需要调整 Python 路径
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from shared.config import GlobalConfig
    from shared.sidebar import create_common_sidebar
except ImportError:
    st.error("无法导入 `shared.config`。请确保 `shared/config.py` 文件存在。")
    st.stop()


class PromptConfig(GlobalConfig):
    """
    专门用于提示词页面的配置类，继承自 GlobalConfig
    """

    def __init__(self):
        super().__init__()

        # 2. 提示词 JSON 文件的路径
        self.LOCAL_PROMPT_FILE = os.path.join("private_data", "prompts.json")
        self.GITHUB_PROMPT_FILE = "prompts.json"  # 在 GitHub 仓库中的路径

# ---------------------------------------------------------------------
# 1. GitHub 数据管理器
# ---------------------------------------------------------------------

class GitHubDataManager:
    """
    用于处理所有与 GitHub 相关的读写操作。
    """

    def __init__(self, token, repo_name):
        if not token or not repo_name:
            st.error("GitHub Token 或仓库名称未配置。")
            self.github = None
            self.repo = None
            return

        try:
            self.github = Github(token)
            self.repo = self.github.get_repo(repo_name)
        except Exception as e:
            st.error(f"连接 GitHub 失败: {e}")
            self.github = None
            self.repo = None

    def get_file(self, file_path):
        """
        从 GitHub 获取文件内容和 sha
        """
        if not self.repo:
            return None, None
        try:
            file = self.repo.get_contents(file_path)
            content = base64.b64decode(file.content).decode("utf-8")
            return content, file.sha
        except GithubException as e:
            if e.status == 404:
                # st.warning(f"GitHub: 文件 {file_path} 未找到。")
                return None, None  # 文件不存在
            else:
                st.error(f"从 GitHub 获取文件时出错: {e}")
                return None, None
        except Exception as e:
            st.error(f"解码 GitHub 文件时出错: {e}")
            return None, None

    def save_file(self, file_path, content, sha, commit_message):
        """
        保存（更新或创建）文件到 GitHub
        """
        if not self.repo:
            return False
        try:
            if sha:
                # 更新现有文件
                self.repo.update_file(file_path, commit_message, content, sha)
            else:
                # 创建新文件
                self.repo.create_file(file_path, commit_message, content)
            # st.success(f"已同步到 GitHub: {commit_message}")
            return True
        except Exception as e:
            st.error(f"保存到 GitHub 时出错: {e}")
            return False


# ---------------------------------------------------------------------
# 2. 提示词数据管理类
# ---------------------------------------------------------------------

class PromptData:
    """
    管理所有提示词模板数据（本地/远程的 CRUD 和同步）
    根据运行模式（local/cloud）采用不同的读写策略
    """

    def __init__(self, config: PromptConfig, github_manager: GitHubDataManager):
        self.config = config
        self.github_manager = github_manager
        self.local_path = config.LOCAL_PROMPT_FILE
        self.remote_path = config.GITHUB_PROMPT_FILE

        # 确保本地目录存在（仅在本地模式下有意义，但在云端运行也无害）
        os.makedirs(os.path.dirname(self.local_path), exist_ok=True)

        self.data = {"last_modified": self.get_utc_now_iso(), "prompts": {}}
        self.remote_sha = None

        # 调用新的同步/加载逻辑
        self.load_data_based_on_mode()

    def get_utc_now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _load_local_data(self):
        """加载本地 JSON 文件"""
        if os.path.exists(self.local_path):
            try:
                with open(self.local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                st.error("本地 prompts.json 文件损坏。")
                return None
        return None

    def _load_remote_data(self):
        """加载远程 GitHub JSON 文件"""
        content, sha = self.github_manager.get_file(self.remote_path)
        if content:
            try:
                data = json.loads(content)
                self.remote_sha = sha  # 保存 sha 以便后续更新
                return data
            except json.JSONDecodeError:
                st.error("GitHub 上的 prompts.json 文件损坏。")
                return None
        self.remote_sha = None  # 文件不存在
        return None

    def _save_local_data(self):
        """将当前数据保存到本地"""
        try:
            with open(self.local_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            st.error(f"保存本地文件失败: {e}")

    def _save_remote_data(self, commit_message):
        """将当前数据保存到 GitHub"""
        try:
            content = json.dumps(self.data, indent=4, ensure_ascii=False)
            success = self.github_manager.save_file(
                self.remote_path,
                content,
                self.remote_sha,
                commit_message
            )
            if success:
                # 成功后，需要重新获取 sha
                _, self.remote_sha = self.github_manager.get_file(self.remote_path)
        except Exception as e:
            st.error(f"保存到 GitHub 失败: {e}")

    def load_data_based_on_mode(self):
        """
        (核心逻辑更新)
        根据运行模式（local/cloud）加载数据
        """
        st.info(f"正在 {self.config.RUN_MODE} 模式下检查数据同步...")

        if self.config.RUN_MODE == "cloud":
            # --- 云端模式 ---
            # 只从 GitHub 加载。不关心本地文件。
            st.info("云端模式：从 GitHub 加载数据。")
            remote_data = self._load_remote_data()
            if remote_data:
                self.data = remote_data
                st.success("成功从 GitHub 加载数据。")
            else:
                # GitHub 没数据，初始化
                st.warning("GitHub 中未找到数据文件。如果登录，将创建新文件。")
                self.data = {"last_modified": self.get_utc_now_iso(), "prompts": {}}
                # (注意：只有在认证后，第一次保存时才会真的创建文件)

        else:
            # --- 本地模式 ---
            # 执行原有的“比对-同步”逻辑
            st.info("本地模式：正在同步本地与 GitHub 数据...")
            local_data = self._load_local_data()
            remote_data = self._load_remote_data()

            local_time = local_data.get("last_modified") if local_data else None
            remote_time = remote_data.get("last_modified") if remote_data else None

            if local_time and remote_time:
                if local_time >= remote_time:
                    # 本地最新或相同
                    self.data = local_data
                    if local_time > remote_time:
                        st.warning("本地数据较新，正在同步到云端...")
                        self._save_remote_data("Sync: local to remote (load)")
                else:
                    # 远程最新
                    st.warning("云端数据较新，正在更新本地...")
                    self.data = remote_data
                    self._save_local_data()  # 只更新本地
            elif local_data:
                # 只有本地
                st.info("仅找到本地数据，正在同步到云端...")
                self.data = local_data
                self._save_remote_data("Sync: Initial upload (local)")
            elif remote_data:
                # 只有远程
                st.info("仅找到云端数据，正在同步到本地...")
                self.data = remote_data
                self._save_local_data()  # 只保存到本地
            else:
                # 两边都没有，创建新数据
                st.info("未找到数据，正在创建新的配置文件...")
                self._save_all("Sync: Initial create")  # _save_all 会处理双端保存

            st.success("数据同步完成。")

    def _save_all(self, commit_message):
        """
        (核心逻辑更新)
        当数据发生变动时，根据模式更新。
        - local: 更新本地 + 远程
        - cloud: (需认证) 仅更新远程
        """
        self.data["last_modified"] = self.get_utc_now_iso()

        if self.config.RUN_MODE == "local":
            # --- 本地模式 ---
            # 保存到两处
            self._save_local_data()
            self._save_remote_data(commit_message)

        else:
            # --- 云端模式 ---
            # 只保存到远程，且必须已认证
            if st.session_state.get("authenticated", False):
                self._save_remote_data(commit_message)
            else:
                # 理论上 UI 会阻止未认证的保存，但作为双重保险
                st.error("未认证，无法在云端模式下保存。")

    # --- CRUD (增删改查) 方法保持不变 ---
    # 它们调用 _save_all()，所以会自动适配新逻辑

    def get_all_prompts(self):
        """获取所有提示词，按名称排序"""
        prompts = self.data.get("prompts", {})
        # 按名称排序
        sorted_items = sorted(prompts.items(), key=lambda item: item[1].get('name', ''))
        return dict(sorted_items)

    def add_prompt(self, name, content):
        """新增提示词"""
        p_id = str(uuid.uuid4())
        self.data["prompts"][p_id] = {
            "name": name,
            "content": content
        }
        self._save_all(f"Add prompt: {name}")
        st.success(f"提示词 '{name}' 已添加。")

    def update_prompt(self, p_id, name, content):
        """编辑提示词"""
        if p_id in self.data["prompts"]:
            self.data["prompts"][p_id] = {
                "name": name,
                "content": content
            }
            self._save_all(f"Update prompt: {name}")
            st.success(f"提示词 '{name}' 已更新。")
        else:
            st.error("提示词 ID 不存在。")

    def delete_prompt(self, p_id):
        """删除提示词"""
        if p_id in self.data["prompts"]:
            name = self.data["prompts"].pop(p_id).get("name", "N/A")
            self._save_all(f"Delete prompt: {name}")
            st.success(f"提示词 '{name}' 已删除。")


# ---------------------------------------------------------------------
# 3. Streamlit UI 界面类
# ---------------------------------------------------------------------

class PromptUI:
    """
    管理所有 Streamlit 界面元素
    """

    def __init__(self, data_manager: PromptData, config: PromptConfig):
        self.data_manager = data_manager
        self.config = config

        # 状态管理，用于跟踪正在编辑的条目
        if "editing_prompt_id" not in st.session_state:
            st.session_state.editing_prompt_id = None
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False

    def display_auth(self):
        """(需求 3) 在云端模式下显示密码输入框"""
        if self.config.RUN_MODE == "cloud" and not st.session_state.authenticated:
            st.info("这是一个云端实例。请输入密码以启用编辑和同步功能。")

            password = st.text_input("请输入访问密码：", type="password", key="cloud_pass_input")
            if st.button("登录"):
                if password == self.config.APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("验证成功！已启用完整功能。")
                    st.rerun()
                else:
                    st.error("密码错误。")
            return False  # 未认证

        # 本地模式或已认证的云端模式
        if self.config.RUN_MODE == "local" and not st.session_state.authenticated:
            st.session_state.authenticated = True  # 本地模式自动认证
        return True  # 已认证

    # ↓↓↓ 错误已修复：删除了 @contextmanager 装饰器 ↓↓↓
    def _prompt_form(self, p_id=None):
        """
        一个用于新增或编辑的表单。
        这是一个生成器，仅在表单提交时 yield 数据。
        """
        if p_id:
            # 编辑模式
            prompt = self.data_manager.data["prompts"][p_id]
            default_name = prompt.get("name")
            default_content = prompt.get("content")
        else:
            # 新增模式
            default_name = ""
            default_content = ""

        with st.form(key=f"form_{p_id or 'new'}"):
            name = st.text_input("提示词名称", value=default_name)
            content = st.text_area("提示词内容", value=default_content, height=200)

            submit_col, cancel_col = st.columns([1, 5])
            submitted = submit_col.form_submit_button("保存")

            # 只有编辑时才显示取消按钮
            if p_id:
                if cancel_col.form_submit_button("取消"):
                    st.session_state.editing_prompt_id = None
                    st.rerun()

            if submitted:
                if not name or not content:
                    st.error("名称和内容不能为空。")
                else:
                    yield name, content  # 将数据传出

    def display_add_form(self):
        """显示"新增提示词"的折叠表单"""
        with st.expander("✚ 新增提示词"):
            # ↓↓↓ 修复：移除了 try...except StopIteration ↓↓↓
            for name, content in self._prompt_form():
                # 当表单提交时，
                self.data_manager.add_prompt(name, content)
                st.rerun()

    def display_edit_form(self, p_id):
        """在容器内显示编辑表单"""
        st.info("正在编辑...")
        # ↓↓↓ 修复：移除了 try...except StopIteration ↓↓↓
        for name, content in self._prompt_form(p_id=p_id):
            # 当表单提交时
            self.data_manager.update_prompt(p_id, name, content)
            st.session_state.editing_prompt_id = None  # 关闭编辑状态
            st.rerun()

    def display_prompt_list(self):
        """(需求 4) 显示所有提示词列表"""
        prompts = self.data_manager.get_all_prompts()

        if not prompts:
            st.info("暂无提示词，请点击'新增提示词'添加。")
            return

        st.header("提示词列表")

        for p_id, prompt in prompts.items():

            # 如果当前条目处于编辑状态，显示编辑表单
            if st.session_state.editing_prompt_id == p_id:
                with st.container(border=True):
                    self.display_edit_form(p_id)
                continue

            # 否则，显示折叠容器
            with st.expander(prompt.get("name", "未命名")):
                st.markdown(f"**提示词 ID：** `{p_id}`")

                st.markdown("**提示词内容：**")
                st.code(prompt.get("content", ""), language=None)

                col1, col2, _ = st.columns([1, 1, 5])

                # 编辑按钮
                if col1.button("编辑", key=f"edit_{p_id}"):
                    st.session_state.editing_prompt_id = p_id
                    st.rerun()

                # 删除按钮
                if col2.button("删除", key=f"delete_{p_id}", type="primary"):
                    self.data_manager.delete_prompt(p_id)
                    st.rerun()

    def run(self):
        """运行整个 UI"""
        st.title("🤖 AI 提示词管理器")

        # 1. 处理认证
        if not self.display_auth():
            st.stop()  # 如果未认证且在云端，停止渲染后续内容

        # 2. 显示新增表单
        self.display_add_form()

        st.divider()

        # 3. 显示提示词列表
        self.display_prompt_list()


# ---------------------------------------------------------------------
# 4. 主程序入口
# ---------------------------------------------------------------------

def main():
    st.set_page_config(page_title="提示词管理器", layout="wide")
    create_common_sidebar(current_label="📄 提示词收纳")

    # 1. 初始化配置
    try:
        config = PromptConfig()
    except Exception as e:
        st.error(f"加载配置失败: {e}")
        st.stop()

    # 2. 初始化 GitHub 管理器
    github_manager = GitHubDataManager(config.GITHUB_TOKEN, config.GITHUB_PRIVATE_REPO)
    if not github_manager.repo:
        st.error("无法初始化 GitHub 管理器，请检查 secrets 配置。")
        st.stop()

    # 3. 初始化数据管理器 (核心逻辑在此)
    # 使用 session_state 缓存数据管理器，防止重复加载和同步
    if "prompt_data_manager" not in st.session_state:
        with st.spinner("正在初始化数据..."):
            st.session_state.prompt_data_manager = PromptData(config, github_manager)

    data_manager = st.session_state.prompt_data_manager

    # 4. 初始化并运行 UI
    ui = PromptUI(data_manager, config)
    ui.run()


if __name__ == "__main__":
    main()