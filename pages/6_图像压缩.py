import streamlit as st
from PIL import Image
import io
from typing import Tuple

# 假设您的侧边栏函数位于此路径
from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar
# track_script_usage("📦 图像压缩")
create_common_sidebar()

# --- 页面配置 ---
st.set_page_config(layout="wide", page_title="图片大小修改器")


def compress_image(
        img: Image.Image,
        target_size_bytes: int,
        original_size_bytes: int
) -> Tuple[io.BytesIO, int]:
    """
    通过迭代调整JPEG质量来压缩图片，直到文件大小接近目标。

    Args:
        img (Image.Image): PIL库打开的图片对象。
        target_size_bytes (int): 目标文件大小（以字节为单位）。
        original_size_bytes (int): 原始文件大小（以字节为单位），用于计算进度。

    Returns:
        Tuple[io.BytesIO, int]: 包含压缩后图片数据（在内存中）和最终质量值的元组。
    """
    # 使用BytesIO在内存中操作图片，避免磁盘读写
    output_image_bytes = io.BytesIO()

    # 从一个较高的质量(95)开始，逐步降低
    # quality 是JPEG的压缩质量参数，范围是1-95
    current_quality = 95

    progress_bar = st.progress(0, text="正在计算最佳压缩率...")

    # 当质量高于5时，进行循环尝试
    while current_quality > 5:
        output_image_bytes.seek(0)  # 重置缓冲区指针
        output_image_bytes.truncate()  # 清空缓冲区内容

        # 以当前质量保存图片到内存中
        img.save(
            output_image_bytes,
            format="JPEG",
            quality=current_quality,
            optimize=True,
            progressive=True
        )

        # 获取当前生成的文件大小
        current_size = output_image_bytes.tell()

        # 更新进度条，提供更好的用户体验
        # 如果目标比原图大，进度直接为100%
        if original_size_bytes <= target_size_bytes:
            progress_percentage = 1.0
        else:
            # 计算一个合理的进度百分比
            progress_percentage = 1 - (current_size - target_size_bytes) / (original_size_bytes - target_size_bytes)

        progress_bar.progress(
            min(1.0, max(0.0, progress_percentage)),
            text=f"尝试质量 {current_quality} -> 大小 {current_size / 1024 / 1024:.2f} MB"
        )

        # 如果当前大小已小于等于目标，则找到了一个可接受的结果
        if current_size <= target_size_bytes:
            break

        # 降低质量，继续尝试
        current_quality -= 5

    progress_bar.progress(1.0, text="处理完成！")
    output_image_bytes.seek(0)  # 将指针移到文件开头，准备后续读取
    return output_image_bytes, current_quality


def display_results(
        original_file,
        original_size_mb: float,
        compressed_data: io.BytesIO,
        final_quality: int,
        target_mb: float
):
    """
    在Streamlit页面上并排显示原始图片和压缩后的图片。

    Args:
        original_file: Streamlit上传的文件对象。
        original_size_mb (float): 原始文件大小 (MB)。
        compressed_data (io.BytesIO): 压缩后的图片数据。
        final_quality (int): 最终使用的压缩质量。
        target_mb (float): 用户设定的目标大小 (MB)。
    """
    st.write("---")
    st.header("处理结果")

    col1, col2 = st.columns(2)

    final_size_bytes = len(compressed_data.getvalue())
    final_size_mb = final_size_bytes / (1024 * 1024)

    with col1:
        st.info("**原始图片**")
        st.metric(label="文件大小", value=f"{original_size_mb:.2f} MB")
        st.image(original_file, caption="原始图片", use_column_width=True)

    with col2:
        # 特殊情况：如果目标大小比原图还大，或压缩后比原图还大，则提示并提供原图
        if final_size_bytes >= (original_size_mb * 1024 * 1024):
            st.warning("目标大小大于或等于原图，已提供原图下载。")
            st.metric(label="文件大小", value=f"{original_size_mb:.2f} MB")
            st.image(original_file, caption="大于或等于目标的图片", use_column_width=True)
            st.download_button(
                label="📥 下载图片",
                data=original_file.getvalue(),
                file_name=f"original_{original_file.name}",
                mime="image/jpeg"
            )
        else:
            st.success("**修改后图片**")
            st.metric(label="文件大小", value=f"{final_size_mb:.2f} MB (目标: {target_mb:.2f} MB)")
            st.image(compressed_data, caption=f"修改后图片 (质量: {final_quality})", use_column_width=True)
            st.download_button(
                label="📥 下载修改后的图片",
                data=compressed_data.getvalue(),
                file_name=f"resized_{target_mb}MB_{original_file.name}",
                mime="image/jpeg"
            )


def main():
    """
    主函数，运行Streamlit应用。
    """
    # --- 页面内容 ---
    st.title("🗜️ 智能图片大小修改器")
    st.write("使用此功能时尽量不要打开VPN，否则会很慢")
    st.write("上传一张图片，设定您期望的文件大小（单位MB），此工具将自动调整图片质量以逼近该目标大小。")
    st.write("")

    # 1. 创建文件上传组件
    uploaded_file = st.file_uploader("请在这里上传您的图片...", type=['jpg', 'jpeg'])

    if not uploaded_file:
        st.info("等待您上传JPEG/JPG格式的图片...")
        return

    # 2. 获取目标文件大小
    target_size_mb = st.number_input(
        '设定目标文件大小 (MB)',
        min_value=0.1,
        value=1.0,
        step=0.1,
        help="输入您希望图片压缩后的大小，例如 1.0"
    )

    # 3. 添加执行按钮
    if st.button('🚀 开始修改尺寸'):
        try:
            # 打开上传的图片
            img = Image.open(uploaded_file)

            # 如果图片是RGBA（带有透明通道），转换为RGB，因为JPEG不支持透明度
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            original_size_bytes = len(uploaded_file.getvalue())
            target_size_bytes = target_size_mb * 1024 * 1024

            # --- 核心逻辑：调用函数进行压缩和显示 ---
            compressed_image_data, final_quality = compress_image(img, target_size_bytes, original_size_bytes)

            display_results(
                original_file=uploaded_file,
                original_size_mb=original_size_bytes / (1024 * 1024),
                compressed_data=compressed_image_data,
                final_quality=final_quality,
                target_mb=target_size_mb
            )

        except Exception as e:
            st.error(f"处理图片时发生错误: {e}")
            st.error("请确保您上传的是有效的JPG或JPEG图片。")

    # --- 页脚 ---
    st.write("")
    st.markdown("---")


if __name__ == "__main__":
    main()