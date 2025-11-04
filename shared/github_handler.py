# 文件路径: shared/github_handler.py

import streamlit as st
import json
import datetime
from github import Github, UnknownObjectException
from shared.config import GlobalConfig


class GitHubDataHandler:
    """
    一个封装了GitHub文件读写操作的通用处理类。

    通过 repo_type ("private" 或 "public") 初始化，
    它会自动从 GlobalConfig 读取对应的仓库名称和Token。
    """

    def __init__(self, repo_type="private"):
        """
        初始化处理器并连接到GitHub仓库。
        :param repo_type: "private" 或 "public"，用于从GlobalConfig中选择仓库。
        """
        self.config = GlobalConfig()
        self.repo = None

        token = self.config.GITHUB_TOKEN
        repo_name = None

        if repo_type == "private":
            repo_name = self.config.GITHUB_PRIVATE_REPO
        elif repo_type == "public":
            repo_name = self.config.GITHUB_PUBLIC_REPO
        else:
            st.error(f"未知的仓库类型: {repo_type}")
            return

        if not token or not repo_name:
            st.error(f"GitHub Token 或 {repo_type} 仓库名称未在Secrets中配置。")
            return

        try:
            g = Github(token)
            self.repo = g.get_repo(repo_name)
        except Exception as e:
            st.error(f"连接到GitHub仓库 {repo_name} 时失败: {e}")
            self.repo = None

    def is_ready(self):
        """检查仓库连接是否成功建立。"""
        return self.repo is not None

    def read_json_file(self, file_path):
        """
        从仓库读取一个JSON文件。

        :param file_path: 文件在仓库中的路径 (例如 "data/my_file.json")
        :return: (data, sha) - data是解码后的dict/list，sha是文件的SHA。
                 如果文件不存在，返回 (None, None)。
        """
        if not self.is_ready():
            return None, None

        try:
            file_content = self.repo.get_contents(file_path)
            decoded_content = file_content.decoded_content.decode("utf-8")
            data = json.loads(decoded_content)
            return data, file_content.sha
        except UnknownObjectException:
            # 文件不存在，这是正常情况
            return None, None
        except Exception as e:
            st.error(f"从GitHub读取 {file_path} 时出错: {e}")
            return None, None

    def write_json_file(self, file_path, data, commit_message_prefix, sha):
        """
        将一个Python字典或列表作为JSON文件写入仓库。

        :param file_path: 文件在仓库中的路径
        :param data: 要写入的Python对象 (dict/list)
        :param commit_message_prefix: 提交信息的前缀 (会自动附加时间戳)
        :param sha: 文件的SHA。如果提供了SHA，则更新文件；如果为None，则创建文件。
        :return: 成功时返回 True，失败时返回 False。
        """
        if not self.is_ready():
            return False

        try:
            data_str = json.dumps(data, indent=4, ensure_ascii=False)
            commit_message = f"{commit_message_prefix} {datetime.datetime.now(self.config.APP_TIMEZONE)}"

            if sha:
                self.repo.update_file(
                    file_path,
                    commit_message,
                    data_str,
                    sha
                )
            else:
                self.repo.create_file(
                    file_path,
                    commit_message,
                    data_str
                )
            return True
        except Exception as e:
            st.error(f"写入 {file_path} 到GitHub时出错: {e}")
            return False


# --- 缓存的工厂函数 ---
# 这些函数确保我们在Streamlit应用中重用同一个GitHubDataHandler实例

@st.cache_resource(ttl=3600)
def get_private_data_handler():
    """
    获取一个缓存的、连接到私有仓库的 GitHubDataHandler 实例。
    """
    return GitHubDataHandler(repo_type="private")


@st.cache_resource(ttl=3600)
def get_public_data_handler():
    """
    获取一个缓存的、连接到公共仓库的 GitHubDataHandler 实例。
    """
    return GitHubDataHandler(repo_type="public")