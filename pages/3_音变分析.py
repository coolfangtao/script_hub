import streamlit as st
import re
import plotly.graph_objects as go
import textwrap
import json  # 确保导入 json
from shared.sidebar import create_common_sidebar
create_common_sidebar(current_label="🎵 音变分析")

# --- 配置类---
class Config:
    """存放所有配置参数和模板"""

    PAGE_TITLE = "英语音变可视化工具"
    PAGE_ICON = "🌟"

    # 统一管理所有字体大小
    FONT_SIZES = {
        'row_label': 20,
        'sentence': 22,
        'ipa': 22,
        'connected_ipa': 22,
        'phenomenon_name': 18,
        'phenomenon_details': 16,
        'linking_title': 18,
        'linking_details': 16
    }

    # 统一管理所有字体颜色
    FONT_COLORS = {
        'row_label': '#555555',  # 用于 "原始句子" 等标签
        'strong_ipa': 'dimgray',  # 独立发音
        'connected_ipa': 'royalblue',  # 口语发音
        'phenom_details': 'dimgray'  # 现象详情
    }

    # 统一管理连接线颜色 (带透明度)
    LINE_COLOR = "rgba(211, 211, 211, 0.8)"

    # 美化配置
    SPANNING_BOX_OPACITY = 0.8   # 跨词框(连读)填充透明度
    SPANNING_BOX_LINE_WIDTH = 1.5  # 跨词框(连读)边框宽度

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

    # 跨词现象列表
    SPANNING_PHENOMENA_NAMES = ["连读 (Linking)", "口语缩合 (Contraction)"]

    # AI提示词模板 (V3)
    PROMPT_TEMPLATE = """
# Role
你是一位精通英语语音学的语言学专家。

# Task
你的任务是为用户提供的英文句子，进行详细的语音学分析。你需要提供每个单词的独立标准发音（强读式）、在自然口语流中的实际发音（连读式），并解释其中发生的关键音变现象。

# Constraints
1.  所有音标必须使用国际音标（IPA）。
2.  发音标准一律采用通用美式英语（General American English）。
3.  输出格式必须是一个严格的、单一的 JSON 对象。不要在 JSON 对象前后添加任何解释性文字或 Markdown 标记 (如 ```json ... ```)。
4.  JSON 对象的结构必须严格遵守下面【JSON Output Format】中定义的结构。
5.  在【phenomena_analysis】对象中：
    * `key` 必须是完整的现象名称。
    * `value` 必须是一个**数组 (array)**。
    * 如果某个现象未出现，其 `value` 必须是一个**空数组 `[]`**。
    * 如果某个现象出现，`value` 数组中必须包含一个或多个对象，每个对象代表一个实例。
    * 每个实例对象必须包含 `involved_words` (一个单词字符串数组) 和 `details` (一个解释字符串，最好用中文解释)。
    * 不要拆开任何缩略形式（如let's），让缩略形式成为involved_words。

# JSON Output Format
{{
  "strong_forms": [
    {{"word": "[单词1]", "ipa": "[IPA 1]"}},
    {{"word": "[单词2]", "ipa": "[IPA 2]"}},
    ...
  ],
  "connected_ipa": "[完整的口语IPA转写]",
  "phenomena_analysis": {{
    "弱读 (Reduction)": [
      {{"involved_words": ["[单词A]"], "details": "[关于单词A的弱读描述]"}},
      {{"involved_words": ["[单词B]"], "details": "[关于单词B的弱读描述]"}}
    ],
    "连读 (Linking)": [
      {{"involved_words": ["[单词C]", "[单词D]"], "details": "[关于单词C和D连读的描述, 包括连读前后的IPA注音]"}}
    ],
    "失爆 (Incomplete Plosion)": [
      {{"involved_words": ["[单词E]"], "details": "[关于单词E失爆的描述]"}}
    ],
    "省略 (Elision)": [],
    "同化 (Assimilation)": [],
    "闪音/弹音 (Flapping)": [
      {{"involved_words": ["[单词F]"], "details": "[关于单词F闪音的描述]"}}
    ],
    "口语缩合 (Contraction)": [
      {{"involved_words": ["[单词G]", "[单词H]"], "details": "[关于单词G和H缩合的描述]"}}
    ]
  }}
}}

## 示例
### Input Sentence:
What are you going to do about it?

### Expected JSON Output:
{{
  "strong_forms": [
    {{"word": "What", "ipa": "/wʌt/"}},
    {{"word": "are", "ipa": "/ɑːr/"}},
    {{"word": "you", "ipa": "/juː/"}},
    {{"word": "going", "ipa": "/ˈɡoʊ.ɪŋ/"}},
    {{"word": "to", "ipa": "/tuː/"}},
    {{"word": "do", "ipa": "/duː/"}},
    {{"word": "about", "ipa": "/əˈbaʊt/"}},
    {{"word": "it", "ipa": "/ɪt/"}}
  ],
  "connected_ipa": "/ˌwʌɾəjə ˈɡənə ˈduːwəˌbaʊɾɪt̚/",
  "phenomena_analysis": {{
    "弱读 (Reduction)": [
      {{"involved_words": ["are"], "details": "'are' /ɑːr/ → /ə/ "}},
      {{"involved_words": ["you"], "details": "'you' /juː/ → /jə/ "}}
    ],
    "连读 (Linking)": [
      {{"involved_words": ["do", "about"], "details": "'do‿about' 中间出现 /w/ 过渡音"}},
      {{"involved_words": ["What", "are", "you"], "details": "'What‿are‿you' 整体连接"}}
    ],
    "失爆 (Incomplete Plosion)": [
      {{"involved_words": ["it"], "details": "句末 'it' 的 /t/ 失去爆破，标记为 /t̚/，只做口型不送气"}}
    ],
    "省略 (Elision)": [
      {{"involved_words": ["What", "are"], "details": "'What are' /wʌt Sɑːr/ 中的 /r/ 在快速口语中可能被省略"}}
    ],
    "同化 (Assimilation)": [],
    "闪音/弹音 (Flapping)": [
      {{"involved_words": ["What"], "details": "'What' 的 /t/ → /ɾ/ "}},
      {{"involved_words": ["about", "it"], "details": "'about it' 的 /t/ → /ɾ/ "}}
    ],
    "口语缩合 (Contraction)": [
      {{"involved_words": ["going", "to"], "details": "'going to' → 'gonna' /ˈɡənə/"}}
    ]
  }}
}}

---
现在，请根据以上规则，为下面的句子生成分析：

**Input Sentence:**
{sentence}
"""


