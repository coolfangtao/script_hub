import streamlit as st
import edge_tts
import asyncio
from io import BytesIO
from langdetect import detect, LangDetectException
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# --- 语言区域代码到中文名称的映射 ---
# 用于在下拉菜单中显示更友好的语言名称
LOCALE_MAP = {
    "zh": "中文（简体）",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "th": "泰语",
    "vi": "越南语",
    "ar": "阿拉伯语",

    "pt": "葡萄牙语",
    "it": "意大利语",
    "hi": "印地语",
    # 可以根据需要添加更多语言
}


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
    获取所有可用的声音列表并缓存结果。
    返回一个从显示名称到声音短名称的映射字典，并按语言排序。
    """
    try:
        # 在异步环境中运行 list_voices
        voices = asyncio.run(edge_tts.list_voices())
        voice_map = {}
        for v in voices:
            # 解析语言代码，例如 "zh-CN" -> "zh"
            lang_code_short = v['Locale'].split('-')[0]
            # 从映射中获取中文名称，如果找不到则使用原始代码
            lang_name = LOCALE_MAP.get(lang_code_short, lang_code_short)

            # 创建更友好的显示名称
            display_name = (
                f"【{lang_name}】{v['ShortName'].split('-')[-1]} "
                f"({v['Gender']}) - {v['Locale']}"
            )
            voice_map[display_name] = v['ShortName']

        # 按键（显示名称）排序，使得相同语言的声音聚在一起
        return dict(sorted(voice_map.items()))

    except Exception as e:
        st.error(f"无法获取声音列表: {e}")
        return {}


# --- Streamlit 页面布局 ---

st.set_page_config(page_title="文本转语音生成器", layout="centered")

st.title("🔊 文本转语音生成器")
st.markdown("输入文本，选择匹配语言的声音，即可生成可播放和下载的语音文件。")

# 获取并显示声音选择框
voice_map = get_voice_list()
if voice_map:
    # 查找一个合适的中文声音作为默认选项
    options = list(voice_map.keys())
    default_index = 0
    try:
        # 寻找一个包含"Xiaoxiao"（一个常用的中文女声）的选项
        preferred_voice = next(i for i, s in enumerate(options) if "zh-CN" in s and "Xiaoxiao" in s)
        default_index = preferred_voice
    except StopIteration:
        # 如果找不到，就使用第一个
        pass

    display_name = st.selectbox(
        "请选择一个声音",
        options=options,
        index=default_index
    )
    selected_voice = voice_map[display_name]

    # 输入文本框
    text_to_convert = st.text_area(
        "请输入要转换的文本",
        height=150,
        placeholder="例如：你好，欢迎使用这个文本转语音工具！"
    )

    # 生成按钮
    if st.button("生成语音", type="primary"):
        if text_to_convert:
            # --- 语言检测与匹配逻辑 ---
            try:
                detected_lang = detect(text_to_convert).split('-')[0]  # 例如 'zh-cn' -> 'zh'
                voice_lang = selected_voice.split('-')[0]  # 例如 'zh-CN-XiaoxiaoNeural' -> 'zh'

                if detected_lang != voice_lang:
                    st.warning(
                        f"**语言不匹配警告！**\n\n"
                        f"- 您输入的文本检测为：**{LOCALE_MAP.get(detected_lang, detected_lang)}**\n"
                        f"- 您选择的声音是：**{LOCALE_MAP.get(voice_lang, voice_lang)}**\n\n"
                        f"请选择与文本语言匹配的声音，否则可能无法生成或效果不佳。"
                    )
                    # 停止执行，防止程序因语言不匹配而报错
                    st.stop()

            except LangDetectException:
                st.warning("文本过短，无法准确检测语言。将继续尝试生成，但请确保您选择了正确的语言。")

            # --- 语音生成核心逻辑 ---
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
st.info(
    "待优化点：\n"
    "1. 输入文本自动推荐对应语言声音\n"
    "2. 声音全部翻译成中文"
)