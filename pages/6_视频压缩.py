import streamlit as st
import subprocess
import tempfile
import os
import io
import zipfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from shared.sidebar import create_common_sidebar


# --- 1. 配置类 ---
class Config:
    """
    收纳所有常用配置
    """
    APP_TITLE = "🎬 视频压缩工具"
    PAGE_ICON = "🎬"
    ALLOWED_TYPES = ['mp4', 'mov', 'avi', 'mkv', 'webm']

    # FFMPEG 压缩配置
    # Constant Rate Factor (CRF): 0 (无损) - 51 (最差).
    # 23 是默认值. 28-30 提供了很好的压缩率，质量可接受.
    FFMPEG_CRF = 28

    # 编码预设: ultrafast, superfast, veryfast, faster, fast, medium, slow
    # 'fast' 是速度和压缩率的良好平衡
    FFMPEG_PRESET = "fast"

    # 强制输出格式
    OUTPUT_FORMAT = "mp4"


# --- 2. 视频处理逻辑 (解耦) ---
class VideoProcessor:
    """
    封装所有 FFMPEG 核心压缩逻辑
    """

    def __init__(self, config: Config):
        self.config = config

    def _get_output_filename(self, original_name: str) -> str:
        """生成压缩后的文件名"""
        stem = Path(original_name).stem
        return f"{stem}_compressed.{self.config.OUTPUT_FORMAT}"

    def compress_video(self, input_path: str, output_path: str) -> Tuple[bool, Optional[str]]:
        """
        使用 FFMPEG 子进程执行压缩

        Args:
            input_path (str): 临时保存的原始视频路径
            output_path (str): 压缩后视频的输出路径

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        command = [
            'ffmpeg',
            '-i', str(input_path),  # 输入文件
            '-vcodec', 'libx264',  # 使用 H.264 编解码器
            '-crf', str(self.config.FFMPEG_CRF),  # 设置恒定速率因子
            '-preset', self.config.FFMPEG_PRESET,  # 设置编码预设
            '-y',  # 覆盖已存在输出文件
            str(output_path)
        ]

        try:
            # 运行命令
            # capture_output=True 会捕获 stdout 和 stderr
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            return True, None
        except subprocess.CalledProcessError as e:
            # FFMPEG 运行出错
            error_message = f"FFmpeg 处理失败: \n{e.stderr}"
            print(error_message)
            return False, error_message
        except FileNotFoundError:
            # 关键错误：服务器上没有安装 FFMPEG
            error_message = "错误：未找到 `ffmpeg`。请确保它已安装并在系统 PATH 中。"
            print(error_message)
            # 立即在 Streamlit 中显示这个关键错误
            st.error(error_message)
            return False, error_message

    def process_uploaded_files(self, uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile]):
        """
        【核心逻辑】
        逐个处理上传的文件列表，以减少瞬时服务器负载。
        将结果存储在 st.session_state 中。
        """

        # 确保 session_state 中有存储结果的地方
        if "compressed_files" not in st.session_state:
            st.session_state.compressed_files = {}

        # 使用一个占位符来显示当前处理状态
        progress_placeholder = st.empty()
        total_files = len(uploaded_files)

        for i, uploaded_file in enumerate(uploaded_files):
            # 检查是否已处理过 (防止重复处理)
            if uploaded_file.name in st.session_state.compressed_files:
                continue

            progress_placeholder.info(f"⏳ 正在处理第 {i + 1} / {total_files} 个视频: {uploaded_file.name}...")

            # 使用临时目录来安全地处理文件
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 创建临时输入路径并保存上传的文件
                input_path = os.path.join(temp_dir, uploaded_file.name)
                with open(input_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())

                # 2. 准备输出路径
                output_filename = self._get_output_filename(uploaded_file.name)
                output_path = os.path.join(temp_dir, output_filename)

                # 3. 执行压缩
                success, error_msg = self.compress_video(input_path, output_path)

                if success:
                    # 4. 压缩成功，读取文件内容到内存
                    with open(output_path, 'rb') as f:
                        compressed_data = f.read()

                    # 5. 将 (压缩数据, 压缩文件名) 存入 session_state
                    st.session_state.compressed_files[uploaded_file.name] = (compressed_data, output_filename)
                else:
                    st.warning(f"跳过文件 {uploaded_file.name} (压缩失败). 错误: {error_msg}")

        # 清空处理状态提示
        progress_placeholder.empty()


# --- 3. UI 类 ---
class VideoCompressorUI:
    """
    管理所有 Streamlit 界面元素
    """

    def __init__(self, config: Config):
        self.config = config
        st.set_page_config(page_title=self.config.APP_TITLE, page_icon=self.config.PAGE_ICON, layout="wide")

    def display_header(self):
        """显示标题和说明"""
        st.title(self.config.APP_TITLE)
        st.info(f"""
        欢迎使用！上传一个或多个视频文件。
        * 系统将使用 FFMPEG (CRF={self.config.FFMPEG_CRF}, Preset={self.config.FFMPEG_PRESET}) 逐个压缩它们。
        * 处理大文件可能需要几分钟时间，请耐心等待。
        """)
        create_common_sidebar(current_label="🎬 视频压缩")

    def display_uploader(self) -> Optional[List[st.runtime.uploaded_file_manager.UploadedFile]]:
        """
        显示文件上传组件 (不在侧边栏)
        """
        uploaded_files = st.file_uploader(
            "选择视频文件...",
            type=self.config.ALLOWED_TYPES,
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        return uploaded_files

    def display_results(self):
        """
        显示压缩结果和下载按钮
        """
        if "compressed_files" in st.session_state and st.session_state.compressed_files:
            st.subheader("🎉 压缩完成！")

            results = st.session_state.compressed_files
            files_to_zip = []  # 用于 "一键下载"

            for original_name, (data, compressed_name) in results.items():
                # 为每个文件创建一个下载区域
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(f"原始文件: {original_name}")
                        st.text(f"压缩后文件: {compressed_name}")

                    with col2:
                        st.download_button(
                            label=f"📥 下载 {compressed_name}",
                            data=data,
                            file_name=compressed_name,
                            mime="video/mp4",
                            key=f"download_{original_name}",
                            use_container_width=True
                        )

                files_to_zip.append((compressed_name, data))

            # "一键下载所有" 按钮
            if len(files_to_zip) > 1:
                self.display_download_all_zip(files_to_zip)

    def display_download_all_zip(self, files_to_zip: List[Tuple[str, bytes]]):
        """
        创建并显示一个 "一键下载" 的 ZIP 按钮
        """
        zip_buffer = io.BytesIO()

        # 在内存中创建 ZIP 文件
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name, file_data in files_to_zip:
                zip_file.writestr(file_name, file_data)

        zip_buffer.seek(0)

        st.download_button(
            label="🗂️ 一键下载所有压缩视频 (.zip)",
            data=zip_buffer,
            file_name="compressed_videos.zip",
            mime="application/zip",
            use_container_width=True
        )


# --- 4. 主程序 ---
def main():
    # 初始化
    config = Config()
    ui = VideoCompressorUI(config)
    processor = VideoProcessor(config)

    # 渲染 UI
    ui.display_header()

    uploaded_files = ui.display_uploader()

    # 状态管理：
    # 检查 session_state，决定是否需要显示 "开始压缩" 按钮
    # 1. 检查是否 *新* 上传了文件 (uploaded_files 列表不为空)
    # 2. 检查这些新文件是否 *尚未* 被处理 (即不在 st.session_state.compressed_files 中)

    files_to_process = False
    if uploaded_files:
        if "compressed_files" not in st.session_state:
            st.session_state.compressed_files = {}

        # 检查是否有任何一个上传的文件不在已处理的列表中
        for f in uploaded_files:
            if f.name not in st.session_state.compressed_files:
                files_to_process = True
                break

        # 如果上传的文件都已经在 state 中了，说明是 rerun 后
        if not files_to_process and st.session_state.compressed_files:
            st.info("所有已上传的视频都已处理完毕。如需重新处理，请刷新页面或上传新文件。")

    if files_to_process:
        # 如果有新文件，显示 "开始" 按钮
        if st.button(f"开始压缩 {len(uploaded_files)} 个视频", use_container_width=True, type="primary"):
            # 点击按钮时，清空旧结果，开始处理新批次
            st.session_state.compressed_files = {}
            processor.process_uploaded_files(uploaded_files)

            # 处理完成后，立即重新运行脚本以显示下载按钮
            st.rerun()

    # 无论何时，只要 session_state 中有结果，就显示它们
    ui.display_results()


if __name__ == "__main__":
    # 关键依赖项检查
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        main()
    except (subprocess.CalledProcessError, FileNotFoundError):
        st.error("严重错误：未在系统中找到 FFMPEG。")
        st.error("请在运行此 Streamlit 应用的服务器上安装 FFMPEG，并确保它在系统的 PATH 环境变量中。")
        st.code("例如 (Ubuntu/Debian): \nsudo apt update \nsudo apt install ffmpeg")
        st.code("例如 (macOS): \nbrew install ffmpeg")