# --- 解析器类---
class JsonParser:
    """解析AI输出的JSON文本 (V6)"""

    def __init__(self, json_text, sentence, config):
        try:
            # 尝试去掉AI可能添加的Markdown代码块标记
            cleaned_text = re.sub(r"```json\n(.*?)\n```", r"\1", json_text, flags=re.DOTALL).strip()
            self.data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}. 请检查AI输出是否为严格的JSON格式。")

        # 存储原始单词列表（带标点），和清理后的单词列表
        self.raw_sentence_words = sentence.split()
        self.sentence_words = [word.strip(".,?!") for word in self.raw_sentence_words]
        self.config = config

        if not self.data or not self.sentence_words:
            raise ValueError("JSON数据和原始句子不能为空。")

    def parse_strong_forms(self):
        try:
            # 匹配 strong_forms 时，我们也应该匹配清理后的单词
            # AI 返回的 strong_forms 列表中的 'word' 键通常是不带标点的
            sf_map = {item['word'].strip().lower(): item['ipa'].strip() for item in self.data['strong_forms']}

            # 将AI的IPA映射回我们句子中带标点的原始单词
            final_sf_map = {}
            for i, clean_word in enumerate(self.sentence_words):
                raw_word_with_punctuation = self.raw_sentence_words[i]
                ipa = sf_map.get(clean_word.lower(), "")
                final_sf_map[raw_word_with_punctuation.strip(".,?!")] = ipa  # 最终可视化还是用无标点的词

            # 为了保险起见，将AI的原始映射也加入，以防句子拆分不一致
            for item in self.data['strong_forms']:
                word_clean = item['word'].strip()
                if word_clean not in final_sf_map:
                    final_sf_map[word_clean] = item['ipa'].strip()

            return final_sf_map

        except Exception as e:
            raise ValueError(f"解析 'strong_forms' JSON 数组失败: {e}")

    def parse_connected_speech(self):
        try:
            return self.data['connected_ipa'].strip()
        except KeyError:
            raise ValueError("在JSON中未找到 'connected_ipa' 键。")

    def _get_all_indices_for_words(self, involved_words_list):
        """
        辅助函数：找到所有匹配的单词索引 (用于非跨词现象)
        """
        indices = []
        for word in involved_words_list:
            for i, s_word in enumerate(self.sentence_words):
                if s_word.lower() == word.lower():
                    indices.append(i)
        return sorted(list(set(indices)))

    def _find_sequential_indices(self, involved_words_list):
        """
        辅助函数：找到 *连续* 匹配的单词序列索引 (用于跨词现象)
        """
        sub_list = [w.lower() for w in involved_words_list]
        main_list = [w.lower() for w in self.sentence_words]

        sub_len = len(sub_list)
        main_len = len(main_list)

        for i in range(main_len - sub_len + 1):
            # 检查从索引 i 开始的子列表是否匹配
            if main_list[i: i + sub_len] == sub_list:
                # 匹配成功，返回这个连续的索引列表
                return list(range(i, i + sub_len))

        # 遍历完成未找到匹配
        return []

    def parse_phenomena(self):
        """
        (V6)
        将现象分为三个桶:
        1. top_spanning_data: 连读/缩合，用于绘制在顶部
        2. bottom_single_word_data: 其他现象的单单词实例 (如弱读, 单个失爆)
        3. bottom_multi_word_data: 其他现象的多单词实例 (如 'hadn't explained' 失爆)
        """
        top_spanning_data = []
        bottom_single_word_data = {i: [] for i in range(len(self.sentence_words))}
        bottom_multi_word_data = []

        try:
            analysis_data = self.data['phenomena_analysis']
        except KeyError:
            raise ValueError("在JSON中未找到 'phenomena_analysis' 对象。")

        for phenomenon_name, instances in analysis_data.items():
            if not instances:
                continue

            for instance in instances:
                try:
                    involved_words_list = instance['involved_words']
                    details = instance['details']
                except KeyError as e:
                    st.warning(f"AI返回的JSON实例中缺少键: {e}，跳过此条目。")
                    continue

                # 检查这个现象是否属于 "顶部条"
                if phenomenon_name in self.config.SPANNING_PHENOMENA_NAMES:
                    # 1. 这是 "连读" 或 "口语缩合"
                    indices = self._find_sequential_indices(involved_words_list)

                    if not indices:
                        # 步骤 2: 查找失败, 尝试从 'details' 中提取缩合词 (e.g., "who'd")
                        contracted_word = None

                        # 尝试匹配 "→ 'gonna'" 这样的格式
                        match_arrow = re.search(r"→ '([^']+)'", details)
                        # 尝试匹配 "缩合为 'who'd'" 这样的格式
                        match_text = re.search(r"缩合为 '([^']+)'", details)

                        if match_arrow:
                            contracted_word = match_arrow.group(1)
                        elif match_text:
                            contracted_word = match_text.group(1)

                        if contracted_word:
                            # 步骤 3: 如果找到了缩合词, 就在句子中查找这个词
                            indices = self._find_sequential_indices([contracted_word.strip(".,?!")])

                    # 步骤 4: 在两次尝试后，再次检查
                    if not indices:
                        st.warning(f"无法在句子中定位序列: {involved_words_list} 或其缩合形式 (用于 {phenomenon_name})")
                        continue

                    top_spanning_data.append({
                        "name": phenomenon_name,
                        "indices": indices,
                        "details": details
                    })
                else:
                    # 2. 这是 "底部" 现象 (失爆, 弱读, etc.)
                    # 检查它是单单词还是多单词
                    if len(involved_words_list) > 1:
                        # 2a. 多单词 "底部" 现象
                        indices = self._find_sequential_indices(involved_words_list)
                        if not indices:
                            st.warning(f"无法在句子中定位 *连续* 序列: {involved_words_list} (用于 {phenomenon_name})")
                            continue
                        bottom_multi_word_data.append({  # 添加到新列表
                            "name": phenomenon_name,
                            "indices": indices,
                            "details": details
                        })
                    else:
                        # 2b. 单单词 "底部" 现象
                        indices = self._get_all_indices_for_words(involved_words_list)
                        if not indices:
                            st.warning(f"无法在句子中定位单词: {involved_words_list} (用于 {phenomenon_name})")
                            continue
                        for i in indices:
                            bottom_single_word_data[i].append({
                                "name": phenomenon_name,
                                "details": details
                            })

        return top_spanning_data, bottom_single_word_data, bottom_multi_word_data

    def parse_all(self):
        top_spanning, bottom_single, bottom_multi = self.parse_phenomena()
        original_sentence = " ".join(self.raw_sentence_words)

        return {
            "original_sentence": original_sentence,
            "strong_forms": self.parse_strong_forms(),
            "connected_ipa": self.parse_connected_speech(),
            "top_spanning_phenomena": top_spanning,
            "bottom_single_word_phenomena": bottom_single,
            "bottom_multi_word_phenomena": bottom_multi
        }


