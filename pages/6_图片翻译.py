import streamlit as st
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import easyocr
from deep_translator import GoogleTranslator
import io


# --- 1. 配置和模型加载 ---
# 将模型加载放在函数外部，利用Streamlit的缓存机制，避免每次点击都重新加载模型。
@st.cache_resource
def load_ocr_reader(languages=['ch_sim', 'en']):
    """
    加载EasyOCR模型。
    :param languages: 需要识别的语言列表，例如 ['ch_sim', 'en'] 表示中英文。
    :return: easyocr.Reader 实例。
    """
    st.write("正在加载OCR模型...")
    reader = easyocr.Reader(languages, gpu=False)  # 如果有GPU, 可以设置为 gpu=True
    st.write("OCR模型加载完成。")
    return reader


# --- 2. 核心功能函数 (解耦) ---

def ocr_and_translate_text(image_np, ocr_reader, target_language='en'):
    """
    对图像进行OCR识别，并翻译识别出的文本。
    :param image_np: NumPy格式的图像数组。
    :param ocr_reader: EasyOCR的Reader实例。
    :param target_language: 目标翻译语言。
    :return: 一个包含识别结果和翻译结果的列表。
             格式: [{'box': [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], 'text': '原文', 'translation': 'Translated Text'}, ...]
    """
    results = ocr_reader.readtext(image_np)

    translated_results = []
    translator = GoogleTranslator(source='auto', target=target_language)

    for (bbox, text, prob) in results:
        # 尝试翻译，如果文本太短或无意义，可能翻译失败
        try:
            translation = translator.translate(text)
        except Exception as e:
            translation = text  # 翻译失败则保留原文
            print(f"翻译失败: '{text}'. 错误: {e}")

        translated_results.append({
            'box': bbox,
            'text': text,
            'translation': translation
        })

    return translated_results


def remove_original_text(image_np, ocr_results):
    """
    使用OpenCV的图像修复功能，从图片上移除原始文字。
    :param image_np: NumPy格式的原始图像数组。
    :param ocr_results: OCR识别结果列表。
    :return: 移除了文字的NumPy格式图像数组。
    """
    mask = np.zeros(image_np.shape[:2], dtype=np.uint8)

    for result in ocr_results:
        # easyocr返回的bbox是一个包含4个点的列表
        # 我们需要将其转换为OpenCV需要的多边形格式
        box_points = np.array(result['box'], dtype=np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [box_points], (255))

    # 使用TELEA算法进行图像修复，效果更自然
    inpainted_image = cv2.inpaint(image_np, mask, 3, cv2.INPAINT_TELEA)

    return inpainted_image


def draw_translated_text(image_np, translated_results, font_path='arial.ttf'):
    """
    在图片上绘制翻译后的文本。
    :param image_np: NumPy格式的图像数组 (通常是已经移除了原文的)。
    :param translated_results: 包含翻译文本和位置信息的结果列表。
    :param font_path: 用于绘制文本的字体文件路径。
    :return: 绘制了翻译文本的PIL Image对象。
    """
    # 将OpenCV图像 (BGR) 转换为Pillow图像 (RGB)
    image_pil = Image.fromarray(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)

    for result in translated_results:
        top_left = tuple(map(int, result['box'][0]))
        translation = result['translation']

        if not translation:
            continue

        # 简单的字体大小选择，可以根据框的高度进行优化
        # 这是一个可以后期改进的点
        box_height = result['box'][2][1] - result['box'][0][1]
        font_size = max(15, int(box_height * 0.7))  # 字体大小约为框高的70%

        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            st.error(f"字体文件未找到: {font_path}。请确保字体文件和脚本在同一目录下。")
            font = ImageFont.load_default()  # 使用默认字体

        draw.text(top_left, translation, font=font, fill=(0, 0, 0))  # 默认为黑色字体

    return image_pil


# --- 3. Streamlit 界面 ---

def main():
    st.set_page_config(page_title="图片翻译工具", layout="wide")
    st.title("🖼️ 图片批量翻译工具")
    st.markdown("上传一张或多张包含文字的图片，工具将自动识别并将其翻译成英文。")

    # 加载模型
    ocr_reader = load_ocr_reader(['ch_sim', 'en'])  # 支持中英文识别

    # 文件上传
    uploaded_files = st.file_uploader(
        "选择图片文件",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )

    if uploaded_files:
        # 创建翻译按钮
        if st.button("开始翻译", use_container_width=True, type="primary"):

            # 遍历所有上传的文件
            for uploaded_file in uploaded_files:
                # 显示加载状态
                with st.spinner(f"正在处理图片: {uploaded_file.name}..."):

                    # 将上传的文件转换为OpenCV可以处理的格式
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    original_image_cv = cv2.imdecode(file_bytes, 1)

                    # --- 调用核心处理流程 ---
                    # 1. OCR识别与文本翻译
                    translation_results = ocr_and_translate_text(original_image_cv, ocr_reader)

                    if not translation_results:
                        st.warning(f"在图片 '{uploaded_file.name}' 中未检测到任何文字。")
                        continue

                    # 2. 从原图中移除文字
                    inpainted_image_cv = remove_original_text(original_image_cv, translation_results)

                    # 3. 将翻译文本绘制到新图上
                    final_image_pil = draw_translated_text(inpainted_image_cv, translation_results,
                                                           font_path='arial.ttf')

                    # --- 显示结果 ---
                    st.subheader(f"处理结果: {uploaded_file.name}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(original_image_cv, caption="原始图片", channels="BGR", use_column_width=True)
                    with col2:
                        st.image(final_image_pil, caption="翻译后图片", use_column_width=True)
                    st.divider()

        else:
            st.info("请点击 '开始翻译' 按钮处理上传的图片。")


if __name__ == '__main__':
    main()