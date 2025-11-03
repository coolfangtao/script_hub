import streamlit as st
import pandas as pd
import re
from io import StringIO
import plotly.graph_objects as go
import textwrap  # 导入textwrap库用于自动换行


# --- 配置类 ---
# 用于存放所有固定参数、模板和样式，方便统一管理和修改。
class Config:
    """存放所有配置参数和模板"""

    PAGE_TITLE = "专业级英语音变可视化工具 (最终版)"
    PAGE_ICON = "🌟"

    # 统一管理所有字体大小
    FONT_SIZES = {
        'row_label': 14,
        'sentence': 22,
        'ipa': 16,
        'connected_ipa': 18,
        'phenomenon_name': 12,
        'phenomenon_details': 11,
        'linking_title': 14,
        'linking_details': 11
    }

    # 定义每种音变现象的颜色
    PHENOMENON_COLORS = {
        "弱读 (Reduction)": "royalblue",
        "连读 (Linking)": "mediumorchid",
        "失爆 (Incomplete Plosion)": "darkorange",
        "省略 (Elision)": "crimson",
        "同化 (Assimilation)": "mediumseagreen",
        "闪音/弹音 (Flapping)": "goldenrod",
        "口语缩合 (Contraction)": "darkviolet"
    }

    # AI提示词模板
    PROMPT_TEMPLATE = """
# Role
你是一位精通英语语音学的语言学专家。

# Task
你的任务是为用户提供的英文句子，进行详细的语音学分析。你需要提供两种核心信息：一是每个单词的独立标准发音（强读式），二是在自然口语流中的实际发音（连读式），并解释其中发生的关键音变现象。

# Constraints
1.  所有音标必须使用国际音标（IPA）。
2.  发音标准一律采用通用美式英语（General American English）。
3.  输出格式必须严格遵守下面【输出格式】部分定义的Markdown结构。不要有任何偏差。
4.  在【音变现象解析】表格中，如果某个音变现象未在句子中明显出现，则其对应的第二列必须且只能填写“未出现”三个字。不要留空或填写其他任何解释性文字。

# Output Format

### 1. 独立单词发音 (Strong Forms)
| Word | IPA (US) |
| :--- | :--- |
| [单词1] | [IPA 1] |
| [单词2] | [IPA 2] |
| ... | ... |

### 2. 日常口语发音 (Connected Speech)
**IPA:** [完整的口语IPA转写]

#### 音变现象解析
| 音变现象 | 在句中的体现 (音标变化) |
| :--- | :--- |
| **弱读 (Reduction)** | [描述哪些单词的元音被弱化，例如：'you' /juː/ → /jə/] |
| **连读 (Linking)** | [描述单词间的连接，例如：辅元连读 'about‿it'] |
| **失爆 (Incomplete Plosion)**| [描述哪个爆破音只做了口型但未送气，例如：'goo(d) boy' /ɡʊd̚ bɔɪ/] |
| **省略 (Elision)** | [描述哪个音被省略了，例如：'and' /ænd/ → /ən/] |
| **同化 (Assimilation)**| [描述哪个音受邻近音影响而改变，例如：'have to' /hæv tu/ → /hæf tu/] |
| **闪音/弹音 (Flapping)** | [描述哪个/t/或/d/音变成了闪音/ɾ/，例如：'about it' /əˈbaʊt ɪt/ → /əˈbaʊɾɪt/] |
| **口语缩合 (Contraction)** | [描述发生了哪些口语合并，例如：'going to' → 'gonna' /ˈɡənə/] |

---

## 示例

### Input Sentence:
What are you going to do about it?

### Expected Output:

### 1. 独立单词发音 (Strong Forms)
| Word | IPA (US) |
| :--- | :--- |
| What | /wʌt/ |
| are | /ɑːr/ |
| you | /juː/ |
| going | /ˈɡoʊ.ɪŋ/ |
| to | /tuː/ |
| do | /duː/ |
| about | /əˈbaʊt/ |
| it | /ɪt/ |

### 2. 日常口语发音 (Connected Speech)
**IPA:** /ˌwʌɾəjə ˈɡənə ˈduːwəˌbaʊɾɪt̚/

#### 音变现象解析
| 音变现象 | 在句中的体现 (音标变化) |
| :--- | :--- |
| **弱读 (Reduction)** | 'are' /ɑːr/ → /ə/， 'you' /juː/ → /jə/ |
| **连读 (Linking)** | 'do‿about' 中间出现 /w/ 过渡音；'What‿are‿you' 整体连接 |
| **失爆 (Incomplete Plosion)**| 句末 'it' 的 /t/ 失去爆破，标记为 /t̚/，只做口型不送气 |
| **省略 (Elision)** | 'What are' /wʌt ɑːr/ 中的 /r/ 在快速口语中可能被省略 |
| **同化 (Assimilation)**| 未出现 |
| **闪音/弹音 (Flapping)** | 'What' 的 /t/ → /ɾ/；'about it' 的 /t/ → /ɾ/ |
| **口语缩合 (Contraction)** | 'going to' → 'gonna' /ˈɡənə/ |

---
现在，请根据以上规则，为下面的句子生成分析：

**Input Sentence:**
{sentence}
"""


