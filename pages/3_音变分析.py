import streamlit as st
import pandas as pd
import re
from io import StringIO
import plotly.graph_objects as go
import textwrap
from shared.sidebar import create_common_sidebar
create_common_sidebar()

# --- 配置类 ---
# 用于存放所有固定参数、模板和样式，方便统一管理和修改。
class Config:
    """存放所有配置参数和模板"""

    PAGE_TITLE = "英语音变可视化工具"
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
        "连读 (Linking)": "mediumseagreen",
        "失爆 (Incomplete Plosion)": "darkorange",
        "省略 (Elision)": "crimson",
        "同化 (Assimilation)": "teal",
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
class MarkdownParser:
    """解析AI输出的Markdown文本"""

    def __init__(self, markdown_text, sentence):
        self.text = markdown_text
        self.sentence_words = [word.strip(".,?!") for word in sentence.split()]
        if not self.text or not self.sentence_words:
            raise ValueError("Markdown文本和原始句子不能为空。")

    def parse_strong_forms(self):
        try:
            table_match = re.search(r"### 1\. 独立单词发音 \(Strong Forms\)\s*([\s\S]*?)\s*### 2\.", self.text)
            if not table_match: raise ValueError("未找到'独立单词发音'表格。")
            table_str = table_match.group(1).strip()
            df = pd.read_csv(StringIO(table_str), sep='|', skipinitialspace=True).dropna(axis=1, how='all').iloc[1:]
            df.columns = [col.strip() for col in df.columns]
            return {row['Word'].strip(): row['IPA (US)'].strip() for _, row in df.iterrows()}
        except Exception as e:
            raise ValueError(f"解析'独立单词发音'表格失败: {e}")

    def parse_connected_speech(self):
        try:
            match = re.search(r"\*\*IPA:\*\*\s*(.*)", self.text)
            return match.group(1).strip() if match else "未能解析"
        except Exception as e:
            raise ValueError(f"解析'日常口语发音'失败: {e}")

    def parse_phenomena_by_word(self):
        try:
            table_match = re.search(r"#### 音变现象解析\s*([\s\S]*)", self.text)
            if not table_match: raise ValueError("未找到'音变现象解析'表格。")
            table_str = table_match.group(1).strip()
            df = pd.read_csv(StringIO(table_str), sep='|', skipinitialspace=True).dropna(axis=1, how='all').iloc[1:]
            df.columns = [col.strip() for col in df.columns]
            phenomena_by_index = {i: [] for i in range(len(self.sentence_words))}
            for _, row in df.iterrows():
                phenomenon_name = row['音变现象'].replace('*', '').strip()
                details_full = row['在句中的体现 (音标变化)'].strip()
                if details_full != "未出现":
                    sub_details = re.split(r'[；;]', details_full)
                    for detail_part in sub_details:
                        detail_part = detail_part.strip()
                        if not detail_part: continue
                        involved_words_raw = re.findall(r"'([^']+)'", detail_part)
                        involved_words = []
                        for word_raw in involved_words_raw:
                            involved_words.extend(word_raw.replace('‿', ' ').split())
                        indices = []
                        unique_involved_words = sorted(list(set(involved_words)))
                        for word in unique_involved_words:
                            try:
                                for i, s_word in enumerate(self.sentence_words):
                                    if s_word.lower() == word.lower():
                                        indices.append(i)
                            except ValueError:
                                pass
                        for i in set(indices):
                            phenomena_by_index[i].append({"name": phenomenon_name, "details": detail_part})
            return phenomena_by_index
        except Exception as e:
            raise ValueError(f"解析'音变现象解析'表格失败: {e}")

    def parse_all(self):
        return {
            "original_sentence": " ".join(self.sentence_words),
            "strong_forms": self.parse_strong_forms(),
            "connected_ipa": self.parse_connected_speech(),
            "phenomena_by_word": self.parse_phenomena_by_word()
        }


