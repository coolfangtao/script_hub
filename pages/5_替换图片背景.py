import streamlit as st
from rembg import remove
from PIL import Image
import io

# --- 页面配置 ---
# st.set_page_config 可以设置页面的标题、图标、布局等
# layout="wide" 让页面内容占据更宽的屏幕空间
st.set_page_config(layout="wide", page_title="图片白底小工具")

# --- 页面内容 ---
st.title("🖼️ 图片背景替换为纯白色")
st.write("上传一张图片，此工具将自动移除其原始背景并替换为纯白色(RGB: 255, 255, 255)。非常适合用于证件照或商品图。")
st.write("")  # 添加一些空白间距

# --- 主体功能 ---

# 1. 创建文件上传组件
uploaded_file = st.file_uploader("请在这里上传您的图片...", type=['png', 'jpg', 'jpeg', 'webp'])

# 2. 检查是否有文件被上传
if uploaded_file is not None:

    # 为了在内存中处理图片，我们使用io.BytesIO
    input_bytes = uploaded_file.getvalue()

    # 使用Pillow库打开图片
    try:
        input_image = Image.open(io.BytesIO(input_bytes))
    except Exception as e:
        st.error(f"无法读取图片文件，请确保文件格式正确。错误: {e}")
        st.stop()

    # 在页面上创建两列布局
    col1, col2 = st.columns(2)

    with col1:
        st.header("原始图片")
        st.image(input_image, use_column_width=True)

    # 显示一个加载提示，优化用户体验
    with st.spinner('正在处理中，请稍候...'):
        # 3. 使用 rembg 库移除背景
        # rembg 处理后会返回一个带Alpha通道的PNG格式图片（背景透明）
        output_image_no_bg = remove(input_bytes)

        # 将处理后的图片（bytes）转换回Pillow Image对象
        output_image = Image.open(io.BytesIO(output_image_no_bg))

        # 4. 创建一个纯白色的背景
        # 新建一个和处理后图片大小相同的RGB模式图片
        # "RGB" 表示红绿蓝三通道，(255, 255, 255) 是白色的颜色代码
        white_background = Image.new("RGB", output_image.size, (255, 255, 255))

        # 5. 将无背景图片粘贴到白色背景上
        # 第三个参数 output_image 作为遮罩(mask)，可以确保只粘贴图片的非透明部分
        white_background.paste(output_image, (0, 0), output_image)

        # 将最终的图片转换成可供下载的bytes
        final_image_bytes = io.BytesIO()
        white_background.save(final_image_bytes, format="PNG")
        final_image_bytes.seek(0)  # 将指针移到文件开头

    with col2:
        st.header("白底图片")
        st.image(white_background, use_column_width=True)

    # 6. 创建下载按钮
    st.download_button(
        label="📥 下载白底图片",
        data=final_image_bytes,
        file_name=f"white_bg_{uploaded_file.name}.png",  # 为下载文件生成一个新名字
        mime="image/png"
    )

else:
    # 如果没有文件上传，显示提示信息
    st.info("等待您上传图片...")

# --- 页脚 ---
st.write("")
st.markdown("---")
st.markdown("待优化点：TODO")