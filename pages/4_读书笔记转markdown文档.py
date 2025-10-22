import streamlit as st
import re
import os
from datetime import datetime
from typing import List, Tuple, Dict
from shared.sidebar import create_common_sidebar  # 导入公共侧边栏函数
create_common_sidebar()


def remove_suffix(text):
    """
    从多行文本中去除尾缀

    参数:
        text: 多行文本字符串

    返回:
        去除尾缀后的文本字符串
    """
    if not text:
        return ""

    # 按行分割文本
    lines = text.splitlines()

    # 找到最后一个非空行的索引
    last_non_empty_index = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():  # 检查行是否非空（去除空白字符后）
            last_non_empty_index = i
            break

    # 如果没有找到非空行，返回空字符串
    if last_non_empty_index == -1:
        return ""

    # 保留从开始到最后一个非空行之前的所有行
    # 注意：最后一个非空行本身也要删除，因为它是尾缀
    result_lines = lines[:last_non_empty_index]

    # 将结果行重新组合成字符串
    return '\n'.join(result_lines)


def extract_book_title(text):
    """
    从多行文本中提取书名

    参数:
    text (str): 多行文本

    返回:
    tuple: (书名, 剩余文本)
    """
    lines = text.splitlines()

    # 找到第一个非空行
    title_line = None
    title_index = -1

    for i, line in enumerate(lines):
        if line.strip():  # 如果不是空行
            title_line = line.strip()
            title_index = i
            break

    # 如果没有找到非空行，返回空字符串
    if title_line is None:
        return "", ""

    # 删除书名行及之前的所有行，保留剩余行
    remaining_lines = lines[title_index + 1:]
    remaining_text = "\n".join(remaining_lines)

    return title_line, remaining_text


def extract_author_name(text):
    """
    从多行文本中提取作者名

    参数:
    text (str): 多行文本

    返回:
    tuple: (作者名, 剩余文本)
    """
    lines = text.splitlines()

    # 找到第一个非空行
    author_name = ""
    author_index = -1

    for i, line in enumerate(lines):
        if line.strip():  # 如果不是空行
            author_name = line.strip()
            author_index = i
            break

    # 如果没有找到非空行，返回空字符串
    if author_index == -1:
        return "", ""

    # 删除作者名行及之前的所有行，保留剩余行
    remaining_lines = lines[author_index + 1:]
    remaining_text = "\n".join(remaining_lines)

    return author_name, remaining_text


def extract_note_count(text):
    """
    从多行文本中提取笔记数

    参数:
    text (str): 多行文本

    返回:
    tuple: (笔记数, 剩余文本)
    """
    lines = text.splitlines()

    # 找到第一个非空行
    note_count = ""
    note_index = -1

    for i, line in enumerate(lines):
        if line.strip():  # 如果不是空行
            note_count = line.strip()
            note_index = i
            break

    # 如果没有找到非空行，返回空字符串
    if note_index == -1:
        return "", ""

    # 删除笔记数行及之前的所有行，保留剩余行
    remaining_lines = lines[note_index + 1:]
    remaining_text = "\n".join(remaining_lines)

    return note_count, remaining_text


def extract_titles(text):
    """
    从多行文本中提取标题

    参数:
    text (str): 多行文本

    返回:
    tuple: (标题列表, 剩余文本)
    """
    lines = text.splitlines()

    # 1. 去除最前面的所有空白行
    start_index = 0
    for i, line in enumerate(lines):
        if line.strip():  # 找到第一个非空行
            start_index = i
            break
    else:
        # 如果所有行都是空白行，返回空结果
        return [], text

    # 保留从第一个非空行开始的所有行
    processed_lines = lines[start_index:]

    # 2. 在最前面加入两个空白行
    processed_lines = ['', ''] + processed_lines

    # 3. 提取标题行（不以字符◆开头，且前面有两个空白行的行）
    titles = []
    remaining_lines = []
    i = 0

    while i < len(processed_lines):
        # 检查当前行是否是标题行
        if (i + 2 < len(processed_lines) and
                not processed_lines[i].strip() and
                not processed_lines[i + 1].strip() and
                processed_lines[i + 2].strip() and
                not processed_lines[i + 2].startswith('◆')):

            # 找到标题行
            title_line = processed_lines[i + 2]
            titles.append(title_line.strip())

            # 跳过这个标题块（两个空白行 + 标题行）
            i += 3
        else:
            # 不是标题行，保留到剩余文本
            remaining_lines.append(processed_lines[i])
            i += 1

    # 将剩余行转换回字符串
    remaining_text = '\n'.join(remaining_lines)

    return titles, remaining_text


