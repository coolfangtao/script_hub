import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
import io


# --- Function Definitions ---

def extract_data_from_cropped_image(image: Image.Image):
    """
    从一个已经裁剪好的表格图片中提取元素分析数据。

    *** 新版本：使用白名单，只识别字母、数字和必要的符号 ***

    Args:
        image: 包含数据表格的 PIL Image 对象。

    Returns:
        一个包含提取数据的字典 (例如: {'C': 13.35, ...})
        如果无法提取数据，则返回一个空字典。
    """
    # --- 1. 定义白名单 ---
    # 我们需要英文字母 (a-z, A-Z) 来识别元素符号和线 (K, L)。
    # 我们需要数字 (0-9) 和小数点 (.) 来识别数值。
    # 我们需要 ± 符号，因为正则表达式用它来定位数据。
    whitelist = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.±'

    # --- 2. 创建新的 Tesseract 配置 ---
    # -c tessedit_char_whitelist=...  <-- 这就是应用白名单的命令
    custom_config = f'--oem 3 --psm 6 -c tessedit_char_whitelist={whitelist}'

    try:
        # --- 3. 修改语言设置 ---
        # 因为白名单里没有中文字符，所以我们不再需要 chi_sim 语言包。
        # 只使用 'eng' 会更高效。
        text = pytesseract.image_to_string(image, lang='eng', config=custom_config)
    except pytesseract.TesseractNotFoundError:
        st.error("错误：Tesseract OCR 未安装或未在系统的 PATH 中。请按照说明安装 Tesseract。")
        st.stop()

    print(text)
    # --- 解析提取到的文本 (这部分无需改动) ---
    data_dict = {}
    regex = r"^\s*([A-Za-z]{1,2})\s+.+?\s+([\d\.]+)\s*±.+"

    lines = text.split('\n')
    for line in lines:
        match = re.match(regex, line.strip())
        if match:
            element = match.group(1)
            try:
                mass_percent = float(match.group(2))
                data_dict[element] = mass_percent
            except (ValueError, IndexError):
                continue

    return data_dict


# --- Streamlit App UI ---

st.set_page_config(page_title="表格数据提取器", layout="wide")

st.title("裁剪表格图片数据提取工具")
st.write("请上传一张 **仅包含数据表格** 的截图，工具将自动提取数据。")

# 上传文件
uploaded_file = st.file_uploader("选择一张裁剪好的表格图片...", type=["png", "jpg", "jpeg", "bmp"])

if uploaded_file is not None:
    # 将上传的文件转换为Pillow Image对象
    image = Image.open(uploaded_file)

    # 在页面左侧显示上传的图片
    st.image(image, caption="已上传的表格截图", width=300)

    # 数据提取和展示
    with st.spinner("正在识别和提取数据..."):
        extracted_data = extract_data_from_cropped_image(image)

    st.write("---")

    if extracted_data:
        st.success("🎉 数据提取成功！")

        # 将结果并排展示
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("1. Python 字典格式")
            st.json(extracted_data)

        with col2:
            st.subheader("2. 表格形式展示")
            # 将字典转换为Pandas DataFrame以便更好地展示
            df = pd.DataFrame(list(extracted_data.items()), columns=["元素 (Element)", "质量% (Mass %)"])
            # 设置索引从1开始
            df.index = df.index + 1
            st.dataframe(df.style.format({'质量% (Mass %)': '{:.2f}'}))

    else:
        st.error("提取失败。未能在图片中找到有效的数据行。请确保上传的图片是清晰的、仅包含表格的截图。")

# 添加使用说明和注意事项
st.info(
    """
    **使用提示:**
    - 这个版本专门为 **已经裁剪好、只剩下表格** 的图片设计。
    - 请确保图片清晰、没有严重的倾斜或失真。
    - 如果识别失败，可以尝试调整图片的对比度或亮度后重新上传。
    """
)