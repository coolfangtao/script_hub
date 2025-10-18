import streamlit as st
import edge_tts
import asyncio
from io import BytesIO

# --- 语言代码到中文名称的映射 ---
LOCALE_MAP = {
    "zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语",
    "fr": "法语", "de": "德语", "es": "西班牙语", "ru": "俄语",
    "it": "意大利语", "pt": "葡萄牙语", "ar": "阿拉伯语", "hi": "印地语",
    "tr": "土耳其语", "nl": "荷兰语", "sv": "瑞典语", "pl": "波兰语",
    "th": "泰语", "vi": "越南语",
}


def get_language_name(locale_code: str) -> str:
    """根据地区代码返回中文语言名称"""
    lang_prefix = locale_code.split('-')[0]
    return LOCALE_MAP.get(lang_prefix, lang_prefix)  # 如果找不到，则返回原始前缀


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
        # 创建一个更友好的显示名称，并按语言排序
        voice_options = []
        for v in voices:
            lang_name = get_language_name(v['Locale'])
            display_name = (
                f"{lang_name} ({v['Locale']}) - "
                f"{v['ShortName'].split('-')[-1]} ({v['Gender']})"
            )
            voice_options.append((display_name, v['ShortName']))

        # 按语言名称排序
        voice_options.sort()
        voice_map = {display: shortname for display, shortname in voice_options}
        return voice_map
    except Exception as e:
        st.error(f"无法获取声音列表: {e}")
        return {}


# --- Streamlit 页面布局 ---

st.set_page_config(page_title="文本转语音生成器", layout="centered")

st.title("🔊 文本转语音生成器")

# --- 添加用户请求的启动代码 ---
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("输入任何文本，选择一个声音，然后生成可以播放和下载的语音文件。")

with col2:
    if st.button("📊 合并多个ASIN的关键词结果", help="合并多个Excel文件到一个Excel中", use_container_width=True):
        # 使用 st.switch_page 切换到指定页面
        st.switch_page(r"pages/2_合并多个ASIN的关键词结果.py")

st.divider()  # 添加分隔线以改善布局

# --- 原有的应用功能 ---

# 获取并显示声音选择框
voice_map = get_voice_list()
if voice_map:
    # 查找默认声音的新显示名称
    default_voice_shortname = "en-US-JennyNeural"
    default_display_name = None
    for display, shortname in voice_map.items():
        if shortname == default_voice_shortname:
            default_display_name = display
            break

    # 如果找到了，就用它作为默认值
    default_index = 0
    if default_display_name:
        try:
            default_index = list(voice_map.keys()).index(default_display_name)
        except ValueError:
            default_index = 0  # 如果找不到，则默认为第一个

    display_name = st.selectbox(
        "请选择一个声音（已按语言分类）",
        options=list(voice_map.keys()),
        index=default_index
    )
    selected_voice = voice_map[display_name]

    # 输入文本框
    text_to_convert = st.text_area(
        "请输入要转换的文本",
        height=150,
        placeholder="例如：你好，世界！或者 Hello, Streamlit!"
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