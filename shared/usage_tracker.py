import streamlit as st
import requests
import json
import base64
import threading
import logging
from datetime import datetime
from shared.config import GlobalConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class UsageTracker:
    def __init__(self):
        self.config = GlobalConfig()
        self.base_url = f"https://api.github.com/repos/{self.config.GITHUB_PUBLIC_REPO}/contents"
        # 线程锁，用于防止竞态条件
        self.lock = threading.Lock()

    def _get_headers(self):
        """获取 GitHub API 请求头"""
        return {
            "Authorization": f"token {self.config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _read_usage_data(self):
        """
        从 GitHub 读取使用数据。
        返回 (data, sha) 或 (None, None) 如果失败。
        """
        try:
            url = f"{self.base_url}/{self.config.USAGE_DATA_FILE}"
            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                result = response.json()
                content = result["content"]
                sha = result["sha"]
                decoded_content = base64.b64decode(content).decode('utf-8')
                return json.loads(decoded_content), sha

            elif response.status_code == 404:
                # 文件不存在，这是正常情况，返回空数据
                logging.info("Usage data file not found. Creating a new one.")
                return {}, None

        except (requests.exceptions.RequestException, json.JSONDecodeError, base64.binascii.Error) as e:
            logging.error(f"读取使用数据失败: {e}")

        # 任何其他错误都表示失败
        return None, None

    def _save_usage_data(self, data, sha):
        """
        保存使用数据到 GitHub。
        'sha' 是必须的（如果是新文件则为 None）。
        """
        try:
            url = f"{self.base_url}/{self.config.USAGE_DATA_FILE}"
            headers = self._get_headers()

            content = json.dumps(data, ensure_ascii=False, indent=2)
            base64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

            payload = {
                "message": f"Update script usage data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "content": base64_content,
                "branch": "main"
            }

            if sha:
                payload["sha"] = sha

            response = requests.put(url, headers=headers, json=payload)

            if response.status_code == 200 or response.status_code == 201:
                logging.info("使用数据保存成功。")
                return True
            else:
                # 409 Conflict 意味着竞态条件（SHA不匹配），但我们的锁应该阻止这个
                logging.error(f"保存使用数据失败: {response.status_code} {response.text}")
                return False

        except Exception as e:
            logging.error(f"保存使用数据时发生异常: {e}")
            return False

    def _update_in_thread(self, script_name, script_path):
        """
        在线程中安全地更新计数（获取锁，执行 读-改-写）。
        这是防止竞态条件的核心。
        """
        with self.lock:
            try:
                # 1. 读取
                usage_data, sha = self._read_usage_data()

                # 如果读取失败，中止操作以防覆盖
                if usage_data is None:
                    logging.error("无法读取 usage_data，更新中止。")
                    return

                # 2. 修改
                if script_path not in usage_data:
                    usage_data[script_path] = {
                        "script_name": script_name,
                        "count": 0,
                        "last_accessed": None,
                        "first_accessed": datetime.now().isoformat()
                    }

                usage_data[script_path]["count"] += 1
                usage_data[script_path]["last_accessed"] = datetime.now().isoformat()

                # 3. 写入
                self._save_usage_data(usage_data, sha)

            except Exception as e:
                # 捕获线程中的任何其他异常
                logging.error(f"线程更新时发生未捕获异常: {e}")

    def track_usage(self, script_name, script_path):
        """
        跟踪脚本使用情况（通过启动一个安全的异步线程）。
        """
        try:
            # 启动线程执行原子更新
            thread = threading.Thread(
                target=self._update_in_thread,
                args=(script_name, script_path)
            )
            thread.start()
            return True
        except Exception as e:
            # 这是主线程中的错误（例如线程启动失败）
            st.error(f"启动跟踪线程失败: {e}")
            return False

    @st.cache_data(ttl=600)  # 核心！缓存10分钟
    def get_usage_stats(self):
        """
        获取使用统计（带缓存）。
        这会大大减少 API 调用。
        """
        try:
            usage_data, _ = self._read_usage_data()  # 我们不需要这里的 sha

            if usage_data is None:
                logging.warning("无法获取统计数据，返回空值。")
                usage_data = {}  # 返回空值而不是 None

            sorted_data = sorted(
                usage_data.items(),
                key=lambda x: x[1].get("count", 0),  # 使用 .get() 增加鲁棒性
                reverse=True
            )

            return {
                "total_scripts": len(usage_data),
                "total_visits": sum(data.get("count", 0) for _, data in usage_data.items()),
                "top_scripts": sorted_data[:10]
            }
        except Exception as e:
            logging.error(f"计算统计数据时出错: {e}")
            return {"total_scripts": 0, "total_visits": 0, "top_scripts": []}


# 创建全局实例
usage_tracker = UsageTracker()


def track_script_usage(script_name=None):
    """公共函数：在页面开头调用此函数来跟踪访问"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()

        if ctx is None:
            script_path = "unknown_script.py"
        else:
            script_path = ctx.main_script_path

    except Exception:
        script_path = "unknown_script.py"

    if script_name is None:
        # 从路径中提取文件名
        script_name = script_path.split('/')[-1].split('\\')[-1]

    # 跟踪使用情况（不再返回 stats，以减少 API 调用）
    usage_tracker.track_usage(script_name, script_path)


def show_usage_stats():
    """在侧边栏显示脚本使用统计"""
    try:
        # 获取使用统计（现在将从缓存中读取）
        stats = usage_tracker.get_usage_stats()

        with st.sidebar.expander("📊 使用统计", expanded=True):
            col1, col2 = st.columns(2)
            col1.metric("总访问", stats['total_visits'])
            col2.metric("总脚本", stats['total_scripts'])

            if stats['top_scripts']:
                st.markdown("**🔥 热门功能:**")
                for i, (path, data) in enumerate(stats['top_scripts'][:3], 1):
                    # 检查 'data' 是否是字典并且有 'script_name'
                    if isinstance(data, dict):
                        name = data.get('script_name', 'N/A')
                        count = data.get('count', 0)
                        st.write(f"{i}. {name} - {count}次")
                    else:
                        logging.warning(f"统计数据格式不正确: {path}")

            if st.button("🔄 刷新统计", use_container_width=True):
                # 清除缓存并重新运行
                usage_tracker.get_usage_stats.clear()
                st.rerun()

    except Exception as e:
        st.sidebar.error("统计加载失败")
        st.sidebar.debug(f"错误详情: {e}")
