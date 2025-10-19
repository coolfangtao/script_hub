import streamlit as st
import re

from shared.sidebar import create_sidebar # <-- 1. 导入函数
create_sidebar() # <-- 2. 调用函数，确保每个页面都有侧边栏

# Main title of the application
st.title("📌 B站标题提取工具")

# --- Page Navigation (as in original code) ---
# This button is for navigating in a multi-page app.
# In a single-file app, it won't switch pages but we keep it as requested.
if st.button("← 返回主页"):
    # In a real multi-page app, this would be: st.switch_page("streamlit_app.py")
    # For this single file app, we can just show a message.
    st.info("这是一个单页面应用。在多页面应用中，此按钮将带您返回主页。")
    st.switch_page("streamlit_app.py")

# --- HTML Input Area ---
st.header("1. 在下方文本框中粘贴 HTML 内容")
html_input = st.text_area(
    "在此处粘贴内容...",
    height=250,
    label_visibility="collapsed" # Hides the label "在此处粘贴内容..." for a cleaner look
)

# --- Extraction and Display Logic ---
if st.button("提取标题", type="primary"):
    if html_input:
        # Use regex to find all occurrences of title="..."
        titles = re.findall(r'title="([^"]+)"', html_input)

        if titles:
            st.header("2. 提取结果")
            # Join all found titles with a newline character
            result_text = "\n".join(titles)

            # Display the results in a code block. Streamlit's code block
            # has a built-in copy icon in the top-right corner.
            st.code(result_text, language='text')

            st.success(f"成功提取了 {len(titles)} 个标题！点击上方结果框右上角的图标即可复制。")

        else:
            # Show a warning if no titles were found
            st.warning("未找到任何匹配 `title=\"...\"` 格式的标题。请检查您的 HTML 内容。")
    else:
        # Show an error if the text area is empty
        st.error("文本框为空，请输入 HTML 内容后再试。")
