import streamlit as st
import requests
import json
from datetime import datetime
from shared.config import GlobalConfig


class UsageTracker:
    def __init__(self):
        self.config = GlobalConfig()
        self.base_url = f"https://api.github.com/repos/{self.config.GITHUB_PUBLIC_REPO}/contents"

    def _get_headers(self):
        """获取 GitHub API 请求头"""
        return {
            "Authorization": f"token {self.config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _get_file_sha(self, file_path):
        """获取文件的 SHA 值"""
        try:
            url = f"{self.base_url}/{file_path}"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                return response.json()["sha"]
            return None
        except:
            return None

    def _read_usage_data(self):
        """从 GitHub 读取使用数据"""
        try:
            url = f"{self.base_url}/{self.config.USAGE_DATA_FILE}"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                content = response.json()["content"]
                # Base64 解码
                import base64
                decoded_content = base64.b64decode(content).decode('utf-8')
                return json.loads(decoded_content)
        except:
            pass
        return {}

    def _save_usage_data(self, data):
        """保存使用数据到 GitHub"""
        try:
            url = f"{self.base_url}/{self.config.USAGE_DATA_FILE}"
            headers = self._get_headers()

            # 获取文件 SHA（如果存在）
            sha = self._get_file_sha(self.config.USAGE_DATA_FILE)

            # 准备请求数据
            content = json.dumps(data, ensure_ascii=False, indent=2)
            encoded_content = content.encode('utf-8')
            import base64
            base64_content = base64.b64encode(encoded_content).decode('utf-8')

            payload = {
                "message": f"Update script usage data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "content": base64_content,
                "branch": "main"
            }

            if sha:
                payload["sha"] = sha

            response = requests.put(url, headers=headers, json=payload)
            return response.status_code == 200 or response.status_code == 201
        except Exception as e:
            st.error(f"保存使用数据失败: {e}")
            return False

    def track_usage(self, script_name, script_path):
        """跟踪脚本使用情况"""
        try:
            # 读取现有数据
            usage_data = self._read_usage_data()

            # 更新计数
            if script_path not in usage_data:
                usage_data[script_path] = {
                    "script_name": script_name,
                    "count": 0,
                    "last_accessed": None,
                    "first_accessed": None
                }

            usage_data[script_path]["count"] += 1
            usage_data[script_path]["last_accessed"] = datetime.now().isoformat()

            if not usage_data[script_path]["first_accessed"]:
                usage_data[script_path]["first_accessed"] = datetime.now().isoformat()

            # 异步保存（不阻塞主线程）
            import threading
            thread = threading.Thread(target=self._save_usage_data, args=(usage_data,))
            thread.start()

            return True
        except Exception as e:
            st.error(f"跟踪使用数据失败: {e}")
            return False

    def get_usage_stats(self):
        """获取使用统计"""
        try:
            usage_data = self._read_usage_data()

            # 按访问次数排序
            sorted_data = sorted(
                usage_data.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )

            return {
                "total_scripts": len(usage_data),
                "total_visits": sum(data["count"] for _, data in usage_data.items()),
                "top_scripts": sorted_data[:10]  # 返回前10个最常用的脚本
            }
        except:
            return {
                "total_scripts": 0,
                "total_visits": 0,
                "top_scripts": []
            }


# 创建全局实例
usage_tracker = UsageTracker()


def track_script_usage(script_name):
    """公共函数：在页面开头调用此函数来跟踪访问"""
    import streamlit as st

    # 获取当前脚本路径
    script_path = st.runtime.scriptrunner.script_run_context.get_script_run_ctx().main_script_path

    # 跟踪使用情况
    usage_tracker.track_usage(script_name, script_path)

    return usage_tracker.get_usage_stats()