# --- 解析器类 ---
# 负责将AI返回的、符合格式的Markdown文本转换成程序可以处理的结构化数据（字典）。
class MarkdownParser:
    """解析AI输出的Markdown文本"""

    def __init__(self, markdown_text, sentence):
        self.text = markdown_text
        self.sentence_words = [word.strip(".,?!") for word in sentence.split()]
        if not self.text or not self.sentence_words:
            raise ValueError("Markdown文本和原始句子不能为空。")

    def parse_strong_forms(self):
        """解析'独立单词发音'表格"""
        try:
            table_match = re.search(r"### 1\. 独立单词发音 \(Strong Forms\)\s*([\s\S]*?)\s*### 2\.", self.text)
            if not table_match: raise ValueError("未找到'独立单词发音'表格。")
            table_str = table_match.group(1).strip()
            # 使用Pandas读取Markdown表格，非常高效健壮
            df = pd.read_csv(StringIO(table_str), sep='|', skipinitialspace=True).dropna(axis=1, how='all').iloc[1:]
            df.columns = [col.strip() for col in df.columns]
            return {row['Word'].strip(): row['IPA (US)'].strip() for _, row in df.iterrows()}
        except Exception as e:
            raise ValueError(f"解析'独立单词发音'表格失败: {e}")

    def parse_connected_speech(self):
        """解析'日常口语发音'行"""
        try:
            match = re.search(r"\*\*IPA:\*\*\s*(.*)", self.text)
            return match.group(1).strip() if match else "未能解析"
        except Exception as e:
            raise ValueError(f"解析'日常口语发音'失败: {e}")

    def parse_phenomena_by_word(self):
        """解析'音变现象解析'表格，并将数据按单词索引组织"""
        try:
            table_match = re.search(r"#### 音变现象解析\s*([\s\S]*)", self.text)
            if not table_match: raise ValueError("未找到'音变现象解析'表格。")
            table_str = table_match.group(1).strip()
            df = pd.read_csv(StringIO(table_str), sep='|', skipinitialspace=True).dropna(axis=1, how='all').iloc[1:]
            df.columns = [col.strip() for col in df.columns]

            # 创建一个字典，键是单词的索引，值是发生在该单词上的音变现象列表
            phenomena_by_index = {i: [] for i in range(len(self.sentence_words))}

            for _, row in df.iterrows():
                phenomenon_name = row['音变现象'].replace('*', '').strip()
                details_full = row['在句中的体现 (音标变化)'].strip()

                if details_full != "未出现":
                    # 按中英文分号分割，处理一个现象有多个实例的情况 (e.g., 句子中有多个弱读)
                    sub_details = re.split(r'[；;]', details_full)
                    for detail_part in sub_details:
                        detail_part = detail_part.strip()
                        if not detail_part: continue

                        # 找出这个音变实例涉及的单词
                        involved_words_raw = re.findall(r"'([^']+)'", detail_part)
                        involved_words = []
                        for word_raw in involved_words_raw:
                            involved_words.extend(word_raw.replace('‿', ' ').split())

                        # 找到这些单词在原句中的索引
                        indices = []
                        unique_involved_words = sorted(list(set(involved_words)))

                        for word in unique_involved_words:
                            try:
                                for i, s_word in enumerate(self.sentence_words):
                                    if s_word.lower() == word.lower():
                                        indices.append(i)
                            except ValueError:
                                pass

                        # 将这个现象的详细信息添加到所有相关单词的条目下
                        for i in set(indices):
                            phenomena_by_index[i].append({
                                "name": phenomenon_name,
                                "details": detail_part,
                            })
            return phenomena_by_index
        except Exception as e:
            raise ValueError(f"解析'音变现象解析'表格失败: {e}")

    def parse_all(self):
        """一个主方法，调用所有解析函数并返回一个包含所有数据的字典"""
        return {
            "original_sentence": " ".join(self.sentence_words),
            "strong_forms": self.parse_strong_forms(),
            "connected_ipa": self.parse_connected_speech(),
            "phenomena_by_word": self.parse_phenomena_by_word()
        }


