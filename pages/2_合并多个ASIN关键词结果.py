import streamlit as st
import pandas as pd
import re
from io import BytesIO
from typing import List, Dict, Tuple, Optional
from shared.sidebar import create_common_sidebar # <-- 1. 导入函数
create_common_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏


# --- 核心功能函数 (Core Logic Functions) ---

def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    从标准文件名中解析出ASIN等信息。
    文件名格式: ReverseASIN-US-B01N9KSITZ(1584)-20251012.xlsx

    Args:
        filename (str): 上传文件的名称。

    Returns:
        Optional[Dict[str, str]]: 包含'country'和'asin'的字典，如果格式不匹配则返回None。
    """
    # 使用正则表达式匹配文件名中的关键信息
    # - Group 1: (.*?) -> 国家代码 (e.g., US)
    # - Group 2: ([A-Z0-9]{10}) -> 10位字母和数字组成的ASIN (e.g., B01N9KSITZ)
    pattern = re.compile(r'ReverseASIN-(.*?)-([A-Z0-9]{10})\(.*\)-\d+')
    match = pattern.match(filename)

    if match:
        return {
            'country': match.group(1),
            'asin': match.group(2)
        }
    return None

def process_uploaded_file(uploaded_file) -> Optional[Tuple[str, pd.DataFrame, pd.DataFrame]]:
    """
    处理单个上传的Excel文件。
    1. 读取第一个sheet。
    2. 解析文件名获取ASIN。
    3. 创建一个新DataFrame，并在第一列添加ASIN信息。

    Args:
        uploaded_file: Streamlit上传的文件对象。

    Returns:
        Optional[Tuple[str, pd.DataFrame, pd.DataFrame]]:
        一个元组，包含:
        - 原始sheet的名称。
        - 原始sheet的完整DataFrame (用于单独存放)。
        - 添加了ASIN列的DataFrame (用于总表合并)。
        如果文件处理失败或文件名格式不正确，则返回None。
    """
    try:
        # 解析文件名
        file_info = parse_filename(uploaded_file.name)
        if not file_info:
            st.warning(f"文件名 '{uploaded_file.name}' 格式不符合要求，已跳过。")
            return None

        asin = file_info['asin']

        # 读取Excel的第一个sheet
        # `sheet_name=0` 表示读取第一个sheet
        # `engine='openpyxl'` 是为了更好地兼容.xlsx文件
        original_df = pd.read_excel(uploaded_file, sheet_name=0, engine='openpyxl')

        # 获取第一个sheet的名称，用于在新Excel中创建同名sheet
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet_name = xls.sheet_names[0]

        # 准备用于合并到总表的数据
        df_for_consolidation = original_df.copy()
        # 在第一列插入ASIN信息
        df_for_consolidation.insert(0, 'ASIN', asin)

        return sheet_name, original_df, df_for_consolidation

    except Exception as e:
        st.error(f"处理文件 '{uploaded_file.name}' 时出错: {e}")
        return None


def create_excel_file(individual_sheets: Dict[str, pd.DataFrame], consolidated_df: pd.DataFrame) -> BytesIO:
    """
    将处理好的数据写入一个新的Excel文件（在内存中）。

    Args:
        individual_sheets (Dict[str, pd.DataFrame]): 一个字典，键是sheet名，值是对应的原始DataFrame。
        consolidated_df (pd.DataFrame): 整合了所有ASIN信息的总表DataFrame。

    Returns:
        BytesIO: 包含新Excel文件内容的二进制流对象。
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. 写入总表，并将其放在第一个
        consolidated_df.to_excel(writer, sheet_name='总表-所有ASIN整合', index=False)

        # 2. 写入每个独立的ASIN sheet
        for sheet_name, df in individual_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # 重置指针到文件开头，以便st.download_button可以读取它
    output.seek(0)
    return output


# --- Streamlit 页面布局 (Streamlit UI) ---

def main():
    """
    Streamlit应用程序的主函数。
    """
    st.set_page_config(page_title="Excel 合并工具", layout="wide")
    st.title("📊 ASIN关键词反查报告合并工具")
    st.markdown("""
    **使用说明:**
    1.  点击下方的“Browse files”按钮，选择一个或多个符合命名规范的Excel文件。
    2.  文件命名规范: `ReverseASIN-国家代码-ASIN(关键词数量)-日期.xlsx` (例如: `ReverseASIN-US-B01N9KSITZ(1584)-20251012.xlsx`)
    3.  选择文件后，点击“开始合并”按钮。
    4.  处理完成后，下方会显示概括信息，并提供合并后文件的下载链接。
    """)

    # 1. 文件上传组件
    uploaded_files = st.file_uploader(
        "请上传需要合并的Excel文件",
        type=['xlsx'],
        accept_multiple_files=True
    )

    # 2. 合并按钮
    if st.button("🚀 开始合并", type="primary"):
        if uploaded_files:
            # 初始化用于存储数据的容器
            individual_sheets_data = {}  # key: sheet名, value: 原始DataFrame
            dfs_for_consolidation = []  # 用于存放所有添加了ASIN列的DataFrame

            # 使用进度条提升用户体验
            progress_bar = st.progress(0)
            total_files = len(uploaded_files)

            for i, uploaded_file in enumerate(uploaded_files):
                st.write(f"📄 正在处理文件: `{uploaded_file.name}`")
                result = process_uploaded_file(uploaded_file)

                if result:
                    sheet_name, original_df, df_with_asin = result
                    individual_sheets_data[sheet_name] = original_df
                    dfs_for_consolidation.append(df_with_asin)

                # 更新进度条
                progress_bar.progress((i + 1) / total_files)

            # 3. 如果成功处理了至少一个文件，则进行合并和生成
            if dfs_for_consolidation:
                # 使用concat合并所有DataFrame
                consolidated_df = pd.concat(dfs_for_consolidation, ignore_index=True)

                # 生成最终的Excel文件
                excel_bytes = create_excel_file(individual_sheets_data, consolidated_df)

                # 4. 输出概括性信息
                st.success("🎉 文件合并成功！")
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                col1.metric("合并文件总数", f"{len(individual_sheets_data)} 个")
                col2.metric("整合后总关键词行数", f"{len(consolidated_df)} 行")
                col3.metric("生成Sheet总数", f"{len(individual_sheets_data) + 1} 个")

                # 5. 提供下载按钮
                st.download_button(
                    label="📥 下载合并后的Excel文件",
                    data=excel_bytes,
                    file_name="Merged_ASIN_Keywords.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("没有成功处理任何文件，请检查上传文件的格式和内容。")
        else:
            # 如果用户没有上传文件就点击按钮
            st.warning("⚠️ 请先上传至少一个Excel文件。")


if __name__ == "__main__":
    main()