# --- 可视化类 ---
class PlotlyVisualizerV5:
    """使用Plotly生成高级可视化图表（最终美化版）"""

    def __init__(self, data, config):
        self.data = data
        self.config = config
        self.fig = go.Figure()
        self.word_positions = []
        self.y_levels = {
            'contraction_box': 7.5,
            'linking_box': 6.0,
            'sentence': 5,
            'connected_ipa': 4,
            'strong_ipa': 3,
            'phenomena_start': 2.0
        }

    def _wrap_text(self, text, width=25):
        wrapped_lines = textwrap.wrap(text, width=width, break_long_words=False, replace_whitespace=False)
        return '<br>'.join(wrapped_lines)

    def generate_figure(self):
        words = self.data["original_sentence"].split()
        self._draw_text_rows_with_labels()
        num_phenom_rows = self._draw_phenomena_annotations()
        self._draw_spanning_annotations()
        fig_width = max(800, len(words) * 150)
        min_y_range = self.y_levels['phenomena_start'] - (num_phenom_rows * 2.2)
        self.fig.update_layout(
            width=fig_width,
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
        labels = ["原始句子", "日常口语发音", "独立发音"]
        y_coords = [self.y_levels['sentence'], self.y_levels['connected_ipa'], self.y_levels['strong_ipa']]
        for label, y in zip(labels, y_coords):
            self.fig.add_annotation(x=0, y=y, text=f"<b>{label}</b>", showarrow=False, xanchor='left',
                                    font_size=self.config.FONT_SIZES['row_label'], font_color='gray')
        words = self.data["original_sentence"].split()
        strong_forms = self.data["strong_forms"]
        current_x = 15.0
        for word in words:
            # 使用 .get() 并为 strip 提供默认值，以处理 strong_forms 中可能不存在的键
            ipa = strong_forms.get(word.strip(".,?!"), "")
            word_width = max(len(word) * 2.2, len(ipa) * 1.8) + 6
            x_center = current_x + word_width / 2
            self.fig.add_annotation(x=x_center, y=self.y_levels['sentence'], text=f"<b>{word}</b>", showarrow=False,
                                    font_size=self.config.FONT_SIZES['sentence'])
            self.fig.add_annotation(x=x_center, y=self.y_levels['strong_ipa'], text=ipa, showarrow=False,
                                    font_size=self.config.FONT_SIZES['ipa'], font_color="dimgray")
            self.word_positions.append({'start': current_x, 'center': x_center, 'end': current_x + word_width})
            current_x += word_width + 5
        if self.word_positions:
            sentence_start_x = self.word_positions[0]['start']
            sentence_end_x = self.word_positions[-1]['end']
            sentence_center_x = (sentence_start_x + sentence_end_x) / 2
            self.fig.add_annotation(x=sentence_center_x, y=self.y_levels['connected_ipa'],
                                    text=self.data['connected_ipa'],
                                    showarrow=False, xanchor='center',
                                    font_size=self.config.FONT_SIZES['connected_ipa'],
                                    font_color='royalblue')

    def _draw_phenomena_annotations(self):
        phenomena_by_word = self.data["phenomena_by_word"]
        ROW_HEIGHT = 2.2
        DETAILS_OFFSET = 0.6
        all_non_spanning_phenomena_names = set()
        for i in range(len(self.word_positions)):
            for p in phenomena_by_word.get(i, []):
                if "连读" not in p['name'] and "口语缩合" not in p['name']:
                    all_non_spanning_phenomena_names.add(p['name'])
        sorted_phenom_types = sorted(list(all_non_spanning_phenomena_names))
        phenom_to_row_map = {name: i for i, name in enumerate(sorted_phenom_types)}
        for i in range(len(self.word_positions)):
            x_center = self.word_positions[i]['center']
            word_phenomena = [p for p in phenomena_by_word.get(i, []) if p['name'] in phenom_to_row_map]
            if not word_phenomena:
                continue
            top_phenom_row = min([phenom_to_row_map[p['name']] for p in word_phenomena])
            line_y_start = self.y_levels['strong_ipa'] - 0.3
            line_y_end = self.y_levels['phenomena_start'] - (top_phenom_row * ROW_HEIGHT) + 0.35
            self.fig.add_shape(type="line", x0=x_center, y0=line_y_start, x1=x_center, y1=line_y_end,
                               line=dict(color="lightgrey", width=1.5))
            for p in word_phenomena:
                row_index = phenom_to_row_map[p['name']]
                y_pos_box = self.y_levels['phenomena_start'] - (row_index * ROW_HEIGHT)
                y_pos_details = y_pos_box - DETAILS_OFFSET
                color = self.config.PHENOMENON_COLORS.get(p["name"], "grey")
                name_short = p["name"].split(" ")[0]
                details_wrapped = self._wrap_text(p['details'], width=20)
                self.fig.add_annotation(
                    x=x_center, y=y_pos_box, text=name_short,
                    showarrow=False, font=dict(color="white", size=self.config.FONT_SIZES['phenomenon_name']),
                    bgcolor=color, borderpad=5, bordercolor=color, borderwidth=1.5
                )
                self.fig.add_annotation(
                    x=x_center, y=y_pos_details, text=details_wrapped,
                    showarrow=False, font=dict(color="dimgray", size=self.config.FONT_SIZES['phenomenon_details']),
                    align="center", yanchor='top'
                )
        return len(sorted_phenom_types)

    def _draw_spanning_annotations(self):
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
                        valid_indices = [idx for idx in indices if idx < len(self.word_positions)]
                        if len(valid_indices) < 1: continue
                        start_idx, end_idx = valid_indices[0], valid_indices[-1]
                        x0 = self.word_positions[start_idx]['start']
                        x1 = self.word_positions[end_idx]['end']
                        x_center = (x0 + x1) / 2
                        color = self.config.PHENOMENON_COLORS[phenom_full_name]
                        y_level = properties['y_level']
                        for idx in valid_indices:
                            word_center_x = self.word_positions[idx]['center']
                            self.fig.add_shape(type="line",
                                               x0=word_center_x, y0=self.y_levels['sentence'] + 0.3,
                                               x1=word_center_x, y1=y_level - 0.3,
                                               line=dict(color="lightgrey", width=1.5))
                        self.fig.add_shape(type="rect", x0=x0, y0=y_level - 0.3, x1=x1, y1=y_level + 0.3,
                                           line=dict(color=color, width=1.5), fillcolor=color, opacity=0.8,
                                           layer="below")
                        self.fig.add_annotation(x=x_center, y=y_level, text=f"<b>{properties['title']}</b>",
                                                showarrow=False,
                                                font=dict(color="white", size=self.config.FONT_SIZES['linking_title']))
                        details_wrapped = self._wrap_text(p['details'], width=30)
                        self.fig.add_annotation(x=x_center, y=y_level + 0.7, text=details_wrapped,
                                                showarrow=False, font=dict(color="dimgray", size=self.config.FONT_SIZES[
                                'linking_details']), align="center")
                        processed_details.add(p['details'])

    def _get_indices_from_linking_detail(self, detail):
        words = [word.strip(".,?!") for word in self.data["original_sentence"].split()]
        involved_words_raw = re.findall(r"'([^']+)'", detail)
        involved_words = []
        for word_raw in involved_words_raw:
            involved_words.extend(word_raw.replace('‿', ' ').split())
        indices = []
        for word in set(involved_words):
            try:
                indices.extend([i for i, s_word in enumerate(words) if s_word.lower() == word.lower()])
            except (ValueError, StopIteration):
                pass
        return sorted(list(set(indices)))


# --- Streamlit 主应用类 (已修改) ---
class PhoneticsApp:
    def __init__(self):
        self.config = Config()
        st.set_page_config(page_title=self.config.PAGE_TITLE, page_icon=self.config.PAGE_ICON, layout="wide")

    def _inject_custom_css(self):
        st.markdown("""
            <style>
                .main .block-container {
                    max-width: 100%;
                    padding-left: 2rem;
                    padding-right: 2rem;
                    padding-top: 1rem;
                }
            </style>
        """, unsafe_allow_html=True)

    def run(self):
        self._inject_custom_css()
        st.title(self.config.PAGE_TITLE)

        # 【修改】创建两个Tab
        tab1, tab2 = st.tabs(["📊 分析工具 (Analysis Tool)", "📖 使用指南 (Usage Guide)"])

        # --- Tab 1: 分析工具 ---
        with tab1:

            # 初始化会话状态
            if 'prompt_generated' not in st.session_state:
                st.session_state.prompt_generated = False
            if 'prompt' not in st.session_state:
                st.session_state.prompt = ""
            if 'sentence_for_prompt' not in st.session_state:
                st.session_state.sentence_for_prompt = ""

            # 步骤1: 输入句子
            sentence = st.text_input(
                "1. Step 1: 输入需要分析的句子",
                value="",
                placeholder="例如: What are you going to do about it?"
            )

            # 步骤2: 生成提示词按钮
            if st.button("生成提示词", type="primary", disabled=not sentence):
                st.session_state.prompt = self.config.PROMPT_TEMPLATE.format(sentence=sentence)
                st.session_state.prompt_generated = True
                st.session_state.sentence_for_prompt = sentence

            # 显示提示词
            if st.session_state.prompt_generated:
                with st.expander("2. 为AI生成的提示词 (点击右上角可复制)", expanded=True):
                    st.code(st.session_state.prompt, language="markdown", height=300)

            # 步骤3: 粘贴AI输出
            markdown_input = st.text_area(
                "3. Step 2: 在此粘贴AI输出的Markdown格式答案",
                height=300,
                value="",
                placeholder="请在此处粘贴AI返回的完整Markdown文本...",
                disabled=not st.session_state.prompt_generated
            )

            # 步骤4: 生成图表按钮
            if st.button(
                    "生成高级可视化图表",
                    type="primary",
                    disabled=not (st.session_state.prompt_generated and markdown_input)
            ):
                with st.spinner("正在解析数据并生成高级图表..."):
                    try:
                        parser = MarkdownParser(markdown_input, st.session_state.sentence_for_prompt)
                        parsed_data = parser.parse_all()
                        visualizer = PlotlyVisualizerV5(parsed_data, self.config)
                        fig = visualizer.generate_figure()
                        st.subheader("4. 可视化分析结果")
                        st.plotly_chart(fig, use_container_width=False)
                    except ValueError as e:
                        st.error(f"解析失败: {e}")
                    except Exception as e:
                        st.error(f"发生未知错误: {e}")

        # --- Tab 2: 使用指南 ---
        with tab2:
            st.subheader("🎯 工具用途")
            st.info("本工具旨在将语言模型（如 Gemini, ChatGPT 等）生成的文本格式音变分析，转换成直观、易于理解的可视化图表，帮助英语学习者更好地掌握连读、弱读、失爆等自然口语现象。")

            st.subheader("📝 操作流程")
            st.markdown("""
            **本工具的使用分为以下五个步骤，形成一个完整的工作流：**

            1.  **输入句子**:
                -   在 **分析工具** Tab 页的第一个输入框中，输入您想要分析的任何英文句子。

            2.  **生成提示词 (Prompt)**:
                -   点击“生成提示词”按钮。
                -   下方会自动出现一个为 AI 定制的、格式精确的提示词。这个提示词是确保 AI 能返回正确格式数据的关键。

            3.  **从 AI 获取分析**:
                -   复制生成的完整提示词。
                -   将它粘贴到您使用的任何大型语言模型（例如 Gemini, ChatGPT, DeepSeek等）的对话框中并发送。
                -   AI 将会返回一段包含多个 Markdown 表格的文本分析。

            4.  **粘贴 AI 的回答**:
                -   完整地复制(直接点击复制！不要鼠标刷选复制！) AI 返回的 Markdown 文本。
                -   回到本工具的 **分析工具** Tab 页，将其粘贴到标有“在此粘贴AI输出的Markdown格式答案”的文本区域中。

            5.  **生成图表**:
                -   点击“生成高级可视化图表”按钮。
                -   如果一切顺利，下方就会渲染出详细的音变分析图。
            """)

            st.subheader("💡 注意事项与技巧")
            st.warning("""
            - **提示词准确性**: 请务必使用本工具生成的、未经修改的提示词。提示词中的格式要求是解析器能够正确工作的保障。
            - **AI 输出格式错误**: 偶尔 AI 可能不会严格遵守格式要求。如果图表生成失败并提示“解析失败”，通常意味着 AI 返回的 Markdown 格式不正确。**最佳解决方法是：** 重新提交一次提示词，AI 通常在第二次就能生成正确的格式。
            - **发音标准**: 所有的音标分析都基于 **通用美式英语 (General American English)**。
            - **长句子**: 如果您分析的句子很长，生成的图表可能会超出屏幕宽度。您可以使用图表下方的水平滚动条来查看完整内容。
            """)


# 程序入口
if __name__ == "__main__":
    app = PhoneticsApp()
    app.run()