# --- 可视化类 ---
class PlotlyVisualizerV5:
    """使用Plotly生成高级可视化图表 (V5)"""

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

        # 绘制 "底部" 的所有现象 (方框和条)
        num_phenom_rows = self._draw_bottom_annotations()
        # 绘制 "顶部" 的连读/缩合
        self._draw_top_spanning_annotations()

        fig_width = max(800, len(words) * 150)
        min_y_range = self.y_levels['phenomena_start'] - (num_phenom_rows * 2.2) - 2.0

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
        labels = ["原始句子   ", "日常口语发音(IPA格式)   ", "独立发音(IPA格式)   "]
        y_coords = [self.y_levels['sentence'], self.y_levels['connected_ipa'], self.y_levels['strong_ipa']]
        for label, y in zip(labels, y_coords):
            self.fig.add_annotation(x=0, y=y, text=f"<b>{label}</b>", showarrow=False, xanchor='left',
                                    font_size=self.config.FONT_SIZES['row_label'],
                                    font_color=self.config.FONT_COLORS['row_label'])

        words = self.data["original_sentence"].split()
        strong_forms = self.data["strong_forms"]
        current_x = 30

        for word in words:
            ipa = strong_forms.get(word.strip(".,?!"), "")
            word_width = max(len(word) * 2.2, len(ipa) * 1.8) + 6
            x_center = current_x + word_width / 2

            self.fig.add_annotation(x=x_center, y=self.y_levels['sentence'], text=f"<b>{word}</b>", showarrow=False,
                                    font_size=self.config.FONT_SIZES['sentence'])

            self.fig.add_annotation(x=x_center, y=self.y_levels['strong_ipa'], text=ipa, showarrow=False,
                                    font_size=self.config.FONT_SIZES['ipa'],
                                    font_color=self.config.FONT_COLORS['strong_ipa'])

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
                                    font_color=self.config.FONT_COLORS['connected_ipa'])

    def _draw_bottom_annotations(self):
        """
        此方法现在绘制所有 "底部" 现象, 包括:
        1. 单单词实例 (如弱读) -> 绘制为 [方框]
        2. 多单词实例 (如失爆) -> 绘制为 [水平条]
        """
        single_word_data = self.data["bottom_single_word_phenomena"]
        multi_word_data = self.data["bottom_multi_word_phenomena"]

        ROW_HEIGHT = 2.2
        DETAILS_OFFSET = 0.6

        all_phenomena_names = set()
        for i in range(len(self.word_positions)):
            for p in single_word_data.get(i, []):
                all_phenomena_names.add(p['name'])
        for p in multi_word_data:
            all_phenomena_names.add(p['name'])

        sorted_phenom_types = sorted(list(all_phenomena_names))
        phenom_to_row_map = {name: i for i, name in enumerate(sorted_phenom_types)}

        line_y_start = self.y_levels['strong_ipa'] - 0.3

        # --- 添加追踪器以解决重叠问题 ---
        last_word_index_for_row = {}
        last_offset_used_for_row = {}
        # 定义一个垂直偏移量，用于错开相邻的同类现象
        ADJACENT_OFFSET = 1.0

        # --- 1. 绘制所有 "单单词" 实例 (方框) ---
        for i in range(len(self.word_positions)):
            x_center = self.word_positions[i]['center']
            word_phenomena = single_word_data.get(i, [])
            if not word_phenomena:
                continue

            for p in word_phenomena:
                row_index = phenom_to_row_map[p['name']]
                y_pos_box_base = self.y_levels['phenomena_start'] - (row_index * ROW_HEIGHT)

                # --- 解决相邻同类现象重叠 ---
                current_offset = 0.0
                last_used_idx = last_word_index_for_row.get(row_index, -99)
                last_offset = last_offset_used_for_row.get(row_index, 0.0)

                # 如果这个现象与前一个单词的 *同一个* 现象行相邻
                if i == last_used_idx + 1:
                    # 切换偏移量: 如果上一个是0, 这次就用OFFSET; 如果上次是OFFSET, 这次就用0
                    current_offset = ADJACENT_OFFSET if last_offset == 0.0 else 0.0

                y_pos_box = y_pos_box_base - current_offset
                y_pos_details = y_pos_box - DETAILS_OFFSET  # 详情自动跟随 y_pos_box 下移
                line_y_end_this_box = y_pos_box + 0.35  # 连接线也跟随下移

                color = self.config.PHENOMENON_COLORS.get(p["name"], "grey")
                name_short = p["name"].split(" ")[0]
                details_wrapped = self._wrap_text(p['details'], width=15)

                self.fig.add_shape(type="line",
                                   x0=x_center, y0=line_y_start,
                                   x1=x_center, y1=line_y_end_this_box,
                                   line=dict(color=self.config.LINE_COLOR, width=1.5, dash='dot'))

                self.fig.add_annotation(
                    x=x_center, y=y_pos_box, text=name_short,
                    showarrow=False,
                    font=dict(color="white", size=self.config.FONT_SIZES['phenomenon_name']),
                    bgcolor=color, borderpad=5, bordercolor=color, borderwidth=1.5
                )

                self.fig.add_annotation(
                    x=x_center, y=y_pos_details, text=details_wrapped,
                    showarrow=False,
                    font=dict(color=self.config.FONT_COLORS['phenom_details'],
                              size=self.config.FONT_SIZES['phenomenon_details']),
                    align="center", yanchor='top'
                )

                # --- 更新偏移追踪器 ---
                last_word_index_for_row[row_index] = i
                last_offset_used_for_row[row_index] = current_offset

        # --- 2. 绘制所有 "多单词" 实例 (水平条) ---
        for event in multi_word_data:
            phenom_full_name = event["name"]
            indices = event["indices"]
            details = event["details"]

            if phenom_full_name not in phenom_to_row_map:
                continue

            valid_indices = [idx for idx in indices if idx < len(self.word_positions)]
            if len(valid_indices) < 1:
                continue

            row_index = phenom_to_row_map[phenom_full_name]
            y_level = self.y_levels['phenomena_start'] - (row_index * ROW_HEIGHT)

            start_idx, end_idx = valid_indices[0], valid_indices[-1]
            x0 = self.word_positions[start_idx]['start']
            x1 = self.word_positions[end_idx]['end']
            x_center = (x0 + x1) / 2
            color = self.config.PHENOMENON_COLORS[phenom_full_name]

            # 绘制连接线 (从 ipa 行连接到条的顶部)
            for idx in valid_indices:
                word_center_x = self.word_positions[idx]['center']
                self.fig.add_shape(type="line",
                                   x0=word_center_x, y0=line_y_start,
                                   x1=word_center_x, y1=y_level + 0.35,  # 连接到条的顶部
                                   line=dict(color=self.config.LINE_COLOR, width=1.5, dash='dot'))

            # 绘制水平条
            self.fig.add_shape(type="rect",
                               x0=x0, y0=y_level - 0.3,
                               x1=x1, y1=y_level + 0.3,
                               line=dict(color=color, width=1.5),
                               fillcolor=color,
                               opacity=0.8,
                               layer="below")

            # 绘制条内文本
            name_short = phenom_full_name.split(" ")[0]
            self.fig.add_annotation(x=x_center, y=y_level, text=name_short,
                                    showarrow=False,
                                    font=dict(color="white", size=self.config.FONT_SIZES['phenomenon_name']),
                                    borderpad=3)

            # 绘制条下方的详细描述
            details_wrapped = self._wrap_text(details, width=30)  # 水平条可以有更宽的描述
            y_pos_details = y_level - DETAILS_OFFSET
            self.fig.add_annotation(x=x_center, y=y_pos_details, text=details_wrapped,
                                    showarrow=False,
                                    font=dict(color=self.config.FONT_COLORS['phenom_details'],
                                              size=self.config.FONT_SIZES['phenomenon_details']),
                                    align="center", yanchor='top')

        return len(sorted_phenom_types)  # 返回总行数

    def _draw_top_spanning_annotations(self):
        """
        !! 修改点: 此方法现在只绘制 "顶部" 现象 !!
        (原 _draw_spanning_annotations)
        """
        # 获取新的数据源
        spanning_events = self.data["top_spanning_phenomena"]

        y_levels_map = {
            "连读 (Linking)": {"y_level": self.y_levels['linking_box'], "title": "连读"},
            "口语缩合 (Contraction)": {"y_level": self.y_levels['contraction_box'], "title": "口语缩合"}
        }

        for event in spanning_events:
            phenom_full_name = event["name"]
            indices = event["indices"]
            details = event["details"]

            if (phenom_full_name not in y_levels_map) or (not indices):
                continue

            properties = y_levels_map[phenom_full_name]
            valid_indices = [idx for idx in indices if idx < len(self.word_positions)]
            if len(valid_indices) < 1:
                continue

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
                                   line=dict(color=self.config.LINE_COLOR, width=1.5, dash='solid'))

            self.fig.add_shape(type="rect",
                               x0=x0, y0=y_level - 0.3,
                               x1=x1, y1=y_level + 0.3,
                               line=dict(color=color, width=self.config.SPANNING_BOX_LINE_WIDTH),
                               fillcolor=color,
                               opacity=self.config.SPANNING_BOX_OPACITY,
                               layer="below")

            self.fig.add_annotation(x=x_center, y=y_level, text=f"<b>{properties['title']}</b>",
                                    showarrow=False,
                                    font=dict(color="white", size=self.config.FONT_SIZES['linking_title']),
                                    borderpad=3
                                    )

            details_wrapped = self._wrap_text(details, width=30)
            self.fig.add_annotation(x=x_center, y=y_level + 0.7, text=details_wrapped,
                                    showarrow=False,
                                    font=dict(color=self.config.FONT_COLORS['phenom_details'],
                                              size=self.config.FONT_SIZES['linking_details']),
                                    align="center")


