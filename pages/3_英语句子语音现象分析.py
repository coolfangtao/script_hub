# pages/phonetics_analyzer.py

import streamlit as st
import asyncio
import edge_tts
import os
import google.generativeai as genai
from typing import Optional
from shared.sidebar import create_common_sidebar
from shared.config import GlobalConfig


# --- 1. 页面专属配置 ---
class PhoneticsPageConfig(GlobalConfig):
    """存储此页面专属的配置，继承全局配置。"""

    def __init__(self):
        super().__init__()
        self.PAGE_TITLE = "英语语音现象分析器"
        self.PAGE_ICON = "🗣️"
        self.OUTPUT_DIR = "tts_audio"
        self.DEFAULT_VOICE = "en-US-JennyNeural"
        self.DEFAULT_SENTENCE = "Let's get a cup of coffee."
        self.PLACEHOLDER_TEXT = "例如: What are you going to do?"
        self.DEFAULT_MODEL = "gemini-2.5-flash-lite"
        self.PROMPT_TEMPLATE = """
        请作为一名专业的英语语音教师，分析以下句子的语音现象。

        句子: "{text}"

        你的任务是：
        1.  **标注语音现象**：识别出句子中所有常见的连读、略读、插读、失去爆破、不完全爆破等现象。
        2.  **提供音标**：为整个句子提供国际音标 (IPA)。
        3.  **格式化输出**：
            - 使用 Markdown 格式。
            - 用颜色和符号来高亮显示语音现象。例如：
              - 连读 (Liaison): 使用 `‿` 连接单词，例如 `an‿apple`。
              - 略读 (Elision): 在被省略的音素位置使用删除线 `~`，例如 `las~t night`。
              - 插读 (Intrusion): 在插入音素的位置使用 `+` 号，例如 `go+w away`。
            - 在句子下方，用列表形式逐一解释每个标记的具体语音现象和规则。

        请严格按照以上要求，生成一个清晰、准确的分析结果。
        """


# --- 2. 核心业务逻辑 ---
class PhoneticsAnalyzer:
    """封装核心的语音生成和文本分析功能。"""

    def __init__(self, config: PhoneticsPageConfig):
        self.config = config
        if not os.path.exists(self.config.OUTPUT_DIR):
            os.makedirs(self.config.OUTPUT_DIR)

    async def generate_tts(self, text: str) -> Optional[str]:
        """使用 edge-tts 生成语音文件。"""
        try:
            sanitized_filename = "".join(c for c in text if c.isalnum() or c in (' ', '.', '_')).rstrip()[:50]
            output_file = os.path.join(self.config.OUTPUT_DIR, f"{sanitized_filename}.mp3")

            if os.path.exists(output_file):
                return output_file

            communicate = edge_tts.Communicate(text, self.config.DEFAULT_VOICE)
            await communicate.save(output_file)
            return output_file
        except Exception as e:
            st.error(f"语音生成失败: {e}", icon="😢")
            return None

    def analyze_with_gemini(self, text: str, model_name: str) -> str:
        """使用指定的 Gemini API 模型分析文本的语音现象。"""
        if not text:
            return ""
        try:
            model = genai.GenerativeModel(model_name)
            prompt = self.config.PROMPT_TEMPLATE.format(text=text)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Gemini API 调用失败: {e}", icon="🔥")
            return "分析时遇到错误，请检查您的 API 密钥是否有效或网络连接是否正常。"

    def process_and_store_results(self, sentence: str, selected_model: str):
        """协调分析和TTS过程，并将结果存储在 session_state 中。"""
        if not sentence:
            st.warning("请输入一个句子进行分析。", icon="✍️")
            return

        with st.spinner("🔊 正在生成语音，请稍候..."):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            audio_file_path = loop.run_until_complete(self.generate_tts(sentence))
            st.session_state.audio_path = audio_file_path

        with st.spinner("🤖 正在分析中，请稍候..."):
            analysis_result = self.analyze_with_gemini(sentence, selected_model)
            st.session_state.analysis_result = analysis_result


