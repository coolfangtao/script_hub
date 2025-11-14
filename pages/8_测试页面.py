import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from pathlib import Path


def get_html_base64():
    """读取文件并返回 Base64 编码的字符串。"""
    # 获取HTML文件路径
    html_file_path = Path(__file__).parent.parent / "other" / "ai_calculator.html"

    if not html_file_path.exists():
        st.error(f"HTML文件不存在: {html_file_path}")
        return None

    try:
        # 以二进制方式读取文件，避免编码问题
        with open(html_file_path, 'rb') as f:
            html_bytes = f.read()

        # 直接使用base64编码二进制数据
        return base64.b64encode(html_bytes).decode()

    except Exception as e:
        st.error(f"读取文件时出错: {str(e)}")
        st.info("请检查文件编码或文件是否完整")
        return None


def main():
    st.set_page_config(
        page_title="ai模型计算器（点击跳转）",
        page_icon="🚀",
        layout="centered"
    )

    st.title("🚀 AI 模型计算器")

    # 1. 在 Session State 中存储 Base64 内容
    if 'html_base64' not in st.session_state:
        st.session_state['html_base64'] = get_html_base64()

    if st.session_state['html_base64'] is None:
        return  # 文件未找到或读取失败，退出

    # 2. 定义 JavaScript 函数 (不自动执行)
    # 注意：我们去掉了底部的 if (document.readyState === 'loading') { ... } 自动执行逻辑
    js_func_template = """
        <script>
        // *** 乱码修复的关键：将 Base64 解码为 Uint8Array ***
        function base64ToUint8Array(base64) {{
            const binary_string = atob(base64);
            const len = binary_string.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {{
                bytes[i] = binary_string.charCodeAt(i);
            }}
            return bytes;
        }}

        // 跳转函数，这次是手动触发
        function triggerRedirect(base64Content) {{
            try {{
                // 1. 解码 Base64 字符串为二进制数组
                const htmlUint8Array = base64ToUint8Array(base64Content);

                // 2. 创建 Blob 对象和 URL
                const blob = new Blob([htmlUint8Array], {{ type: 'text/html; charset=utf-8' }});
                const url = URL.createObjectURL(blob);

                // 3. 打开新窗口 (浏览器通常允许此操作，因为它是由用户点击触发的)
                const newWindow = window.open(url, '_blank');

                // 4. 检查是否打开成功
                if (newWindow) {{
                     // 清理 URL 对象 (在新窗口打开成功后，这里通常不太需要手动清理)
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                }} else {{
                    // 如果 newWindow 是 null 或 undefined，可能是被阻止了 (但在用户点击后很少发生)
                    alert('⚠️ 浏览器可能阻止了弹出窗口，请检查浏览器设置。');
                }}

            }} catch (error) {{
                console.error('跳转错误:', error);
                alert('❌ 打开页面时出错：' + error.message);
            }}
        }}

        // 外部函数，供 Python 调用
        window.streamlit_js_redirect = function() {{
            // 调用跳转函数，并传入 Base64 内容
            triggerRedirect("{base64_content}");
        }};

        // 立即执行 window.streamlit_js_redirect，因为 components.html 在渲染时就是一次性的点击
        window.streamlit_js_redirect();
        </script>
    """

    # 3. 定义一个函数，在按钮点击时调用
    # 3. 定义一个函数，在按钮点击时调用
    def redirect_on_click():
        """在 Streamlit 按钮点击时渲染带有执行脚本的 components.html"""

        # 增加计数器，确保每次点击都渲染新的组件 (通过改变 height 来避免缓存问题)
        # 注意：需要先增加计数器，才能用于 height 或 width 的计算
        st.session_state['redirect_count'] = st.session_state.get('redirect_count', 0) + 1
        current_count = st.session_state['redirect_count']

        # 渲染包含了 Base64 内容和自动执行逻辑的 JS
        js_to_execute = js_func_template.format(base64_content=st.session_state['html_base64'])

        # *** 关键修改：移除 key 参数，通过改变 height (使用计数器) 来强制重新渲染 ***
        # 使用 count 确保每次渲染的 height 都不同，从而绕过 Streamlit 的组件缓存
        # 我们使用一个极小的 height，例如 1 像素 + 计数器的模 100
        # 这样 height 变化很小，但能保证 Streamlit 认为它是一个新组件
        calculated_height = 1 + (current_count % 100)

        components.html(js_to_execute, height=calculated_height, width=0)

        # 这里不需要再设置 session state，因为已经在上面设置了
        # st.session_state['redirect_count'] = st.session_state.get('redirect_count', 0) + 1

    # 4. 创建按钮，点击时调用 redirect_on_click
    st.button(
        "🚀 在新窗口打开计算器",
        on_click=redirect_on_click,
        type="primary"
    )

    st.info("""
    **🚀 使用指南：**
    1.  本应用（AI 模型计算器）将以**独立新标签页**的形式运行，以保证最佳的使用体验。
    2.  请点击上方的 **“🚀 在新窗口打开计算器”** 按钮。
    3.  如果新窗口意外关闭，请直接**刷新本 Streamlit 页面 (F5)**，然后再次点击按钮即可重新打开。
    """)


if __name__ == "__main__":
    if 'redirect_count' not in st.session_state:
        st.session_state['redirect_count'] = 0
    main()