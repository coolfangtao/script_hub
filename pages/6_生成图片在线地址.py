# app.py
import streamlit as st
import requests
import base64
import uuid
from datetime import datetime

# --- 核心配置 ---
# 导入并实例化全局配置类
from shared.config import GlobalConfig
from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar

# 实例化配置
# 假设 get_run_mode() 和 GlobalConfig 定义在 shared.config 中或可被正确导入
# 如果 get_run_mode() 不在 GlobalConfig 内部，确保它能被正确调用
cfg = GlobalConfig()

track_script_usage("🔗 在线图床")
create_common_sidebar()  # 调用函数创建侧边栏


def upload_image_to_github(image_bytes, original_filename, token, repo_owner, repo_name, image_path=cfg.IMAGE_PATH_IN_REPO):
    """
    将图片字节上传到指定的 GitHub 仓库并返回 jsDelivr CDN URL。
    这是一个通用函数，接收所有必要的认证和路径信息。

    Args:
        image_bytes (bytes): 图片的字节数据。
        original_filename (str): 原始文件名，用于获取文件扩展名。
        token (str): GitHub Personal Access Token.
        repo_owner (str): 仓库所有者的用户名。
        repo_name (str): 仓库的名称。
        image_path (str, optional): 仓库中存放图片的文件夹路径. Defaults to "images".

    Returns:
        str: 成功则返回图片的 jsDelivr CDN URL，失败则返回错误信息。
    """
    if not all([token, repo_owner, repo_name]):
        return "错误：GitHub 配置不完整 (Token, Owner, Repo 必须提供)。"

    try:
        file_extension = original_filename.split('.')[-1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"

        # 构建API URL，处理根目录和子目录的情况
        if image_path:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{image_path}/{unique_filename}"
        else:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{unique_filename}"

        b64_image = base64.b64encode(image_bytes).decode('utf-8')

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        payload = {
            "message": f"feat: Add image {unique_filename}",
            "content": b64_image,
            "committer": {"name": "Streamlit App Uploader", "email": "app@streamlit.io"}
        }

        response = requests.put(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if 'content' in data and 'path' in data['content']:
            cdn_url = f"https://cdn.jsdelivr.net/gh/{repo_owner}/{repo_name}/{data['content']['path']}"
            return cdn_url
        else:
            return f"API返回数据格式不正确: {data}"

    except requests.exceptions.HTTPError as e:
        return f"GitHub API 错误: {e.response.status_code} - {e.response.json().get('message', '无详细信息')}"
    except requests.exceptions.RequestException as e:
        return f"网络请求失败: {e}"
    except Exception as e:
        return f"发生未知错误: {e}"


# --- Streamlit 页面配置 ---
st.set_page_config(page_title="图片转GitHub链接工具", page_icon="🖼️", layout="wide")
st.title("🖼️ 图片转 GitHub 仓库链接工具")
st.markdown("批量上传图片，生成由 jsDelivr CDN 加速的在线链接。")

# --- 初始化变量 ---
github_token = None
repo_owner = None
repo_name = None
is_configured = False

# --- UI 逻辑：根据运行模式（local/cloud）显示不同选项 ---

if cfg.RUN_MODE == "cloud":
    st.subheader("请选择图片存储方式")
    storage_option = st.radio(
        "选择一个选项:",
        ("使用共享的临时仓库 (方便快捷，但图片可能随时被清理)", "使用我自己的 GitHub 仓库 (推荐，数据由您自己掌控)"),
        label_visibility="collapsed"
    )

    if storage_option.startswith("使用共享"):
        st.warning(
            "⚠️ **重要提示**: 您即将把图片上传到一个 **公开共享** 的仓库。"
            "此仓库仅用于功能演示，**不保证数据的永久性**，图片可能会因容量问题被 **不定期清理**。"
            "**请勿上传任何敏感或私人图片！**"
        )
        if cfg.GITHUB_TOKEN and cfg.GITHUB_PUBLIC_REPO:
            github_token = cfg.GITHUB_TOKEN
            repo_owner, repo_name = cfg.GITHUB_PUBLIC_REPO.split('/')
            is_configured = True
        else:
            st.error("管理员未配置共享仓库，此选项不可用。")

    else:  # 使用自己的仓库
        st.info("请提供您自己的 GitHub 信息以确保数据安全和持久。")
        user_repo_input = st.text_input(
            "你的公开仓库 (格式: `用户名/仓库名`)",
            placeholder="e.g., my-username/my-image-repo"
        )
        user_token_input = st.text_input(
            "你的 GitHub Personal Access Token",
            type="password",
            help="需要 `repo` 权限。Token仅在本次上传中使用，不会被存储。"
        )
        if user_repo_input and user_token_input:
            if '/' in user_repo_input:
                github_token = user_token_input
                repo_owner, repo_name = user_repo_input.split('/')
                is_configured = True
            else:
                st.error("仓库格式不正确，请确保格式为 `用户名/仓库名`。")

else:  # local 模式
    st.success("✅ **本地模式**: 使用 `secrets.toml` 中配置的 GitHub 仓库。")
    if cfg.GITHUB_TOKEN and cfg.GITHUB_PUBLIC_REPO:
        github_token = cfg.GITHUB_TOKEN
        repo_owner, repo_name = cfg.GITHUB_PUBLIC_REPO.split('/')
        is_configured = True
    else:
        st.error("本地配置错误: 请检查 secrets.toml 中的 `github_data_token` 和 `github_data_public_repo`。")

st.divider()

# --- 文件上传和处理逻辑 ---
uploaded_files = st.file_uploader(
    "请选择一张或多张图片...",
    type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
    accept_multiple_files=True,
    help="您可以按住`Ctrl`(Windows)或`Command`(Mac)键来选择多张图片。"
)

# 只有当仓库配置完成并且有文件上传时，按钮才可用
if st.button("生成在线链接", disabled=not uploaded_files or not is_configured, type="primary"):
    st.header("处理结果")
    progress_bar = st.progress(0, text="正在准备上传...")
    total_files = len(uploaded_files)
    num_columns = 3
    cols = st.columns(num_columns)

    for i, uploaded_file in enumerate(uploaded_files):
        progress_text = f"正在上传第 {i + 1}/{total_files} 张图片: {uploaded_file.name}"
        progress_bar.progress((i + 1) / total_files, text=progress_text)

        image_bytes = uploaded_file.getvalue()
        col_index = i % num_columns
        with cols[col_index]:
            st.image(image_bytes, caption=f"预览: {uploaded_file.name}", use_container_width=True)
            with st.spinner("正在生成链接..."):
                # 调用通用函数，传入动态获取的配置
                image_url = upload_image_to_github(
                    image_bytes=image_bytes,
                    original_filename=uploaded_file.name,
                    token=github_token,
                    repo_owner=repo_owner,
                    repo_name=repo_name
                )
            if image_url and image_url.startswith("http"):
                st.success("链接生成成功！")
                st.code(image_url, language=None)
            else:
                st.error(f"上传失败: {image_url}")
            st.divider()

    progress_bar.empty()
    st.success("所有图片处理完毕！")