# --- 可视化类 ---
# 负责将解析后的结构化数据转换成Plotly图表。
class PlotlyVisualizerV5:
    """使用Plotly生成高级可视化图表（最终美化版）"""

    def __init__(self, data, config):
        self.data = data
        self.config = config
        self.fig = go.Figure()
        self.word_positions = []  # 用于存储每个单词的X坐标范围
        # 为口语缩合增加Y坐标层级
        self.y_levels = {
            'contraction_box': 7.5,
            'linking_box': 6.0,
            'sentence': 5,
            'connected_ipa': 4,
            'strong_ipa': 3,
            'phenomena_start': 2.0
        }

    def _wrap_text(self, text, width=25):
        """辅助函数，用于将长文本按指定宽度换行"""
        wrapped_lines = textwrap.wrap(text, width=width, break_long_words=False, replace_whitespace=False)
        return '<br>'.join(wrapped_lines)  # 转换为Plotly可识别的HTML换行符

    def generate_figure(self):
        """生成图表的主方法"""
        words = self.data["original_sentence"].split()

        self._draw_text_rows_with_labels()
        # 【修改】调用重构后的方法，它现在返回的是音变现象的总行数
        num_phenom_rows = self._draw_phenomena_annotations()
        self._draw_spanning_annotations()

        fig_width = max(800, len(words) * 150)

        # 【修改】根据现象行数动态计算Y轴范围，确保所有行都可见
        # 我们在 _draw_phenomena_annotations 中定义的行高为 2.2
        min_y_range = self.y_levels['phenomena_start'] - (num_phenom_rows * 2.2)

        self.fig.update_layout(
            width=fig_width,
            # 【修改】同样使用行数和行高来动态计算图表高度
            height=max(500, (self.y_levels['contraction_box'] + 2.0 - min_y_range) * 60),
            xaxis=dict(visible=False, range=[0, self.word_positions[-1]['end'] + 5 if self.word_positions else 20]),
            yaxis=dict(visible=False, range=[min_y_range, self.y_levels['contraction_box'] + 2.0]),
            plot_bgcolor='white',
            margin=dict(l=10, r=10, t=20, b=20),
            font_family="Arial, sans-serif",
            showlegend=False
        )
        return self.fig

    def _draw_text_rows_with_labels(self):
        """绘制新的三行文本布局"""
        labels = ["原始句子", "日常口语发音", "独立发音"]
        y_coords = [self.y_levels['sentence'], self.y_levels['connected_ipa'], self.y_levels['strong_ipa']]

        for label, y in zip(labels, y_coords):
            self.fig.add_annotation(x=0, y=y, text=f"<b>{label}</b>", showarrow=False, xanchor='left',
                                    font_size=self.config.FONT_SIZES['row_label'], font_color='gray')

        words = self.data["original_sentence"].split()
        strong_forms = self.data["strong_forms"]
        current_x = 15.0

        for word in words:
            ipa = strong_forms.get(word, "")
            word_width = max(len(word) * 2.2, len(ipa) * 1.8) + 6  # 调整宽度计算
            x_center = current_x + word_width / 2

            # 绘制第一行：原始句子
            self.fig.add_annotation(x=x_center, y=self.y_levels['sentence'], text=f"<b>{word}</b>", showarrow=False,
                                    font_size=self.config.FONT_SIZES['sentence'])
            # 绘制第三行：独立发音
            self.fig.add_annotation(x=x_center, y=self.y_levels['strong_ipa'], text=ipa, showarrow=False,
                                    font_size=self.config.FONT_SIZES['ipa'], font_color="dimgray")

            self.word_positions.append({'start': current_x, 'center': x_center, 'end': current_x + word_width})
            current_x += word_width + 5

        # 绘制居中的日常口语发音
        if self.word_positions:
            sentence_start_x = self.word_positions[0]['start']
            sentence_end_x = self.word_positions[-1]['end']
            sentence_center_x = (sentence_start_x + sentence_end_x) / 2
            self.fig.add_annotation(x=sentence_center_x, y=self.y_levels['connected_ipa'],
                                    text=self.data['connected_ipa'],
                                    showarrow=False, xanchor='center',
                                    font_size=self.config.FONT_SIZES['connected_ipa'],
                                    font_color='royalblue')

    # --- vvv 主要修改区域 vvv ---
    def _draw_phenomena_annotations(self):
        """
        绘制单词下方的音变现象标签。
        新逻辑：每种音变现象占据一个独立的水平行，以避免标签重叠。
        """
        phenomena_by_word = self.data["phenomena_by_word"]
        ROW_HEIGHT = 2.2  # 定义固定的行高，为标签和描述文字提供足够空间
        DETAILS_OFFSET = 0.6  # 标签和描述之间的垂直偏移量

        # 1. 找出所有出现过的、非跨词的音变现象类型
        all_non_spanning_phenomena_names = set()
        for i in range(len(self.word_positions)):
            for p in phenomena_by_word.get(i, []):
                # 过滤掉连读和口语缩合这两种跨词现象
                if "连读" not in p['name'] and "口语缩合" not in p['name']:
                    all_non_spanning_phenomena_names.add(p['name'])

        # 2. 为每种现象类型分配一个固定的Y轴层级（行），并排序确保每次生成的顺序一致
        sorted_phenom_types = sorted(list(all_non_spanning_phenomena_names))
        phenom_to_row_map = {name: i for i, name in enumerate(sorted_phenom_types)}

        # 3. 遍历每个单词，并在正确的“行”上绘制其对应的音变现象
        for i in range(len(self.word_positions)):
            x_center = self.word_positions[i]['center']

            # 过滤出当前单词的、需要在此处绘制的现象
            word_phenomena = [p for p in phenomena_by_word.get(i, []) if p['name'] in phenom_to_row_map]

            if not word_phenomena:
                continue

            # 为这个单词绘制一条从IPA指向其最顶层现象的连接线
            top_phenom_row = min([phenom_to_row_map[p['name']] for p in word_phenomena])
            line_y_start = self.y_levels['strong_ipa'] - 0.3
            line_y_end = self.y_levels['phenomena_start'] - (top_phenom_row * ROW_HEIGHT) + 0.35
            self.fig.add_shape(type="line", x0=x_center, y0=line_y_start, x1=x_center, y1=line_y_end,
                               line=dict(color="lightgrey", width=1.5))

            # 绘制该单词的所有现象
            for p in word_phenomena:
                row_index = phenom_to_row_map[p['name']]

                # 根据现象所在的行计算Y坐标
                y_pos_box = self.y_levels['phenomena_start'] - (row_index * ROW_HEIGHT)
                y_pos_details = y_pos_box - DETAILS_OFFSET

                color = self.config.PHENOMENON_COLORS.get(p["name"], "grey")
                name_short = p["name"].split(" ")[0]

                details_wrapped = self._wrap_text(p['details'], width=20)

                # 绘制现象名称标签
                self.fig.add_annotation(
                    x=x_center, y=y_pos_box, text=name_short,
                    showarrow=False, font=dict(color="white", size=self.config.FONT_SIZES['phenomenon_name']),
                    bgcolor=color, borderpad=5, bordercolor=color, borderwidth=1.5
                )
                # 绘制现象详细描述
                self.fig.add_annotation(
                    x=x_center, y=y_pos_details, text=details_wrapped,
                    showarrow=False, font=dict(color="dimgray", size=self.config.FONT_SIZES['phenomenon_details']),
                    align="center",
                    yanchor='top'  # 关键：让文本从指定Y坐标向下渲染，避免与下一行重叠
                )

        # 4. 返回创建的总行数，用于在主函数中调整图表整体高度
        num_rows = len(sorted_phenom_types)
        return num_rows

    # --- ^^^ 主要修改区域 ^^^ ---

    def _draw_spanning_annotations(self):
        """一个统一的函数，用于绘制所有跨词现象（连读，口语缩合）"""
        spanning_types = {
            "连读 (Linking)": {"y_level": self.y_levels['linking_box'], "title": "连读"},
            "口语缩合 (Contraction)": {"y_level": self.y_levels['contraction_box'], "title": "口语缩合"}
        }

        for phenom_full_name, properties in spanning_types.items():
            phenomena = self.data["phenomena_by_word"]
            processed_details = set()

            for i in range(len(self.word_positions)):
                for p in phenomena.get(i, []):
                    if phenom_full_name in p['name'] and p['details'] not in processed_details:
                        indices = self._get_indices_from_linking_detail(p['details'])
                        if not indices: continue

                        # 确保所有索引都在有效范围内
                        valid_indices = [idx for idx in indices if idx < len(self.word_positions)]
                        if len(valid_indices) < 1: continue

                        start_idx, end_idx = valid_indices[0], valid_indices[-1]
                        x0 = self.word_positions[start_idx]['start']
                        x1 = self.word_positions[end_idx]['end']
                        x_center = (x0 + x1) / 2

                        color = self.config.PHENOMENON_COLORS[phenom_full_name]
                        y_level = properties['y_level']

                        # 添加从每个相关单词到标签的连接线
                        for idx in valid_indices:
                            word_center_x = self.word_positions[idx]['center']
                            self.fig.add_shape(type="line",
                                               x0=word_center_x, y0=self.y_levels['sentence'] + 0.3,
                                               x1=word_center_x, y1=y_level - 0.3,
                                               line=dict(color="lightgrey", width=1.5))

                        # 绘制矩形背景
                        self.fig.add_shape(type="rect", x0=x0, y0=y_level - 0.3, x1=x1, y1=y_level + 0.3,
                                           line=dict(color=color, width=1.5), fillcolor=color, opacity=0.8,
                                           layer="below")

                        self.fig.add_annotation(x=x_center, y=y_level, text=f"<b>{properties['title']}</b>",
                                                showarrow=False,
                                                font=dict(color="white", size=self.config.FONT_SIZES['linking_title']))

                        # 详细描述自动换行
                        details_wrapped = self._wrap_text(p['details'], width=30)
                        self.fig.add_annotation(x=x_center, y=y_level + 0.7, text=details_wrapped,
                                                showarrow=False, font=dict(color="dimgray", size=self.config.FONT_SIZES[
                                'linking_details']), align="center")

                        processed_details.add(p['details'])

    def _get_indices_from_linking_detail(self, detail):
        """辅助函数，从描述中找出涉及的单词索引"""
        words = self.data["original_sentence"].split()
        involved_words_raw = re.findall(r"'([^']+)'", detail)
        involved_words = []
        for word_raw in involved_words_raw:
            involved_words.extend(word_raw.replace('‿', ' ').split())
        indices = []
        for word in set(involved_words):
            try:
                # 寻找所有匹配的词，而不仅仅是第一个
                indices.extend([i for i, s_word in enumerate(words) if s_word.lower() == word.lower()])
            except (ValueError, StopIteration):
                pass
        return sorted(list(set(indices)))