def remove_empty_lines(text):
    """
    去除字符串中的所有空白行

    参数:
    text (str): 多行文本

    返回:
    str: 去除所有空白行后的文本
    """
    lines = text.splitlines()

    # 过滤掉所有空白行
    non_empty_lines = [line for line in lines if line.strip()]

    # 重新组合成字符串
    return '\n'.join(non_empty_lines)


def split_notes_preserve_format(text, symbol='◆'):
    """
    按照指定符号分割字符串（保留格式版本）
    每个笔记包含其原始格式，包括换行符

    参数:
    text (str): 多行文本
    symbol (str): 分割符号，默认为'◆'

    返回:
    list: 分割后的笔记列表
    """
    if not text.strip():
        return []

    # 使用符号进行分割，但保留换行符
    parts = text.split(symbol)

    # 处理第一个部分
    notes = []
    if parts and parts[0].strip():
        # 如果第一个部分有内容，且不是以符号开头，可以单独处理或忽略
        pass

    # 为剩余部分添加符号
    for i, part in enumerate(parts[1:], 1):
        if part.strip():  # 只处理非空部分
            note = symbol + part
            notes.append(note)

    return notes


# 新增函数：解析单条笔记
def parse_single_note(note: str) -> Dict:
    """
    解析单条笔记的内容和类型

    参数:
        note: 单条笔记字符串

    返回:
        dict: 包含笔记信息的字典
    """
    note_info = {
        'type': 'unknown',
        'content': '',
        'original_text': '',
        'thought': '',
        'date': '',
        'tags': []
    }

    lines = note.strip().split('\n')

    # 检查笔记类型
    if note.startswith('◆ '):
        # 形式1: 只有划线内容
        if '发表想法' not in note:
            note_info['type'] = 'highlight'
            note_info['content'] = note.replace('◆ ', '').strip()
        # 形式2: 有想法和原文
        else:
            note_info['type'] = 'thought'
            # 提取日期
            date_match = re.search(r'◆ (\d{4}/\d{2}/\d{2})发表想法', note)
            if date_match:
                note_info['date'] = date_match.group(1)

            # 分离想法和原文
            thought_parts = note.split('原文：')
            if len(thought_parts) == 2:
                # 提取想法部分（去掉第一行的日期信息）
                thought_lines = thought_parts[0].split('\n')[1:]  # 跳过第一行
                note_info['thought'] = '\n'.join([line.strip() for line in thought_lines if line.strip()])
                note_info['original_text'] = thought_parts[1].strip()

    # 检测标签
    tag_patterns = {
        'Q': r'^Q\s+(.+)',
        'A': r'^A\s+(.+)',
        'C': r'^C\s+(.+)',
        'G': r'^G\s+(.+)',
        'TODO': r'^TODO\s+(.+)',
        'TODO-Q': r'^TODO-Q\s+(.+)'
    }

    for tag, pattern in tag_patterns.items():
        if re.search(pattern, note_info.get('thought', ''), re.MULTILINE) or \
                re.search(pattern, note_info.get('content', ''), re.MULTILINE):
            note_info['tags'].append(tag)

    return note_info


