# shared/config.py

import yaml
from pathlib import Path


class Config:
    """
    这个类用于集中存放所有Streamlit应用的配置参数。理论上所有的硬编码都应该放在这里
    它支持从YAML文件加载配置、动态设置/获取值以及清晰地打印所有配置项。
    """

    def __init__(self):
        # --- 默认配置 ---
        # 即使没有外部配置文件，这些值也会被设置

        # 页面基础设置
        self.PAGE_TITLE = "我的多页面应用"
        self.PAGE_ICON = "🎈"
        self.LAYOUT = "wide"
        self.INITIAL_SIDEBAR_STATE = "expanded"

        # 应用元数据
        self.APP_NAME = "Streamlit 工具箱"
        self.APP_VERSION = "1.2.0"
        self.CONTACT_EMAIL = "morebetter2025@163.com"
        self.GITHUB_URL = "https://github.com/your_username/your_repo"

        # API密钥和凭证 (通过st.secrets()获得)
        self.GEMINI_API_KEY = "gemini_api_key"
        self.IMGBB_API_KEY = "imgbb_api_key"
        self.FEEDBACK_DB_URL = "feedback_db_url"
        self.FEEDBACK_DB_TOKEN = "feedback_db_token"

        # 文件和目录路径
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.DATA_DIR = self.BASE_DIR / "data"
        self.SHARED_DIR = self.BASE_DIR / "shared"
        self.SAMPLE_DATA_PATH = self.DATA_DIR / "sample_data.csv"

        # Listing自动生成参数
        self.LISTING_DEFAULT_MODEL = "gemini-2.5-pro"

        # 分析英语句子参数
        self.DEFAULT_VOICE_NAME= "en-US-JennyNeural"
        self.ANALYSIS_DEFAULT_MODEL = "gemini-2.0-flash"

        # 业务逻辑参数
        self.DEFAULT_ITEMS_TO_SHOW = 10
        self.MAX_QUERY_LENGTH = 500
        self.DEFAULT_MODEL_NAME = "gpt-4"

        # 样式和主题
        self.PRIMARY_COLOR = "#FF4B4B"
        self.BACKGROUND_COLOR = "#FFFFFF"
        self.FONT_FAMILY = "sans-serif"

        # 可用的AI模型
        self.GEMINI_MODEL_OPTIONS = [
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

        # 杂质检测可用的AI模型
        self.ZAZHI_JIANCE_GEMINI_MODEL_OPTIONS = [
            "gemini-2.5-flash-lite",  # 默认模型，可用，2.15秒
            "gemini-2.0-flash",  # 可用，5.11秒
            "gemini-2.5-pro",   # 可用，14.93秒
            "gemini-2.0-flash-exp",  # 可用，4.28秒
            "gemini-2.0-flash-lite",  # 可用，9.62秒
            "gemini-2.5-flash",  # 可用，6.74秒
            "gemini-robotics-er-1.5-preview",  # 可用，8.73秒
        ]
        self.ZAZHI_JIANCE_GET_ELEMENTS_DATA_PROMPT = """
                        请仔细分析提供的图片，该图片展示了X射线能谱（EDS）分析的结果界面。你的任务是从右上角的‘定量结果’表格中，提取所有检测到的元素的定量分析数据。
                        对于表格中列出的每一个元素，请提取并清晰地列出以下两个数值：
                        - 质量百分比（Mass %）： 提取该元素在‘质量%’列中的数值及其不确定度。
                        - 原子百分比（Atomic %）： 提取该元素在‘原子%’列中的数值及其不确定度。
                        请以 Markdown 表格的格式呈现这些数据，确保所有数值及其对应的不确定度都完整且准确地体现在输出中。
                        最后关注‘定量结果’列表中的元素及其含量，并结合能谱图的峰位，判断被测物质的主要成分以及可能存在的杂质。
                        """

    def get(self, key, default=None):
        """
        安全地获取一个配置项的值。

        :param key: 配置项的名称 (字符串)
        :param default: 如果配置项不存在时返回的默认值
        :return: 配置项的值或默认值
        """
        return getattr(self, key, default)

    def set(self, key, value):
        """
        动态地设置一个配置项的值。
        如果配置项已存在，则更新其值；如果不存在，则创建它。

        :param key: 配置项的名称 (字符串)
        :param value: 要设置的新值
        """
        setattr(self, key, value)
        return self  # 支持链式调用，例如 config.set(...).set(...)

    def load_from_yaml(self, file_path):
        """
        从YAML文件加载配置并更新现有配置。
        文件中的键需要与类中的属性名匹配。

        :param file_path: YAML配置文件的路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config:
                for key, value in yaml_config.items():
                    # 使用 set 方法来更新值
                    self.set(key, value)
        except FileNotFoundError:
            print(f"警告: 配置文件 '{file_path}' 未找到。将使用默认配置。")
        except Exception as e:
            print(f"错误: 加载或解析配置文件 '{file_path}'失败: {e}")

        return self  # 支持链式调用

    def to_dict(self):
        """
        将所有配置项转换为字典。
        """
        return {key: value for key, value in self.__dict__.items()}

    def __repr__(self):
        """
        返回一个清晰的、可读的字符串表示形式，方便调试。
        """
        class_name = self.__class__.__name__
        attributes = "\n".join(f"  {key} = {value!r}" for key, value in self.to_dict().items())
        return f"{class_name}(\n{attributes}\n)"