# --- Streamlit 主应用类 ---
# 负责构建应用的UI界面和处理用户交互。
class PhoneticsApp:
    def __init__(self):
        self.config = Config()
        st.set_page_config(page_title=self.config.PAGE_TITLE, page_icon=self.config.PAGE_ICON, layout="wide")

    def _inject_custom_css(self):
        """注入CSS以实现真正的全宽布局"""
        st.markdown("""
            <style>
                /* 覆盖Streamlit的默认样式，让主内容区域真正占满屏幕宽度 */
                .main .block-container {
                    max-width: 100%;
                    padding-left: 2rem;
                    padding-right: 2rem;
                    padding-top: 1rem;
                }
            </style>
        """, unsafe_allow_html=True)

    def run(self):
        self._inject_custom_css()  # 在应用开始时注入CSS

        st.title(self.config.PAGE_TITLE)
        st.markdown("""
        这是一个高级可视化版本，直接展示所有音变细节。如果句子太长，图表下方会出现滚动条。
        """)

        # UI元素：文本输入框
        sentence = st.text_input("1. 输入需要分析的句子", "What are you going to do about it?")

        if sentence:
            # UI元素：可折叠的提示词区域
            with st.expander("2. 点击这里查看并复制为AI生成的提示词"):
                prompt = self.config.PROMPT_TEMPLATE.format(sentence=sentence)
                st.code(prompt, language="markdown")

        # UI元素：文本区域，用于粘贴AI的输出
        markdown_input = st.text_area("3. 在此粘贴AI输出的Markdown格式答案", height=300,
                                      value="""### 1. 独立单词发音 (Strong Forms)
| Word | IPA (US) |
| :--- | :--- |
| What | /wʌt/ |
| are | /ɑːr/ |
| you | /juː/ |
| going | /ˈɡoʊ.ɪŋ/ |
| to | /tuː/ |
| do | /duː/ |
| about | /əˈbaʊt/ |
| it | /ɪt/ |

### 2. 日常口语发音 (Connected Speech)
**IPA:** /ˌwʌɾəjə ˈɡənə ˈduːwəˌbaʊɾɪt̚/

#### 音变现象解析
| 音变现象 | 在句中的体现 (音标变化) |
| :--- | :--- |
| **弱读 (Reduction)** | 'are' /ɑːr/ → /ə/； 'you' /juː/ → /jə/ |
| **连读 (Linking)** | 'about it' /əˈbaʊt ɪt/ |
| **失爆 (Incomplete Plosion)**| 'it' 的 /t/ 失去爆破 |
| **省略 (Elision)** | 未出现 |
| **同化 (Assimilation)**| 未出现 |
| **闪音/弹音 (Flapping)** | 'What are' /wʌt ɑːr/ → /wʌɾər/； 'about it' /əˈbaʊt ɪt/ → /əˈbaʊɾɪt/ |
| **口语缩合 (Contraction)** | 'going to' → 'gonna' /ˈɡənə/ |
""")

        # UI元素：主按钮
        if st.button("生成高级可视化图表", type="primary") and markdown_input and sentence:
            # 运行逻辑：解析 -> 生成图表 -> 显示
            with st.spinner("正在解析数据并生成高级图表..."):
                try:
                    parser = MarkdownParser(markdown_input, sentence)
                    parsed_data = parser.parse_all()

                    visualizer = PlotlyVisualizerV5(parsed_data, self.config)
                    fig = visualizer.generate_figure()

                    st.subheader("4. 可视化分析结果")
                    # 设置 use_container_width=False 以启用水平滚动
                    st.plotly_chart(fig, use_container_width=False)

                except ValueError as e:
                    st.error(f"解析失败: {e}")
                except Exception as e:
                    st.error(f"发生未知错误: {e}")


# 程序入口
if __name__ == "__main__":
    app = PhoneticsApp()
    app.run()