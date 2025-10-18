import streamlit as st
from PIL import Image
import numpy as np
from rembg import remove
import io

# 设置页面标题和布局
st.set_page_config(page_title="电商图片白底工具", layout="centered")
st.title("🛍️ 电商图片白底工具")
st.markdown("""
**一键去除图片背景，替换为纯白色（RGB: 255,255,255）**  
适用于商品主图、展示图等电商场景
""")

# 文件上传区域
uploaded_file = st.file_uploader(
    "上传图片（支持PNG/JPG/JPEG）",
    type=["png", "jpg", "jpeg"],
    help="建议使用商品主体清晰的图片，效果更佳"
)

# 侧边栏设置（可选参数）
with st.sidebar:
    st.header("⚙️ 高级设置")
    bg_color = st.color_picker("背景颜色", "#FFFFFF")  # 默认为纯白
    border_padding = st.slider("边缘留白（像素）", 0, 100, 10, help="在商品周围添加额外留白")
    quality = st.slider("输出质量（仅JPG）", 50, 100, 90)


# 处理函数
def process_image(uploaded_file, bg_color, padding):
    # 将上传的文件转为PIL Image
    input_img = Image.open(uploaded_file)

    # 使用rembg去除背景（返回RGBA格式）
    output_img = remove(input_img)

    # 创建纯色背景
    bg = Image.new("RGB", output_img.size, bg_color)

    # 将去背景图片粘贴到纯色背景上
    bg.paste(output_img, (0, 0), output_img)

    # 添加留白（如果需要）
    if padding > 0:
        new_size = (bg.width + 2 * padding, bg.height + 2 * padding)
        new_bg = Image.new("RGB", new_size, bg_color)
        new_bg.paste(bg, (padding, padding))
        bg = new_bg

    return bg


# 如果有文件上传，则进行处理
if uploaded_file is not None:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("原图")
        st.image(uploaded_file, use_column_width=True)

    with col2:
        st.subheader("白底效果")
        with st.spinner("正在处理中，请稍候..."):
            try:
                # 处理图片
                result_img = process_image(
                    uploaded_file,
                    bg_color,
                    border_padding
                )

                # 显示结果
                st.image(result_img, use_column_width=True)

                # 转换为字节流供下载
                img_bytes = io.BytesIO()
                format = "PNG" if uploaded_file.type.endswith("png") else "JPEG"
                result_img.save(img_bytes, format=format, quality=quality)
                img_bytes.seek(0)

                # 下载按钮
                st.download_button(
                    label="下载处理后的图片",
                    data=img_bytes,
                    file_name=f"white_bg_{uploaded_file.name}",
                    mime=f"image/{format.lower()}"
                )

            except Exception as e:
                st.error(f"处理失败: {str(e)}")
                st.error("请尝试更换图片或调整参数")

# 使用说明折叠区域
with st.expander("📚 使用说明与技巧"):
    st.markdown("""
    ### 最佳实践建议：
    1. **图片选择**：商品主体清晰、与背景对比度高的图片效果最好
    2. **复杂边缘处理**：对于毛发、透明材质等复杂边缘，可能需要后期手动修图
    3. **文件格式**：
       - PNG格式保留更多细节（文件较大）
       - JPG格式适合网页使用（文件较小）
    4. **批量处理**：如需处理多张图片，请逐个上传

    ### 常见问题：
    ❓ **为什么有些边缘有残留？**  
    → 尝试增加"边缘留白"参数，或使用专业修图软件微调

    ❓ **如何处理透明背景？**  
    → 将背景颜色设置为透明色码`#00000000`（需输出PNG格式）
    """)

# 页脚
st.markdown("---")
st.caption("© 2023 电商工具箱 | 使用技术: Python + rembg + Streamlit")