# 新增函数：提取所有概念
def extract_concepts(notes: List[Dict]) -> Dict[str, str]:
    """
    从笔记中提取所有概念及其解释

    参数:
        notes: 笔记列表

    返回:
        dict: 概念到解释的映射
    """
    concepts = {}
    concept_pattern = r'^C\s+(.+?)(?:\n|$)((?:\n(?!\n).*)*)'

    for note in notes:
        # 在想法中查找概念
        if note['thought']:
            matches = re.findall(concept_pattern, note['thought'], re.MULTILINE)
            for match in matches:
                concept = match[0].strip()
                explanation = match[1].strip() if match[1].strip() else concept
                concepts[concept] = explanation

        # 在内容中查找概念
        if note['content']:
            matches = re.findall(concept_pattern, note['content'], re.MULTILINE)
            for match in matches:
                concept = match[0].strip()
                explanation = match[1].strip() if match[1].strip() else concept
                concepts[concept] = explanation

    return concepts


# 新增函数：生成Markdown内容
def generate_markdown(book_title: str, author_name: str, notes: List[Dict], concepts: Dict[str, str]) -> str:
    """
    生成完整的Markdown文档

    参数:
        book_title: 书名
        author_name: 作者名
        notes: 笔记列表
        concepts: 概念字典

    返回:
        str: Markdown格式的文档内容
    """
    # 文档头部
    md_content = f"""# {book_title}

**作者**: {author_name}  
**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**笔记数量**: {len(notes)}

---

## 📝 读书笔记

"""

    # 处理每条笔记
    footnote_counter = 1
    concept_footnotes = {}
    question_footnotes = {}

    for i, note in enumerate(notes, 1):
        md_content += f"### 笔记 {i}\n\n"

        if note['date']:
            md_content += f"**记录时间**: {note['date']}\n\n"

        # 处理原文内容
        if note['original_text']:
            md_content += f"**原文**: {note['original_text']}\n\n"

        # 处理想法内容
        if note['thought']:
            thought_content = note['thought']

            # 处理Q/A对
            qa_pattern = r'Q\s+(.+?)\nA\s+(.+)'
            qa_matches = re.findall(qa_pattern, thought_content, re.DOTALL)
            for question, answer in qa_matches:
                question_footnotes[question.strip()] = answer.strip()
                thought_content = thought_content.replace(
                    f"Q {question}\nA {answer}",
                    f"<span title='{answer.strip()}'>Q: {question.strip()}[^{footnote_counter}]</span>"
                )
                footnote_counter += 1

            # 处理概念
            c_pattern = r'C\s+(.+?)(?:\n|$)'
            c_matches = re.findall(c_pattern, thought_content)
            for concept in c_matches:
                concept = concept.strip()
                if concept in concepts:
                    concept_footnotes[concept] = concepts[concept]
                    thought_content = re.sub(
                        f'C\\s+{re.escape(concept)}',
                        f"<span title='{concepts[concept]}'>C: {concept}[^{footnote_counter}]</span>",
                        thought_content
                    )
                    footnote_counter += 1

            # 处理TODO
            thought_content = re.sub(r'TODO\s+(.+)', r'- [ ] \1', thought_content)
            thought_content = re.sub(r'TODO-Q\s+(.+)', r'- [ ] Q: \1', thought_content)

            # 处理G标记
            thought_content = re.sub(r'G\s+(.+)', r'🌟 \1', thought_content)

            md_content += f"**想法**:\n{thought_content}\n\n"

        elif note['content']:
            content = note['content']
            # 对纯内容也进行标签处理
            content = re.sub(r'TODO\s+(.+)', r'- [ ] \1', content)
            content = re.sub(r'G\s+(.+)', r'🌟 \1', content)
            md_content += f"{content}\n\n"

        md_content += "---\n\n"

    # 添加脚注
    if question_footnotes or concept_footnotes:
        md_content += "## 📌 注释\n\n"

        counter = 1
        for question, answer in question_footnotes.items():
            md_content += f"[^{counter}]: **Q**: {question}\n    **A**: {answer}\n\n"
            counter += 1

        for concept, explanation in concept_footnotes.items():
            md_content += f"[^{counter}]: **概念**: {concept}\n    **解释**: {explanation}\n\n"
            counter += 1

    # 添加术语表
    if concepts:
        md_content += "## 📚 术语表\n\n"
        for concept, explanation in sorted(concepts.items()):
            md_content += f"### {concept}\n{explanation}\n\n"

    return md_content


