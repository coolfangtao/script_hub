import streamlit as st
import edge_tts
import asyncio
from io import BytesIO
from langdetect import detect, LangDetectException

# 假设您的侧边栏文件位于项目的 "shared" 文件夹中
# from shared.sidebar import create_common_sidebar

# --- 全局常量与配置 ---

# 页面配置，建议放在脚本最开始
st.set_page_config(
    page_title="文本转语音生成器",
    page_icon="🔊",
    layout="centered"
)

# 扩展语言区域代码到中文名称的映射，并添加 Emoji
LOCALE_MAP = {
    "af": "🇿🇦 南非语", "ar": "🇸🇦 阿拉伯语", "bg": "🇧🇬 保加利亚语", "bn": "🇧🇩 孟加拉语",
    "ca": "🇪🇸 加泰罗尼亚语", "cs": "🇨🇿 捷克语", "cy": "🇬🇧 威尔士语", "da": "🇩🇰 丹麦语",
    "de": "🇩🇪 德语", "el": "🇬🇷 希腊语", "en": "🇬🇧 英语", "es": "🇪🇸 西班牙语",
    "et": "🇪🇪 爱沙尼亚语", "fa": "🇮🇷 波斯语", "fi": "🇫🇮 芬兰语", "fr": "🇫🇷 法语",
    "gu": "🇮🇳 古吉拉特语", "he": "🇮🇱 希伯来语", "hi": "🇮🇳 印地语", "hr": "🇭🇷 克罗地亚语",
    "hu": "🇭🇺 匈牙利语", "id": "🇮🇩 印度尼西亚语", "is": "🇮🇸 冰岛语", "it": "🇮🇹 意大利语",
    "ja": "🇯🇵 日语", "jv": "🇮🇩 爪哇语", "km": "🇰🇭 高棉语", "kn": "🇮🇳 卡纳达语",
    "ko": "🇰🇷 韩语", "lt": "🇱🇹 立陶宛语", "lv": "🇱🇻 拉脱维亚语", "ml": "🇮🇳 马拉雅拉姆语",
    "mr": "🇮🇳 马拉地语", "ms": "🇲🇾 马来语", "my": "🇲🇲 缅甸语", "ne": "🇳🇵 尼泊尔语",
    "nl": "🇳🇱 荷兰语", "no": "🇳🇴 挪威语", "pl": "🇵🇱 波兰语", "pt": "🇵🇹 葡萄牙语",
    "ro": "🇷🇴 罗马尼亚语", "ru": "🇷🇺 俄语", "si": "🇱🇰 僧伽罗语", "sk": "🇸🇰 斯洛伐克语",
    "sl": "🇸🇮 斯洛文尼亚语", "sq": "🇦🇱 阿尔巴尼亚语", "sr": "🇷🇸 塞尔维亚语", "su": "🇮🇩 巽他语",
    "sv": "🇸🇪 瑞典语", "sw": "🇰🇪 斯瓦希里语", "ta": "🇮🇳 泰米尔语", "te": "🇮🇳 泰卢固语",
    "th": "🇹🇭 泰语", "tr": "🇹🇷 土耳其语", "uk": "🇺🇦 乌克兰语", "ur": "🇵🇰 乌尔都语",
    "vi": "🇻🇳 越南语", "zh": "🇨🇳 中文",
}