# --- Streamlit 主应用类---
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

        tab1, tab2 = st.tabs(["📊 分析工具 (Analysis Tool)", "📖 使用指南 (Usage Guide)"])

        with tab1:
            if 'prompt_generated' not in st.session_state:
                st.session_state.prompt_generated = False
            if 'prompt' not in st.session_state:
                st.session_state.prompt = ""
            if 'sentence_for_prompt' not in st.session_state:
                st.session_state.sentence_for_prompt = ""

            sentence = st.text_input(
                "1. Step 1: 输入需要分析的句子（输入完成后点击输入框外即可点击按钮）",
                value="",
                placeholder="例如: What are you going to do about it?"
            )

            if st.button("生成提示词", type="primary", disabled=not sentence):
                st.session_state.prompt = self.config.PROMPT_TEMPLATE.format(sentence=sentence)
                st.session_state.prompt_generated = True
                st.session_state.sentence_for_prompt = sentence

            if st.session_state.prompt_generated:
                with st.expander("2. 为AI生成的提示词 (点击右上角可复制)", expanded=True):
                    # 提示词语言改为 json
                    st.code(st.session_state.prompt, language="json", height=300)

            # 提示文本修改
            json_input = st.text_area(
                "3. Step 2: 在此粘贴AI输出的JSON格式答案",
                height=300,
                value="",
                placeholder="请在此处粘贴AI返回的完整JSON文本...",
                disabled=not st.session_state.prompt_generated
            )

            if st.button(
                    "生成可视化图表",
                    type="primary",
                    disabled=not (st.session_state.prompt_generated and json_input)
            ):
                with st.spinner("正在解析数据并生成图表..."):
                    try:
                        # 调用 JsonParser 并传入 config
                        parser = JsonParser(json_input, st.session_state.sentence_for_prompt, self.config)
                        parsed_data = parser.parse_all()

                        visualizer = PlotlyVisualizerV5(parsed_data, self.config)
                        fig = visualizer.generate_figure()

                        st.subheader("4. 可视化分析结果")
                        st.plotly_chart(fig, use_container_width=False)

                    except ValueError as e:
                        st.error(f"解析失败: {e}")
                    except Exception as e:
                        st.error(f"发生未知错误: {e}", icon="🚨")

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
                -   下方会自动出现一个为 AI 定制的、格式精确的 **JSON 提示词**。

            3.  **从 AI 获取分析**:
                -   复制生成的完整提示词。
                -   将它粘贴到您使用的任何大型语言模型（例如 Gemini, ChatGPT, DeepSeek等）的对话框中并发送。
                -   AI 将会返回一段 **JSON 格式的文本**。

            4.  **粘贴 AI 的回答**:
                -   完整地复制 AI 返回的 JSON 文本 (通常以 `{` 开始，以 `}` 结束)。
                -   回到本工具的 **分析工具** Tab 页，将其粘贴到标有“在此粘贴AI输出的JSON格式答案”的文本区域中。

            5.  **生成图表**:
                -   点击“生成可视化图表”按钮。
                -   下方就会渲染出详细的音变分析图。
            """)

            st.subheader("💡 注意事项与技巧")
            st.warning("""
            - **提示词准确性**: 请务必使用本工具生成的、未经修改的提示词。提示词中的 JSON 格式要求是解析器能够正确工作的保障。
            - **AI 输出格式错误**: 偶尔 AI 可能不会严格遵守格式要求（例如，在 JSON 之前或之后添加了额外的说明文字）。如果图表生成失败并提示“解析失败”，**最佳解决方法是：** 重新提交一次提示词，AI 通常在第二次就能生成正确的格式。
            - **发音标准**: 所有的音标分析都基于 **通用美式英语 (General American English)**。
            - **长句子**: 如果您分析的句子很长，生成的图表可能会超出屏幕宽度。您可以使用图表下方的水平滚动条来查看完整内容。
            """)


# 程序入口
if __name__ == "__main__":
    app = PhoneticsApp()
    app.run()