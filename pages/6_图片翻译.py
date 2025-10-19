# app.py

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import easyocr
from googletrans import Translator
import numpy as np
import io


# --- 1. 核心功能模块 (解耦) ---

# 模块一: 文字识别 (OCR)
# 使用 @st.cache_resource 来缓存 OCR 读取器，避免每次运行都重新加载模型，提升性能。
@st.cache_resource
def load_ocr_reader():
    """加载 EasyOCR 读取器模型"""
    # 我们只需要识别英文和简体中文，可以指定语言列表
    # 'ch_sim' 代表简体中文, 'en' 代表英文
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)  # 如果有NVIDIA GPU，可以设置为 gpu=True
    return reader


def extract_text(image_bytes, reader):
    """
    从图片中提取文字和其边界框。
    :param image_bytes: 图片的字节数据。
    :param reader: EasyOCR 的 reader 对象。
    :return: OCR 识别结果的列表。
    """
    try:
        results = reader.readtext(image_bytes)
        return results
    except Exception as e:
        st.error(f"文字识别失败: {e}")
        return []


# 模块二: 文本翻译
# 使用 @st.cache_resource 缓存 Translator 对象
@st.cache_resource
def get_translator():
    """获取 googletrans 的 Translator 实例"""
    return Translator()


def translate_text(text, translator, dest_lang='en'):
    """
    将文本翻译成目标语言。
    :param text: 需要翻译的文本字符串。
    :param translator: Translator 对象。
    :param dest_lang: 目标语言代码 (默认为 'en' - 英语)。
    :return: 翻译后的文本字符串。
    """
    try:
        translated = translator.translate(text, dest=dest_lang)
        return translated.text
    except Exception as e:
        st.warning(f"翻译失败: '{text[:20]}...' - {e}. 将使用原文。")
        return text  # 如果翻译失败，返回原文


# 模块三: 图像处理与绘制
def process_and_draw(image, ocr_results, font_path='DejaVuSans.ttf'):
    """
    在图片上覆盖原文并绘制翻译后的文本。
    :param image: PIL Image 对象。
    :param ocr_results: EasyOCR 的识别结果。
    :param font_path: 用于绘制文本的 .ttf 字体文件路径。
    :return: 处理后的 PIL Image 对象。
    """
    # 转换为 RGBA 格式以支持绘制
    img_draw = image.convert("RGBA")
    draw = ImageDraw.Draw(img_draw)
    translator = get_translator()

    for (bbox, text, prob) in ocr_results:
        # 1. 翻译文本
        translated_text = translate_text(text, translator)

        # 2. 准备覆盖原文
        # bbox 是一个包含四个点的列表 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        # 获取左上角和右下角坐标
        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))

        # 3. 绘制一个纯白色的矩形覆盖原文区域
        draw.rectangle([top_left, bottom_right], fill="white")

        # 4. 准备绘制翻译后的文本
        # 计算文本框的宽度和高度
        box_width = bottom_right[0] - top_left[0]
        box_height = bottom_right[1] - top_left[1]

        # 5. 动态调整字体大小 (一个简单的策略)
        # 尝试从一个较大的字体大小开始，逐步减小直到文本能放入框内
        font_size = box_height
        font = ImageFont.truetype(font_path, font_size)

        # 使用 textbbox 获取文本的实际渲染尺寸
        text_bbox = draw.textbbox((0, 0), translated_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]

        while text_width > box_width and font_size > 8:
            font_size -= 2
            font = ImageFont.truetype(font_path, font_size)
            text_bbox = draw.textbbox((0, 0), translated_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]

        # 6. 将翻译后的文本绘制在矩形中央
        text_x = top_left[0] + (box_width - text_width) / 2
        text_y = top_left[1] + (box_height - (text_bbox[3] - text_bbox[1])) / 2

        draw.text((text_x, text_y), translated_text, font=font, fill="black")

    return img_draw.convert("RGB")  # 转回 RGB 格式以便于显示和保存


# --- 2. Streamlit 界面 ---

st.set_page_config(layout="wide")
st.title("🖼️ 图片批量翻译工具")
st.markdown("上传一张或多张包含文字的图片，工具将自动识别其中的文字，翻译成**英语**，并生成新图片。")

# 加载模型
with st.spinner("正在加载OCR模型，首次加载可能需要几分钟..."):
    ocr_reader = load_ocr_reader()

# 文件上传器
uploaded_files = st.file_uploader(
    "选择图片文件",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if uploaded_files:
    # "开始翻译" 按钮
    if st.button("🚀 开始翻译", use_container_width=True):
        if not ocr_reader:
            st.error("OCR模型加载失败，请刷新页面重试。")
        else:
            # 为每张图片创建进度条和并排显示的列
            for uploaded_file in uploaded_files:
                st.markdown("---")
                # 读取图片数据
                image_bytes = uploaded_file.getvalue()
                original_image = Image.open(io.BytesIO(image_bytes))

                # 设置左右两列用于对比显示
                col1, col2 = st.columns(2)
                with col1:
                    st.image(original_image, caption=f"原始图片: {uploaded_file.name}", use_column_width=True)

                with col2:
                    with st.spinner(f"正在处理 {uploaded_file.name}..."):
                        # 1. 文字识别
                        ocr_results = extract_text(image_bytes, ocr_reader)

                        if not ocr_results:
                            st.warning(f"在 '{uploaded_file.name}' 中未检测到文字。")
                            st.image(original_image, caption="未作修改", use_column_width=True)
                            continue

                        # 2. 翻译并绘制
                        try:
                            font_path = 'DejaVuSans.ttf'  # 确保字体文件在此路径
                            translated_image = process_and_draw(original_image.copy(), ocr_results, font_path)
                            st.image(translated_image, caption=f"翻译后图片: {uploaded_file.name}", use_column_width=True)

                            # 提供下载按钮
                            buf = io.BytesIO()
                            translated_image.save(buf, format="PNG")
                            btn = st.download_button(
                                label="下载翻译后的图片",
                                data=buf.getvalue(),
                                file_name=f"translated_{uploaded_file.name}.png",
                                mime="image/png"
                            )
                        except FileNotFoundError:
                            st.error(f"错误：找不到字体文件 'DejaVuSans.ttf'。请确保该文件与 app.py 在同一目录下。")
                        except Exception as e:
                            st.error(f"处理图片 '{uploaded_file.name}' 时发生错误: {e}")