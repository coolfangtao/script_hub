# pages/phonetics_analyzer.py

import streamlit as st
import asyncio
import edge_tts
import os
import google.generativeai as genai
from typing import Optional

# --- 配置部分 ---

# 定义语音输出的目录
OUTPUT_DIR = "tts_audio"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# --- 核心功能函数 (解耦) ---

async def generate_tts(text: str, voice: str = "en-US-JennyNeural") -> Optional[str]:
    """
    使用 edge-tts 生成语音文件.
    :param text: 要转换的文本.
    :param voice: 使用的语音模型.
    :return: 成功则返回音频文件路径, 否则返回 None.
    """
    try:
        # 使用文本作为文件名，并进行清理以避免路径问题
        sanitized_filename = "".join(c for c in text if c.isalnum() or c in (' ', '.', '_')).rstrip()
        output_file = os.path.join(OUTPUT_DIR, f"{sanitized_filename}.mp3")

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        return output_file
    except Exception as e:
        st.error(f"语音生成失败: {e}", icon="😢")
        return None


def analyze_phonetics_with_gemini(text: str) -> str:
    """
    使用 Gemini API 分析文本的语音现象.
    :param text: 要分析的英语句子.
    :return: 包含分析结果的 Markdown 格式字符串.
    """
    if not text:
        return ""

    # 此时 genai 模块应该已经被配置好了
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = f"""
        请作为一名专业的英语语音教师，分析以下句子的语音现象。

        句子: "{text}"

        你的任务是：
        1.  **标注语音现象**：识别出句子中所有常见的连读、略读、插读、失去爆破、不完全爆破等现象。
        2.  **提供音标**：为整个句子提供国际音标 (IPA)。
        3.  **格式化输出**：
            - 使用 Markdown 格式。
            - 用颜色和符号来高亮显示语音现象。例如：
              - 连读 (Liaison): 使用下划线 `_` 连接单词，并用 `lian` class 包裹，例如 `<span class="lian">an‿apple</span>`。
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


# --- Streamlit 界面布局函数 ---

def setup_page_config_and_styles():
    """配置页面和注入CSS样式。"""
    st.set_page_config(page_title="英语语音现象分析器", page_icon="🗣️", layout="wide")
    st.markdown("""
        <style>
        .phonetic-analysis {
            background-color: #f0f2f6;
            border-left: 6px solid #1E90FF;
            padding: 15px;
            border-radius: 5px;
            font-size: 1.1em;
            line-height: 1.6;
        }
        .phonetic-analysis strong {
            color: #005A9C;
        }
        .lian {
            color: #28a745;
            font-weight: bold;
            text-decoration: underline;
            text-decoration-style: wavy;
        }
        /* 隐藏Streamlit页脚 */
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)


def setup_sidebar():
    """在侧边栏设置API密钥输入框。"""
    st.sidebar.header("🔑 API 密钥配置")
    st.sidebar.markdown("为了使用分析功能，请输入你的Google Gemini API密钥:\n链接：https://aistudio.google.com/app/api-keys")

    # 使用 st.session_state 来持久化存储 API 密钥
    if "GEMINI_API_KEY" not in st.session_state:
        st.session_state["GEMINI_API_KEY"] = ""

    api_key = st.sidebar.text_input(
        "Gemini API 密钥",
        type="password",
        value=st.session_state["GEMINI_API_KEY"],
        help="您的密钥将仅在当前浏览器会话中使用，不会被存储或分享。"
    )

    # 当输入框内容改变时，更新 session_state
    if api_key:
        st.session_state["GEMINI_API_KEY"] = api_key

    if st.session_state["GEMINI_API_KEY"]:
        st.sidebar.success("API 密钥已配置！", icon="✅")
    else:
        st.sidebar.warning("请输入您的 API 密钥以启用分析功能。", icon="⚠️")


def display_main_content():
    """显示页面的主要交互内容。"""
    st.title("🗣️ 英语句子语音现象分析器")
    st.markdown("输入一个英语句子，即可生成标准发音，并由 Gemini AI 分析其中包含的连读、略读等语音现象。\n"
                "部分符号说明："
                "- 连读 (Liaison): 使用上括号 `‿` 连接单词，例如 next‿two\n"
                "- 略读 (Elision): 在被省略的音素位置使用删除线 `~`，例如 las~t night\n"
                "- 插读 (Intrusion): 在插入音素的位置使用 `+` 号，例如 go+w away\n"
                "- | 符号表示自然的语调停顿。")

    with st.form("input_form"):
        sentence = st.text_input(
            "**在这里输入英语句子或短语：**",
            value="Let's get a cup of coffee.",
            placeholder="例如: What are you going to do?"
        )
        submitted = st.form_submit_button("分析并生成语音", type="primary")

    if submitted:
        if not st.session_state["GEMINI_API_KEY"]:
            st.error("操作失败：请先在左侧边栏输入您的 Gemini API 密钥。", icon="🚫")
            return

        # 配置 Gemini API
        try:
            genai.configure(api_key=st.session_state["GEMINI_API_KEY"])
        except Exception as e:
            st.error(f"API 密钥配置失败，请检查您的密钥是否正确。错误: {e}", icon="🚨")
            return

        # 开始处理并展示结果
        process_and_display_results(sentence)


def process_and_display_results(sentence: str):
    """协调分析和TTS过程，并在页面上展示结果。"""
    if not sentence:
        st.warning("请输入一个句子进行分析。", icon="✍️")
        return

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("语音现象分析 (由 Gemini 提供)")
        with st.spinner("🤖 Gemini 正在分析中，请稍候..."):
            analysis_result = analyze_phonetics_with_gemini(sentence)
            st.markdown(f'<div class="phonetic-analysis">{analysis_result}</div>', unsafe_allow_html=True)

    with col2:
        st.subheader("文本转语音 (TTS)")
        with st.spinner("🔊 正在生成语音，请稍候..."):
            audio_file_path = asyncio.run(generate_tts(sentence))
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
                st.error("无法生成或找到语音文件。")


# --- 主程序入口 ---

def main():
    """主函数, 运行 Streamlit 应用."""
    setup_page_config_and_styles()
    setup_sidebar()
    display_main_content()


if __name__ == "__main__":
    main()