import streamlit as st
from PIL import Image
import io
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 页面配置 ---
st.set_page_config(layout="wide", page_title="图片大小修改器")

# --- 页面内容 ---
st.title("🗜️ 智能图片大小修改器")
st.write("使用此功能时尽量不要打开VPN，否则会很慢")
st.write("上传一张图片，设定您期望的文件大小（单位MB），此工具将自动调整图片质量以逼近该目标大小。")
st.write("")

# --- 主体功能 ---

# 1. 创建文件上传组件
uploaded_file = st.file_uploader("请在这里上传您的图片...", type=['jpg', 'jpeg'])

if uploaded_file:
    # 2. 获取目标文件大小
    # st.number_input 用于接收数字，设置最小值和默认值
    target_size_mb = st.number_input(
        '设定目标文件大小 (MB)',
        min_value=0.1,
        value=1.2,
        step=0.1,
        help="输入您希望图片压缩后的大小，例如 1.2"
    )

    # 将MB转换为字节(Bytes)
    target_size_bytes = target_size_mb * 1024 * 1024

    # 3. 添加一个执行按钮
    if st.button('开始修改尺寸'):

        try:
            # 打开上传的图片
            img = Image.open(uploaded_file)

            # 获取原始图片信息
            original_size_bytes = len(uploaded_file.getvalue())
            original_size_mb = original_size_bytes / (1024 * 1024)

            # --- 核心逻辑：迭代调整图片质量 ---
            # 使用BytesIO在内存中操作图片，避免磁盘读写
            output_image_bytes = io.BytesIO()

            # 我们从一个较高的质量开始 (95)，然后逐步降低
            # quality 是JPEG的压缩质量参数，范围是1-95
            current_quality = 95

            # 进度条，优化用户体验
            progress_bar = st.progress(0, text="正在计算最佳压缩率...")

            # 这是一个简单的二分法或线性搜索的简化版，从高质量开始尝试
            # 找到一个合适的压缩率
            while current_quality > 5:  # 质量低于5的图片通常不可接受
                output_image_bytes.seek(0)  # 重置buffer
                output_image_bytes.truncate()  # 清空buffer

                # 以当前质量保存图片到内存中
                # optimize=True 和 progressive=True 是JPEG优化的选项
                img.save(output_image_bytes, format="JPEG", quality=current_quality, optimize=True, progressive=True)

                # 检查生成的文件大小
                current_size = output_image_bytes.tell()

                # 更新进度条
                progress_percentage = 1 - (current_size - target_size_bytes) / (
                            original_size_bytes - target_size_bytes) if original_size_bytes > target_size_bytes else 1
                progress_bar.progress(min(1.0, max(0.0, progress_percentage)),
                                      text=f"尝试质量 {current_quality} -> 大小 {current_size / 1024 / 1024:.2f} MB")

                if current_size <= target_size_bytes:
                    # 如果当前大小已经小于等于目标，就找到了一个可接受的结果
                    break

                # 降低质量，继续尝试
                current_quality -= 5

            progress_bar.progress(1.0, text="处理完成！")

            # 将指针移到文件开头，准备显示和下载
            output_image_bytes.seek(0)

            # --- 结果展示 ---
            st.write("---")
            st.header("处理结果")

            col1, col2 = st.columns(2)

            final_size_bytes = len(output_image_bytes.getvalue())
            final_size_mb = final_size_bytes / (1024 * 1024)

            with col1:
                st.info(f"**原始图片**")
                st.metric(label="文件大小", value=f"{original_size_mb:.2f} MB")
                st.image(uploaded_file, caption="原始图片", use_column_width=True)

            with col2:
                if final_size_bytes > original_size_bytes:
                    st.warning("目标大小大于原图，已提供原图下载。")
                    st.metric(label="文件大小", value=f"{original_size_mb:.2f} MB")
                    st.image(uploaded_file, caption="大于目标的图片", use_column_width=True)
                    # 提供原图下载
                    st.download_button(
                        label="📥 下载图片",
                        data=uploaded_file.getvalue(),
                        file_name=f"resized_{uploaded_file.name}",
                        mime="image/jpeg"
                    )
                else:
                    st.success(f"**修改后图片**")
                    st.metric(label="文件大小", value=f"{final_size_mb:.2f} MB (目标: {target_size_mb:.2f} MB)")
                    st.image(output_image_bytes, caption=f"修改后图片 (质量: {current_quality})", use_column_width=True)
                    # 6. 创建下载按钮
                    st.download_button(
                        label="📥 下载修改后的图片",
                        data=output_image_bytes,
                        file_name=f"resized_{target_size_mb}MB_{uploaded_file.name}",
                        mime="image/jpeg"
                    )

        except Exception as e:
            st.error(f"处理图片时发生错误: {e}")
            st.error("请确保您上传的是有效的JPG或JPEG图片。")

else:
    # 如果没有文件上传，显示提示信息
    st.info("等待您上传JPEG/JPG格式的图片...")

# --- 页脚 ---
st.write("")
st.markdown("---")