# 新增函数：处理上传的文本
def process_wechat_notes(text: str) -> Tuple[str, str, str]:
    """
    处理微信读书笔记文本并生成Markdown

    参数:
        text: 原始文本

    返回:
        tuple: (markdown内容, 文件名, 书籍信息)
    """
    try:
        # 使用你提供的函数处理文本
        remaining_text = remove_suffix(text)
        book_title, remaining_text = extract_book_title(remaining_text)
        author_name, remaining_text = extract_author_name(remaining_text)
        note_num, remaining_text = extract_note_count(remaining_text)
        titles, remaining_text = extract_titles(remaining_text)
        remaining_text = remove_empty_lines(remaining_text)
        notes_list = split_notes_preserve_format(remaining_text)

        # 解析每条笔记
        parsed_notes = [parse_single_note(note) for note in notes_list]

        # 提取概念
        concepts = extract_concepts(parsed_notes)

        # 生成Markdown
        markdown_content = generate_markdown(book_title, author_name, parsed_notes, concepts)

        # 生成文件名
        filename = f"{book_title}_{author_name}_读书笔记.md".replace(' ', '_').replace('/', '_')

        book_info = f"《{book_title}》 - {author_name} - {note_num}"

        return markdown_content, filename, book_info

    except Exception as e:
        st.error(f"处理过程中出现错误: {str(e)}")
        return "", "", ""


# Streamlit界面
def main():
    """主函数：构建Streamlit界面"""
    st.set_page_config(
        page_title="微信读书笔记整理工具",
        page_icon="📚",
        layout="wide"
    )

    # 页面标题和说明
    st.title("📚 微信读书笔记整理工具")
    st.markdown("""
    这个工具可以帮助你整理微信读书导出的笔记，并将其转换为格式优美的Markdown文档。

    ### 使用方法：
    1. 在微信读书中导出笔记到剪贴板
    2. 将内容粘贴到下方的文本区域
    3. 点击"生成Markdown文档"按钮
    4. 下载生成的文档

    ### 支持的标签：
    - **Q/A**: 问题和答案
    - **C**: 概念和术语  
    - **G**: 好的句子或想法
    - **TODO**: 待办事项
    - **TODO-Q**: 未解决的问题
    """)

    # 文本输入区域
    st.subheader("📝 粘贴微信读书笔记")
    input_text = st.text_area(
        "请将微信读书导出的笔记内容粘贴到这里：",
        height=300,
        placeholder="粘贴你的微信读书笔记内容到这里..."
    )

    # 处理按钮
    if st.button("🚀 生成Markdown文档", type="primary"):
        if not input_text.strip():
            st.warning("请先粘贴微信读书笔记内容！")
            return

        with st.spinner("正在处理笔记，请稍候..."):
            markdown_content, filename, book_info = process_wechat_notes(input_text)

            if markdown_content:
                st.success(f"✅ 成功处理 {book_info}")

                # 显示预览
                st.subheader("📖 文档预览")
                with st.expander("点击查看Markdown预览", expanded=True):
                    st.markdown(markdown_content)

                # 下载按钮
                st.subheader("📥 下载文档")
                st.download_button(
                    label="下载Markdown文档",
                    data=markdown_content,
                    file_name=filename,
                    mime="text/markdown",
                    icon="📄"
                )

                # 显示统计信息
                st.subheader("📊 统计信息")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("笔记数量", len(markdown_content.split("### 笔记")) - 1)
                with col2:
                    concept_count = len(re.findall(r'C:\s+', markdown_content))
                    st.metric("概念数量", concept_count)
                with col3:
                    question_count = len(re.findall(r'Q:\s+', markdown_content))
                    st.metric("问题数量", question_count)


if __name__ == "__main__":
    main()