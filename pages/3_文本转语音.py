import streamlit as st
import edge_tts
import asyncio
from io import BytesIO
from langdetect import detect, LangDetectException
from typing import List, Dict, Any, Optional


# 假设您的侧边栏文件位于项目的 "shared" 文件夹中
from shared.usage_tracker import track_script_usage
from shared.sidebar import create_common_sidebar
track_script_usage("🔊 文字转语音")
create_common_sidebar()

# --- 1. 配置类 (Config) ---
# 将所有硬编码的常量和配置集中管理

class AppConfig:
    """应用配置类"""
    PAGE_TITLE = "文本转语音生成器"
    PAGE_ICON = "🔊"

    # 语言区域代码到显示名称的映射
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

    # 性别映射
    GENDER_MAP = {
        "Male": "男声",
        "Female": "女声"
    }

    # 查找默认声音时，优先选择的关键词
    PREFERRED_VOICES = ["Xiaoxiao", "Yunxi", "Microsoft Server Speech Text to Speech Voice"]


# --- 2. 服务类 (Service) ---
# 负责处理核心业务逻辑，如API调用、数据处理等，与UI分离

class TTSService:
    """文本转语音核心服务类"""

    @staticmethod
    async def text_to_speech_async(text: str, voice: str) -> BytesIO:
        """异步将文本转换为语音"""
        voice_data = BytesIO()
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                voice_data.write(chunk["data"])
        voice_data.seek(0)
        return voice_data

    @staticmethod
    @st.cache_data
    def get_voice_list() -> List[Dict[str, str]]:
        """获取并缓存所有可用的声音列表"""
        try:
            # 使用同步方式运行异步函数以适配 st.cache_data
            voices = asyncio.run(edge_tts.list_voices())
            voice_list = []
            for v in voices:
                lang_code_short = v['Locale'].split('-')[0]
                lang_name = AppConfig.LOCALE_MAP.get(lang_code_short, lang_code_short)
                gender = AppConfig.GENDER_MAP.get(v['Gender'], v['Gender'])
                display_name = f"{lang_name} | {gender} - {v['ShortName'].split('-')[-1]}"

                voice_list.append({
                    "display_name": display_name,
                    "short_name": v['ShortName'],
                    "lang_code": lang_code_short
                })
            # 按显示名称排序
            return sorted(voice_list, key=lambda x: x['display_name'])
        except Exception as e:
            st.error(f"获取声音列表时出错: {e}")
            return []

    @staticmethod
    def find_default_voice_index(voices: List[Dict[str, str]], lang_code: str = "zh") -> int:
        """在声音列表中查找合适的默认声音索引"""
        # 优先尝试寻找特定的、高质量的声音
        for p_voice in AppConfig.PREFERRED_VOICES:
            for i, voice in enumerate(voices):
                if lang_code in voice["short_name"] and p_voice in voice["short_name"]:
                    return i
        # 如果没找到，就返回该语言的第一个声音
        for i, voice in enumerate(voices):
            if voice["lang_code"] == lang_code:
                return i
        return 0  # 最终回退

    @staticmethod
    def detect_language(text: str) -> Optional[str]:
        """检测文本的语言"""
        if len(text) > 10:
            try:
                return detect(text).split('-')[0]
            except LangDetectException:
                return None
        return None


# --- 3. UI类 (UI) ---
# 负责所有Streamlit的UI组件渲染