# --- 3. 页面UI布局 ---
class PhoneticsPageUI:
    """封装页面的所有UI渲染逻辑。"""

    def __init__(self, config: PhoneticsPageConfig):
        self.config = config

    def setup_page(self):
        st.set_page_config(
            page_title=self.config.PAGE_TITLE,
            page_icon=self.config.PAGE_ICON,
            layout="wide"
        )

    def display_header(self):
        st.title(f"{self.config.PAGE_ICON} {self.config.PAGE_TITLE}")
        st.markdown("输入一个英语句子，即可生成标准发音，并由AI分析其中包含的连读、略读等语音现象。\n"
                    "**部分符号说明：**\n"
                    "- 连读 (Liaison): 使用 `‿` 连接单词\n"
                    "- 略读 (Elision): 在被省略的音素位置使用删除线 `~`\n"
                    "- 插读 (Intrusion): 在插入音素的位置使用 `+` 号\n"
                    "- 停顿: `|` 符号表示自然的语调停顿。")

    def inject_custom_css(self):
        st.markdown("""
            <style>
            .phonetic-analysis { background-color: #f0f2f6; border-left: 6px solid #1E90FF; padding: 15px; border-radius: 5px; font-size: 1.1em; line-height: 1.6; color: #212529; }
            .phonetic-analysis strong { color: #005A9C; }
            footer { visibility: hidden; }
            </style>
        """, unsafe_allow_html=True)

    def display_api_key_input(self):
        """在页面主区域显示API Key输入框（仅在Cloud模式下）。"""
        if self.config.RUN_MODE == "cloud":
            # 仅当没有在 session_state 中找到 key 时，默认展开
            is_expanded = not st.session_state.get("gemini_api_key")
            with st.expander("🔑 配置 Gemini API Key", expanded=is_expanded):
                st.info("检测到Cloud运行模式，请输入您的API密钥以使用本页面功能。")
                api_key = st.text_input(
                    "Gemini API Key",
                    type="password",
                    # 使用新的、唯一的 widget key
                    key="gemini_api_key_input_main",
                    # value从session_state获取，实现持久化
                    value=st.session_state.get("gemini_api_key", "")
                )
                # 用户输入时，实时更新到 session_state
                if api_key:
                    st.session_state.gemini_api_key = api_key

                # 如果 session_state 中已有 key，则显示成功信息
                if st.session_state.get("gemini_api_key"):
                    st.success("API Key 已配置。您可以折叠此区域。")

    def display_input_form(self):
        selected_model = st.selectbox(
            "**请选择一个分析模型：**",
            options=self.config.GEMINI_MODEL_OPTIONS,
            index=self.config.GEMINI_MODEL_OPTIONS.index(st.session_state.selected_model)
        )
        st.session_state.selected_model = selected_model

        with st.form("input_form"):
            sentence = st.text_input(
                "**在这里输入英语句子或短语：**",
                value=st.session_state.sentence_input,
                placeholder=self.config.PLACEHOLDER_TEXT
            )
            submitted = st.form_submit_button("分析并生成语音", type="primary")

        if submitted:
            st.session_state.sentence_input = sentence

        return st.session_state.sentence_input, submitted

    def display_results(self):
        if not st.session_state.get('analysis_result') and not st.session_state.get('audio_path'):
            return

        st.divider()
        st.subheader("标准发音")
        audio_path = st.session_state.get('audio_path')
        if audio_path and os.path.exists(audio_path):
            st.success("语音已生成！")
            st.audio(audio_path, format="audio/mp3")
            with open(audio_path, "rb") as file:
                st.download_button(
                    label="📥 下载语音 (MP3)",
                    data=file,
                    file_name=os.path.basename(audio_path),
                    mime="audio/mp3"
                )
        elif st.session_state.sentence_input:
            st.error("语音文件生成失败或缓存已失效。")

        st.divider()
        st.subheader("语音现象分析")
        analysis_result = st.session_state.get('analysis_result')
        if analysis_result:
            st.markdown(f'<div class="phonetic-analysis">{analysis_result}</div>', unsafe_allow_html=True)
        elif st.session_state.sentence_input:
            st.error("语音分析失败，请检查后台错误信息或API Key。")


# --- 4. 主程序入口 ---
def main():
    config = PhoneticsPageConfig()
    ui = PhoneticsPageUI(config)
    analyzer = PhoneticsAnalyzer(config)

    ui.setup_page()
    ui.inject_custom_css()
    create_common_sidebar()
    ui.display_header()

    # 初始化 session_state
    if 'sentence_input' not in st.session_state:
        st.session_state.sentence_input = config.DEFAULT_SENTENCE
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = ""
    if 'audio_path' not in st.session_state:
        st.session_state.audio_path = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = config.DEFAULT_MODEL
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = None

    # 根据运行模式获取API密钥
    if config.RUN_MODE == 'local':
        try:
            st.session_state.gemini_api_key = st.secrets["gemini_api_key"]
        except (KeyError, FileNotFoundError):
            st.error("本地模式运行失败：未在 .streamlit/secrets.toml 中找到 'gemini_api_key'。")
            st.stop()  # 停止执行
    else:  # cloud 模式
        ui.display_api_key_input()  # 在主页面渲染输入框

    # 检查API密钥是否存在，如果不存在则阻止后续渲染
    if not st.session_state.get("gemini_api_key"):
        st.warning("请输入您的Gemini API Key以启用分析功能。")
        st.stop()  # 停止执行

    # 配置Gemini API
    try:
        genai.configure(api_key=st.session_state.gemini_api_key)
    except Exception as e:
        st.error(f"API 密钥配置失败，请检查您的密钥是否正确。错误: {e}", icon="🚨")
        st.stop()

    # 显示输入表单并获取用户操作
    sentence, submitted = ui.display_input_form()

    if submitted:
        st.session_state.audio_path = None
        st.session_state.analysis_result = ""
        analyzer.process_and_store_results(sentence, st.session_state.selected_model)

    ui.display_results()


if __name__ == "__main__":
    main()