GENDER_MAP = {
    "Male": "男声",
    "Female": "女声"
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
def get_voice_list() -> list[dict]:
    """
    获取所有可用的声音列表并缓存。
    返回一个字典列表，每个字典包含显示名称、短名称和语言代码。
    """
    try:
        voices = asyncio.run(edge_tts.list_voices())
        voice_list = []
        for v in voices:
            lang_code_short = v['Locale'].split('-')[0]
            lang_name = LOCALE_MAP.get(lang_code_short, lang_code_short)
            gender = GENDER_MAP.get(v['Gender'], v['Gender'])

            # 创建更优雅的显示名称
            display_name = (
                f"{lang_name} | {gender} - {v['ShortName'].split('-')[-1]}"
            )

            voice_list.append({
                "display_name": display_name,
                "short_name": v['ShortName'],
                "lang_code": lang_code_short
            })

        # 按显示名称的字母顺序排序
        return sorted(voice_list, key=lambda x: x['display_name'])

    except Exception as e:
        st.error(f"获取声音列表时出错: {e}")
        return []


def find_default_voice_index(voices: list[dict], lang_code: str = "zh") -> int:
    """在声音列表中查找一个合适的默认声音索引。"""
    # 优先尝试寻找特定的、高质量的声音
    preferred_voices = ["Xiaoxiao", "Yunxi", "Microsoft Server Speech Text to Speech Voice"]
    for p_voice in preferred_voices:
        for i, voice in enumerate(voices):
            if lang_code in voice["short_name"] and p_voice in voice["short_name"]:
                return i
    # 如果没找到，就返回该语言的第一个声音
    for i, voice in enumerate(voices):
        if voice["lang_code"] == lang_code:
            return i
    return 0  # 最终回退


# --- Streamlit 页面主函数 ---

def main():
    """主应用函数"""
    # 如果您有侧边栏，在这里调用
    # create_common_sidebar()

    st.title("🔊 文本转语音生成器")
    st.markdown("输入任何文本，选择一个喜欢的声音，即可轻松生成高质量的语音文件。")

    # 获取所有声音
    all_voices = get_voice_list()
    if not all_voices:
        st.error("无法加载声音列表，请刷新页面或检查网络连接。")
        st.stop()

    # --- UI 布局 ---
    with st.container(border=True):
        text_to_convert = st.text_area(
            "📝 **第一步：输入文本**",
            height=150,
            placeholder="例如：你好，欢迎使用这个文本转语音工具！"
        )

        # --- 语言检测与声音筛选 ---
        detected_lang = None
        if text_to_convert:
            try:
                # 仅在文本足够长时检测，避免不准确
                if len(text_to_convert) > 10:
                    detected_lang = detect(text_to_convert).split('-')[0]
            except LangDetectException:
                st.info("文本太短，无法自动检测语言。请手动选择声音。", icon="ℹ️")

        st.markdown("---")  # 分割线
        st.markdown("🗣️ **第二步：选择声音**")

        auto_filter = st.toggle(
            '根据输入文本自动筛选声音',
            value=True,
            help="开启后，将只显示与上方输入文本语言匹配的声音选项。"
        )

        # 根据开关状态和检测结果决定要显示的声音列表
        if auto_filter and detected_lang:
            filtered_voices = [v for v in all_voices if v["lang_code"] == detected_lang]
            if not filtered_voices:
                st.warning(f"未找到与检测到的语言 **({LOCALE_MAP.get(detected_lang, detected_lang)})** 匹配的声音。显示所有声音。")
                display_voices = all_voices
            else:
                display_voices = filtered_voices
        else:
            display_voices = all_voices

        # 计算默认声音的索引
        default_index = find_default_voice_index(display_voices, detected_lang or "zh")

        # 让用户选择声音
        selected_voice_display = st.selectbox(
            "请选择一个声音",
            options=[v["display_name"] for v in display_voices],
            index=default_index
        )

        # 查找选中声音对应的短名称
        selected_voice_short_name = next(
            v["short_name"] for v in display_voices if v["display_name"] == selected_voice_display
        )

    # --- 生成操作 ---
    if st.button("🚀 生成语音", type="primary", use_container_width=True):
        if text_to_convert:
            with st.spinner("🧠 正在生成语音，请稍候..."):
                try:
                    # 调用异步函数生成语音
                    audio_buffer = asyncio.run(
                        text_to_speech_async(text_to_convert, selected_voice_short_name)
                    )

                    st.success("🎉 生成成功！")

                    # 显示播放器和下载按钮
                    st.audio(audio_buffer, format="audio/mp3")
                    st.download_button(
                        label="📥 下载MP3文件",
                        data=audio_buffer,
                        file_name="generated_speech.mp3",
                        mime="audio/mp3",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"生成语音时出错: {e}")
        else:
            st.warning("请输入一些文本才能生成语音。")

    # --- 关于和说明 ---
    with st.expander("ℹ️ 关于与说明"):
        st.markdown("""
        - **技术支持**: 本工具使用 `edge-tts` 库，调用微软 Edge 浏览器的免费文本转语音服务。
        - **数据隐私**: 您的文本仅用于生成语音，不会被存储。
        - **智能推荐**: 工具会自动检测您输入的文本语言，并为您筛选出最匹配的声音列表，让选择更简单。
        """)


if __name__ == "__main__":
    main()