class AppUI:
    """应用UI界面类"""

    def __init__(self, service: TTSService):
        self.service = service
        self.all_voices = self.service.get_voice_list()

    def _initialize_session_state(self):
        """初始化 session_state，用于跨页面或重跑时保存用户输入"""
        if "text_to_convert" not in st.session_state:
            st.session_state.text_to_convert = "你好，欢迎使用这个文本转语音工具！"
        if "generated_audio" not in st.session_state:
            st.session_state.generated_audio = None

    def render_header(self):
        """渲染页面标题和介绍"""
        st.title(f"{AppConfig.PAGE_ICON} {AppConfig.PAGE_TITLE}")
        st.markdown("输入任何文本，选择一个喜欢的声音，即可轻松生成高质量的语音文件。")

    def render_input_form(self):
        """渲染文本输入和声音选择表单"""
        with st.container(border=True):
            st.text_area(
                "📝 **第一步：输入文本**",
                height=150,
                key="text_to_convert"  # 关键：将组件与session_state关联
            )

            st.markdown("---")
            st.markdown("🗣️ **第二步：选择声音**")

            # 语言检测
            detected_lang = self.service.detect_language(st.session_state.text_to_convert)

            auto_filter = st.toggle(
                '根据输入文本自动筛选声音',
                value=True,
                help="开启后，将只显示与上方输入文本语言匹配的声音选项。"
            )

            # 根据条件筛选声音列表
            display_voices = self.all_voices
            if auto_filter and detected_lang:
                filtered_voices = [v for v in self.all_voices if v["lang_code"] == detected_lang]
                if filtered_voices:
                    display_voices = filtered_voices
                else:
                    st.warning(
                        f"未找到与检测到的语言 **({AppConfig.LOCALE_MAP.get(detected_lang, detected_lang)})** 匹配的声音。显示所有声音。")

            # 确定默认选项
            default_index = self.service.find_default_voice_index(display_voices, detected_lang or "zh")

            # 声音选择框
            selected_voice_display = st.selectbox(
                "请选择一个声音",
                options=[v["display_name"] for v in display_voices],
                index=default_index
            )

            # 返回选择的声音 short_name
            return next(v["short_name"] for v in display_voices if v["display_name"] == selected_voice_display)

    def render_generate_button(self, selected_voice_short_name: str):
        """渲染生成按钮并处理点击事件"""
        if st.button("🚀 生成语音", type="primary", use_container_width=True):
            text = st.session_state.text_to_convert
            if text:
                with st.spinner("🧠 正在生成语音，请稍候..."):
                    try:
                        audio_buffer = asyncio.run(
                            self.service.text_to_speech_async(text, selected_voice_short_name)
                        )
                        st.session_state.generated_audio = audio_buffer  # 保存到session
                        st.success("🎉 生成成功！")
                    except Exception as e:
                        st.error(f"生成语音时出错: {e}")
                        st.session_state.generated_audio = None
            else:
                st.warning("请输入一些文本才能生成语音。")

    def render_audio_player(self):
        """如果生成了音频，则渲染播放器和下载按钮"""
        if st.session_state.generated_audio:
            audio_buffer = st.session_state.generated_audio
            st.audio(audio_buffer, format="audio/mp3")
            st.download_button(
                label="📥 下载MP3文件",
                data=audio_buffer,
                file_name="generated_speech.mp3",
                mime="audio/mp3",
                use_container_width=True
            )

    def render_footer(self):
        """渲染页脚说明"""
        with st.expander("ℹ️ 关于与说明", expanded=True):
            st.markdown("""
            - **技术支持**: 本工具使用 `edge-tts` 库，调用微软 Edge 浏览器的免费文本转语音服务。
            - **数据隐私**: 您的文本仅用于生成语音，不会被存储。
            - **智能推荐**: 工具会自动检测您输入的文本语言，并为您筛选出最匹配的声音列表。
            - **状态保持**: 您的输入文本和生成的音频会在当前会话中被记住，即使切换到其他页面再返回。
            """)

    def render(self):
        """渲染整个页面"""
        self._initialize_session_state()
        self.render_header()

        if not self.all_voices:
            st.error("无法加载声音列表，请刷新页面或检查网络连接。")
            st.stop()

        selected_voice = self.render_input_form()
        self.render_generate_button(selected_voice)
        self.render_audio_player()
        self.render_footer()


# --- 4. 主应用 (Main App) ---
# 组装并运行App

def main():
    """主应用函数"""
    st.set_page_config(
        page_title=AppConfig.PAGE_TITLE,
        page_icon=AppConfig.PAGE_ICON,
        layout="wide"
    )

    # 实例化服务和UI
    tts_service = TTSService()
    app_ui = AppUI(tts_service)

    # 渲染页面
    app_ui.render()


if __name__ == "__main__":
    main()