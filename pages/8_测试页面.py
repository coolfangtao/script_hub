import streamlit as st
from PIL import Image
import io
import google.generativeai as genai
from shared.config import GlobalConfig
import time


# --- 1. 页面特定配置类 ---
class PageConfig(GlobalConfig):
    """
    继承自 GlobalConfig，添加当前页面特定的配置。
    """

    def __init__(self):
        super().__init__()
        # 页面标题和图标
        self.PAGE_TITLE = "AI智能去文字 (Gemini)"
        self.PAGE_ICON = "🎨"

        # 默认的精细化提示词
        # 针对电商场景去除中文特别优化，强调了“去除”和“保留背景”
        self.DEFAULT_REMOVE_TEXT_PROMPT = """
You are an expert professional image editor for e-commerce.
Your ONLY task is to remove ALL Chinese text (Hanzi) from this product image.

STRICT INSTRUCTIONS:
1. DETECT: Identify all regions containing Chinese characters.
2. REMOVE & INPAINT: Completely erase the Chinese text. Seamlessly fill (inpaint) the erased areas by extending the surrounding background texture, color, and lighting. The result must look 100% natural, as if the text never existed.
3. PRESERVE: Do NOT alter, distort, or remove any English text, numbers, logos, brand names, or the main product itself. Keep the original image resolution and quality.
4. OUTPUT: Return ONLY the final processed image.
"""


# --- 2. 核心逻辑类 (API调用) ---
class GeminiImageEditor:
    """
    负责与 Gemini API 交互的逻辑类。
    """

    def __init__(self, api_key):
        try:
            genai.configure(api_key=api_key)
            self.is_configured = True
        except Exception as e:
            st.error(f"Gemini API 配置失败: {e}")
            self.is_configured = False

    def remove_text(self, image: Image.Image, prompt: str, model_name: str):
        """
        调用 Gemini API 去除图片文字。
        注意：这依赖于所选模型是否支持返回图像。
        """
        if not self.is_configured:
            return None, "API未配置"

        model = genai.GenerativeModel(model_name)

        try:
            with st.spinner(f"正在请求 {model_name} 进行AI修图，请耐心等待..."):
                # 记录开始时间
                start_time = time.time()

                # 发送请求：提示词 + 图片
                # 注意：不同的Gemini SDK版本对图像输入的支持方式可能略有差异，
                # 这里使用最通用的列表方式 [text_prompt, image_object]
                response = model.generate_content([prompt, image])

                end_time = time.time()
                elapsed_time = end_time - start_time

            # 处理响应
            # 检查响应中是否包含图像部分
            # 注意：标准Gemini API如果返回图片，通常在 parts 中会有 inline_data 或类似结构，
            # 或者整个 response 结构需要特定解析。
            # 这里尝试一种通用的解析方式，如果失败则返回调试信息。

            try:
                # 尝试直接获取返回的第一个图像部分（如果模型支持直接返回图像）
                # 这部分代码可能需要根据实际Gemini版本返回的数据结构进行微调
                # 如果是纯文本模型，这里会报错或返回None
                if response.parts and hasattr(response.parts[0], 'inline_data'):
                    img_data = response.parts[0].inline_data.data
                    processed_image = Image.open(io.BytesIO(img_data))
                    return processed_image, f"处理成功 (耗时: {elapsed_time:.2f}s)"

                # 如果通过标准属性没拿到，尝试检查是否有文本内容的兜底（有时模型会拒绝并返回文本原因）
                if response.text:
                    return None, f"模型未返回图像，而是返回了文本信息 (可能模型不支持此功能或拒绝了请求):\n{response.text}"

            except Exception as e_parse:
                # 最后的尝试：有时response本身可以直接被视为某种多媒体对象，视具体SDK版本而定
                # 如果上述失败，打印原始 response 以便调试
                print(f"Debug Response: {response}")
                return None, f"解析模型返回结果失败。请检查所选模型是否支持图像输出。\n错误信息: {e_parse}"

            return None, "未知错误：模型响应中未找到图像数据。"

        except Exception as e:
            return None, f"API调用过程出错: {e}"


