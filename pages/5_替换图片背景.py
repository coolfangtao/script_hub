import streamlit as st
from rembg import remove
from PIL import Image
import io

# --- 1. 导入和调用侧边栏 ---
try:
    # 假设 shared.sidebar 模块在同一个父目录下
    from shared.sidebar import create_common_sidebar

    create_common_sidebar()  # 调用函数，确保每个页面都有侧边栏
except ImportError:
    st.sidebar.warning("未找到 'shared.sidebar' 模块，侧边栏将不会显示。")


# --- 2. 核心处理函数 (带缓存) ---
@st.cache_data
def process_image(image_bytes):
    """
    接收图片字节流，移除背景，替换为白色，并返回PIL图像和可供下载的字节流。
    使用 @st.cache_data 缓存计算结果。
    """
    try:
        # 使用 rembg 库移除背景
        output_image_no_bg = remove(image_bytes)

        # 将处理后的图片（bytes）转换回Pillow Image对象
        output_image = Image.open(io.BytesIO(output_image_no_bg))

        # 创建一个纯白色的背景
        white_background = Image.new("RGB", output_image.size, (255, 255, 255))

        # 将无背景图片粘贴到白色背景上
        white_background.paste(output_image, (0, 0), output_image)

        # 准备可供下载的字节流
        final_image_bytes_io = io.BytesIO()
        white_background.save(final_image_bytes_io, format="PNG")
        final_image_bytes_io.seek(0)

        # 返回 PIL 图像（用于显示）和 bytes（用于下载）
        return white_background, final_image_bytes_io.getvalue()

    except Exception as e:
        st.error(f"处理图片时发生错误 (rembg可能失败): {e}")
        return None, None


# --- 3. UI 辅助函数 ---

def setup_page():
    """
    设置页面配置和标题。
    """
    st.set_page_config(layout="wide", page_title="图片白底小工具")
    st.title("🖼️ 图片背景替换为纯白色")
    st.write("使用此功能时尽量不要打开VPN，否则会很慢")
    st.write("友情链接：https://zh.bgsub.com/")
    st.write("上传一张图片，此工具将自动移除其原始背景并替换为纯白色(RGB: 255, 255, 255)。非常适合用于证件照或商品图。")
    st.write("")  # 添加一些空白间距


def clear_session_state():
    """
    清除 session_state 中存储的图片数据。
    """
    for key in ["original_image_bytes", "processed_image_pil", "processed_image_bytes", "original_file_name"]:
        if key in st.session_state:
            del st.session_state[key]
    # 强制刷新页面以清除上传组件的状态
    st.rerun()


def handle_file_upload(uploaded_file):
    """
    处理上传的文件，调用处理函数，并更新 session_state。
    """
    input_bytes = uploaded_file.getvalue()

    try:
        # 验证图片是否可读
        Image.open(io.BytesIO(input_bytes)).verify()

        # 显示加载提示
        with st.spinner('正在处理中，请稍候... (相同图片将从缓存加载)'):
            # 调用缓存的处理函数
            processed_pil, processed_bytes = process_image(input_bytes)

            if processed_pil and processed_bytes:
                # 将结果存入 session_state
                st.session_state.original_image_bytes = input_bytes
                st.session_state.processed_image_pil = processed_pil
                st.session_state.processed_image_bytes = processed_bytes
                st.session_state.original_file_name = uploaded_file.name
            else:
                # 如果处理失败，清空 session
                clear_session_state()

    except Exception as e:
        st.error(f"无法读取图片文件，请确保文件格式正确。错误: {e}")
        # 如果出错，也清空 session_state
        clear_session_state()


def display_results():
    """
    如果 session_state 中有结果，则显示原始图片和处理后的图片。
    """
    if "processed_image_bytes" in st.session_state:
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.header("原始图片")
            st.image(st.session_state.original_image_bytes, use_column_width=True)

        with col2:
            st.header("白底图片")
            st.image(st.session_state.processed_image_pil, use_column_width=True)

        # 创建下载按钮
        st.download_button(
            label="📥 下载白底图片",
            data=st.session_state.processed_image_bytes,
            file_name=f"white_bg_{st.session_state.original_file_name}.png",
            mime="image/png"
        )
    else:
        # 如果没有文件上传，也没有 session 数据，显示提示信息
        st.info("等待您上传图片...")


def display_footer():
    """
    显示页脚。
    """
    st.write("")
    st.markdown("---")
    st.markdown("待优化点：TODO")


# --- 4. 主函数 (应用入口) ---

def main():
    """
    应用的主函数。
    """
    # 1. 设置页面
    setup_page()

    # 2. 显示文件上传和清除按钮
    uploaded_file = st.file_uploader("请在这里上传您的图片...", type=['png', 'jpg', 'jpeg', 'webp'])

    if st.button("清除当前图片"):
        clear_session_state()

    # 3. 处理文件上传
    if uploaded_file is not None:
        # 检查是否是新的文件（避免在清除后重新上传相同文件时触发）
        # 通过比较文件名和大小是一种简单的方式，但为了简化，我们直接处理
        # 更好的方式是比较字节流，但 file_uploader 每次都会重新触发
        handle_file_upload(uploaded_file)

    # 4. 显示结果
    display_results()

    # 5. 显示页脚
    display_footer()


# --- 5. 运行应用 ---
if __name__ == "__main__":
    main()