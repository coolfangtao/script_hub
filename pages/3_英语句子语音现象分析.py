# pages/phonetics_analyzer.py

import streamlit as st
import asyncio
import edge_tts
import os
import google.generativeai as genai
from typing import Optional
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数

# --- 页面和侧边栏配置 ---
# 配置页面信息
st.set_page_config(page_title="英语语音现象分析器", page_icon="🗣️", layout="wide")
# 调用函数创建共享的侧边栏
create_common_sidebar()

# --- 常量和样式定义 ---
# 定义语音输出的目录
OUTPUT_DIR = "tts_audio"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 定义可选的 AI 模型列表
MODEL_OPTIONS = [
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash-tts",
    "gemini-2.5-flash",
    "gemini-robotics-er-1.5-preview",
    "gemma-3-12b",
    "gemma-3-1b",
    "gemma-3-27b",
    "gemma-3-2b",
    "gemma-3-4b",
    "learnim-2.0-flash-experimental",
    "imagen-3.0-generate",
    "veo-2.0-generate-001",
    "gemini-2.0-flash-live",
    "gemini-2.5-flash-live",
    "gemini-2.5-flash-native-audio-dialog"
]

# 注入自定义CSS样式
st.markdown("""
    <style>
    .phonetic-analysis {
        background-color: #f0f2f6;
        border-left: 6px solid #1E90FF;
        padding: 15px;
        border-radius: 5px;
        font-size: 1.1em;
        line-height: 1.6;
        color: #212529; /* <--  已修复：为这个框设置固定的深色文字 */
    }
    .phonetic-analysis strong {
        color: #005A9C;
    }
    /* 隐藏Streamlit页脚 */
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# --- 核心功能函数 ---

async def generate_tts(text: str, voice: str = "en-US-JennyNeural") -> Optional[str]:
    """
    使用 edge-tts 生成语音文件.
    :param text: 要转换的文本.
    :param voice: 使用的语音模型.
    :return: 成功则返回音频文件路径, 否则返回 None.
    """
    try:
        sanitized_filename = "".join(c for c in text if c.isalnum() or c in (' ', '.', '_')).rstrip()
        output_file = os.path.join(OUTPUT_DIR, f"{sanitized_filename}.mp3")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        return output_file
    except Exception as e:
        st.error(f"语音生成失败: {e}", icon="😢")
        return None


def analyze_phonetics_with_gemini(text: str, model_name: str) -> str:
    """
    使用指定的 Gemini API 模型分析文本的语音现象.
    :param text: 要分析的英语句子.
    :param model_name: 要使用的 Gemini 模型名称.
    :return: 包含分析结果的 Markdown 格式字符串.
    """
    if not text:
        return ""

    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""
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
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API 调用失败: {e}", icon="🔥")
        return "分析时遇到错误，请检查您的 API 密钥是否有效或网络连接是否正常。"


def process_and_display_results(sentence: str, selected_model: str):
    """
    协调分析和TTS过程，并在页面上展示结果。
    此版本先生成语音，再在下方生成分析。
    :param sentence: 用户输入的句子.
    :param selected_model: 用户选择的AI模型.
    """
    if not sentence:
        st.warning("请输入一个句子进行分析。", icon="✍️")
        return

    # --- 1. 文本转语音 (TTS) ---
    st.subheader("标准发音")
    with st.spinner("🔊 正在生成语音，请稍候..."):
        # 使用更稳健的方式在 Streamlit 中运行异步代码
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        audio_file_path = loop.run_until_complete(generate_tts(sentence))

        if audio_file_path and os.path.exists(audio_file_path):
            st.success("语音生成成功！")
            st.audio(audio_file_path, format="audio/mp3")
            with open(audio_file_path, "rb") as file:
                st.download_button(
                    label="📥 下载语音 (MP3)",
                    data=file,
                    file_name=os.path.basename(audio_file_path),
                    mime="audio/mp3"
                )
        else:
            # generate_tts 函数内部已经显示了具体的错误信息，所以这里不需要再显示
            pass

    st.divider()  # 添加一条分割线

    # --- 2. 语音现象分析 ---
    st.subheader("语音现象分析")
    with st.spinner("🤖 正在分析中，请稍候..."):
        analysis_result = analyze_phonetics_with_gemini(sentence, selected_model)
        st.markdown(f'<div class="phonetic-analysis">{analysis_result}</div>', unsafe_allow_html=True)


# --- 主程序入口 ---

def main():
    """主函数, 运行 Streamlit 应用."""
    st.title("🗣️ 英语句子语音现象分析器")
    st.markdown("输入一个英语句子，即可生成标准发音，并由AI分析其中包含的连读、略读等语音现象。\n"
                "**部分符号说明：**\n"
                "- 连读 (Liaison): 使用 `‿` 连接单词，例如 an‿apple\n"
                "- 略读 (Elision): 在被省略的音素位置使用删除线 `~`，例如 las~t night\n"
                "- 插读 (Intrusion): 在插入音素的位置使用 `+` 号，例如 go+w away\n"
                "- 停顿: `|` 符号表示自然的语调停顿。")

    # 模型选择框
    selected_model = st.selectbox(
        "**请选择一个分析模型：**",
        options=MODEL_OPTIONS,
        index=MODEL_OPTIONS.index("gemini-2.0-flash")  # 默认选中 'gemini-2.0-flash'
    )

    with st.form("input_form"):
        sentence = st.text_input(
            "**在这里输入英语句子或短语：**",
            value="Let's get a cup of coffee.",
            placeholder="例如: What are you going to do?"
        )
        submitted = st.form_submit_button("分析并生成语音", type="primary")

    if submitted:
        # 从secrets读取API密钥
        try:
            api_key = st.secrets["API_KEY"]
            genai.configure(api_key=api_key)
        except (KeyError, FileNotFoundError):
            st.error("操作失败：未在 Streamlit secrets 中找到名为 'API_KEY' 的 Gemini API 密钥。", icon="🚫")
            return
        except Exception as e:
            st.error(f"API 密钥配置失败，请检查您的密钥是否正确。错误: {e}", icon="🚨")
            return

        # 开始处理并展示结果
        process_and_display_results(sentence, selected_model)


if __name__ == "__main__":
    main()