# --- 3. 用户界面类 ---
class PageUI:
    """
    负责页面渲染和交互。
    """

    def __init__(self, config: PageConfig):
        self.config = config
        # 从 secrets 中安全读取 API Key
        api_key = st.secrets.get(self.config.GEMINI_API_KEY, "")
        if not api_key:
            st.warning("⚠️ 未在 secrets 中找到 GEMINI_API_KEY，请检查您的 .streamlit/secrets.toml 配置。")
        self.editor = GeminiImageEditor(api_key)

    def render_sidebar(self):
        with st.sidebar:
            st.header("🛠️ 修图设置")

            # 模型选择器
            selected_model = st.selectbox(
                "选择 Gemini 模型",
                options=self.config.GEMINI_MODEL_OPTIONS,
                index=0,  # 默认选择第一个
                help="不同模型在速度和图像处理能力上可能有所不同。建议尝试不同模型以获得最佳效果。"
            )

            st.markdown("---")
            st.markdown("### 💡 使用小贴士")
            st.info(
                "1. 图片越清晰，文字识别越准确。\n"
                "2. 如果效果不佳，尝试微调右侧的提示词，例如明确指出要去除的文字内容。\n"
                "3. 这是一个实验性功能，依赖于Gemini模型的生成能力。"
            )
            return selected_model

    def render_main_area(self, selected_model):
        st.title(f"{self.config.PAGE_ICON} {self.config.PAGE_TITLE}")
        st.caption("上传带有中文的产品图，利用 AI 自动去除文字并修复背景，助力电商出海。")

        # 布局：左侧上传和设置，右侧显示结果
        col1, col2 = st.columns([1, 1.2])

        with col1:
            st.subheader("1️⃣ 上传原始图片")
            uploaded_file = st.file_uploader("支持 JPG, PNG 格式", type=["png", "jpg", "jpeg"])

            if uploaded_file:
                # 显示原图
                original_image = Image.open(uploaded_file)
                st.image(original_image, caption="原始图片", use_column_width=True)

                st.subheader("2️⃣ 提示词设置 (Prompt)")
                prompt_text = st.text_area(
                    "指导 AI 修图的指令 (支持自定义修改)",
                    value=self.config.DEFAULT_REMOVE_TEXT_PROMPT,
                    height=250,
                    help="用英语描述通常能获得更好的遵循效果。"
                )

                # 执行按钮
                start_btn = st.button("🚀 开始 AI 修图", type="primary", use_container_width=True)

        with col2:
            st.subheader("3️⃣ 处理结果")
            # 定义一个空容器用于稍后放置结果
            result_container = st.empty()

            if uploaded_file and start_btn:
                if not self.editor.is_configured:
                    result_container.error("请先配置有效的 Gemini API Key。")
                else:
                    # 调用API
                    processed_img, msg = self.editor.remove_text(original_image, prompt_text, selected_model)

                    if processed_img:
                        # 显示成功结果
                        result_container.image(processed_img, caption=f"🎉 处理完成! {msg}", use_column_width=True)

                        # 提供下载按钮
                        # 将 PIL Image 转为 Bytes 供下载
                        buf = io.BytesIO()
                        processed_img.save(buf, format="PNG")
                        byte_im = buf.getvalue()

                        st.download_button(
                            label="⬇️ 下载处理后的图片 (PNG)",
                            data=byte_im,
                            file_name="removed_text_image.png",
                            mime="image/png",
                            type="primary"
                        )
                    else:
                        # 显示错误信息
                        result_container.error(f"处理失败: {msg}")
            elif not uploaded_file:
                result_container.info("👈 请先在左侧上传图片。")
            else:
                result_container.info("等待开始... 点击左侧的【🚀 开始 AI 修图】按钮。")

    def render(self):
        st.set_page_config(page_title=self.config.PAGE_TITLE, page_icon=self.config.PAGE_ICON, layout="wide")
        selected_model = self.render_sidebar()
        self.render_main_area(selected_model)


# --- 4. 主函数 ---
def main():
    config = PageConfig()
    ui = PageUI(config)
    ui.render()


if __name__ == "__main__":
    main()