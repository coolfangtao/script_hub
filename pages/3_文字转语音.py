import streamlit as st
import edge_tts
import asyncio
from io import BytesIO

# --- 核心功能函数 ---

async def text_to_speech_async(text: str, voice: str) -> BytesIO:
    """
    异步函数，接收文本和声音名称，返回包含MP3数据的BytesIO对象。
    """
    voice_data = BytesIO()
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            voice_data.write(chunk["data"])
    voice_data.seek(0)
    return voice_data

@st.cache_data
def get_voice_list() -> dict:
    """
    获取所有可用的声音列表并缓存结果，返回一个显示名称到短名称的映射字典。
    """
    try:
        # 在异步环境中运行 list_voices
        voices = asyncio.run(edge_tts.list_voices())
        # 创建一个更友好的显示名称
        voice_map = {
            f"{v['Locale']} - {v['ShortName'].split('-')[-1]} ({v['Gender']})": v['ShortName']
            for v in voices
        }
        return voice_map
    except Exception as e:
        st.error(f"无法获取声音列表: {e}")
        return {}


# --- Streamlit 页面布局 ---

st.set_page_config(page_title="文本转语音生成器", layout="centered")

st.title("🔊 文本转语音生成器")
st.markdown("输入任何文本，选择一个声音，然后生成可以播放和下载的语音文件。")

# 获取并显示声音选择框
voice_map = get_voice_list()
if voice_map:
    display_name = st.selectbox(
        "请选择一个声音（zh开头为中文，en开头为英文，请务必选择正确）",
        options=list(voice_map.keys()),
        index=list(voice_map.keys()).index("en-US - JennyNeural (Female)")  # 默认选中一个常用声音
    )
    selected_voice = voice_map[display_name]

    # 输入文本框
    text_to_convert = st.text_area(
        "请输入要转换的文本",
        height=150,
        placeholder="例如：Hello, Streamlit! This is a text-to-speech app."
    )

    # 生成按钮
    if st.button("生成语音", type="primary"):
        if text_to_convert:
            with st.spinner("正在生成语音，请稍候..."):
                try:
                    # 调用异步函数生成语音
                    audio_buffer = asyncio.run(text_to_speech_async(text_to_convert, selected_voice))

                    # 显示播放器
                    st.audio(audio_buffer, format="audio/mp3")

                    # 提供下载按钮
                    st.download_button(
                        label="📥 下载MP3文件",
                        data=audio_buffer,
                        file_name="generated_speech.mp3",
                        mime="audio/mp3"
                    )
                except Exception as e:
                    st.error(f"生成语音时出错: {e}")
        else:
            st.warning("请输入一些文本才能生成语音。")
else:
    st.error("无法加载声音列表，请检查网络连接或依赖项。")

# --- 运行说明 ---
st.info("如何运行本应用：\n1. 确保已安装所需库: pip install streamlit edge-tts\n2. 在终端运行: streamlit run app.py")
