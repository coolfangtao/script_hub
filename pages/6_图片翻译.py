import streamlit as st
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import easyocr
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException  # <--- 新增: 导入语言检测库
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar(current_label="🌐 图片翻译") # <-- 2. 调用函数，确保每个页面都有侧边栏


# --- 1. 配置和模型加载 ---
# (这部分完全没有变化)
@st.cache_resource
def load_ocr_reader(languages=['ch_sim', 'en']):
    """
    加载EasyOCR模型。
    :param languages: 需要识别的语言列表，例如 ['ch_sim', 'en'] 表示中英文。
    :return: easyocr.Reader 实例。
    """
    st.write("正在加载OCR模型...")
    reader = easyocr.Reader(languages, gpu=False)
    st.write("OCR模型加载完成。")
    return reader


# --- 2. 核心功能函数 (解耦) ---
def ocr_and_translate_text(image_np, ocr_reader, target_language='en'):
    """
    对图像进行OCR识别，并仅翻译识别出的中文文本。
    :param image_np: NumPy格式的图像数组。
    :param ocr_reader: EasyOCR的Reader实例。
    :param target_language: 目标翻译语言。
    :return: 一个包含识别结果和翻译结果的列表。
    """
    results = ocr_reader.readtext(image_np)

    translated_results = []
    translator = GoogleTranslator(source='auto', target=target_language)

    for (bbox, text, prob) in results:
        translation = text  # <--- 修改: 默认情况下，翻译结果就是原文

        # --- 新增: 语言检测逻辑 ---
        try:
            lang = detect(text)
            # 检查检测到的语言是否是中文 (zh-cn, zh-tw 等)
            if lang.startswith('zh'):
                translation = translator.translate(text)
        except LangDetectException:
            # 如果文本太短或无法识别，就不进行翻译，直接使用原文
            print(f"无法检测语言: '{text}', 将保留原文。")
        except Exception as e:
            # 处理其他可能的翻译错误
            print(f"翻译失败: '{text}'. 错误: {e}")
            translation = text  # 翻译失败则保留原文
        # --- 语言检测逻辑结束 ---

        translated_results.append({
            'box': bbox,
            'text': text,
            'translation': translation
        })

    return translated_results


def remove_original_text(image_np, ocr_results):
    """
    使用OpenCV的图像修复功能，从图片上移除原始文字。
    (这部分完全没有变化)
    """
    mask = np.zeros(image_np.shape[:2], dtype=np.uint8)

    for result in ocr_results:
        box_points = np.array(result['box'], dtype=np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [box_points], (255))

    inpainted_image = cv2.inpaint(image_np, mask, 3, cv2.INPAINT_TELEA)

    return inpainted_image


def draw_translated_text(image_np, translated_results, font_path='Arial.ttf'):
    """
    在图片上绘制翻译后的文本。
    (这部分完全没有变化)
    """
    image_pil = Image.fromarray(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)

    for result in translated_results:
        # 如果原文和译文相同，就不需要重绘了，可以跳过以保留原文的清晰度
        # 这是一个小优化，你可以选择性保留或删除
        if result['text'] == result['translation']:
            continue

        top_left = tuple(map(int, result['box'][0]))
        translation = result['translation']

        if not translation:
            continue

        box_height = result['box'][2][1] - result['box'][0][1]
        font_size = max(15, int(box_height * 0.7))

        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            st.error(f"字体文件未找到: {font_path}。请确保字体文件和脚本在同一目录下。")
            font = ImageFont.load_default()

        draw.text(top_left, translation, font=font, fill=(0, 0, 0))

    return image_pil


# --- 3. Streamlit 界面 ---
# (这部分完全没有变化)
def main():
    st.set_page_config(page_title="图片翻译工具", layout="wide")
    st.title("🖼️ 图片中英翻译工具 (仅翻译中文，效果不好，待改进)")
    st.markdown("上传一张或多张包含文字的图片，工具将自动识别**中文**并将其翻译成英文，英文部分将保持不变。")

    ocr_reader = load_ocr_reader(['ch_sim', 'en'])

    uploaded_files = st.file_uploader(
        "选择图片文件",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("开始翻译", use_container_width=True, type="primary"):

            for uploaded_file in uploaded_files:
                with st.spinner(f"正在处理图片: {uploaded_file.name}..."):

                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    original_image_cv = cv2.imdecode(file_bytes, 1)

                    translation_results = ocr_and_translate_text(original_image_cv, ocr_reader)

                    if not translation_results:
                        st.warning(f"在图片 '{uploaded_file.name}' 中未检测到任何文字。")
                        continue

                    inpainted_image_cv = remove_original_text(original_image_cv, translation_results)

                    final_image_pil = draw_translated_text(inpainted_image_cv, translation_results,
                                                           font_path='../assets/Arial.ttf')

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