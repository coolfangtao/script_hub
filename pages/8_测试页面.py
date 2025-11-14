import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from pathlib import Path


def main():
    st.set_page_config(
        page_title="自动HTML跳转",
        page_icon="🚀",
        layout="centered"
    )

    st.title("🚀 HTML自动跳转")

    # 获取HTML文件路径
    html_file_path = Path(__file__).parent.parent / "other" / "ai_calculator.html"

    if not html_file_path.exists():
        st.error(f"HTML文件不存在: {html_file_path}")
        return

    # 读取HTML内容
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 将HTML内容编码为base64
    html_base64 = base64.b64encode(html_content.encode()).decode()

    # 自动跳转的JavaScript代码
    auto_redirect_js = f"""
    <script>
    // 创建blob URL
    const htmlContent = atob("{html_base64}");
    const blob = new Blob([htmlContent], {{ type: 'text/html' }});
    const url = URL.createObjectURL(blob);

    // 尝试自动打开新窗口
    const newWindow = window.open(url, '_blank');

    // 如果被阻止，显示手动打开链接
    if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {{
        document.getElementById('manualLink').style.display = 'block';
        document.getElementById('autoRedirectMessage').innerHTML = 
            '⚠️ 浏览器阻止了自动弹出窗口，请点击下方链接手动打开';
    }}
    </script>

    <div id="autoRedirectMessage" style="color: green; font-weight: bold;">
    🔄 正在尝试自动打开新页面...
    </div>

    <div id="manualLink" style="display: none; margin-top: 20px; padding: 10px; background: #f0f2f6; border-radius: 5px;">
    <p>请手动点击链接打开：</p>
    <a href="#" id="manualLinkAnchor" onclick="window.open(url, '_blank')">点击打开HTML页面</a>
    </div>

    <script>
    // 设置手动链接的URL
    document.getElementById('manualLinkAnchor').href = url;
    </script>
    """

    # 执行JavaScript
    components.html(auto_redirect_js, height=150)

    st.info("""
    **说明：**
    - 页面加载后将自动尝试在新标签页打开HTML文件
    - 如果浏览器阻止了弹出窗口，请允许该网站的弹出窗口
    - 或者使用上方显示的手动链接
    """)


if __name__ == "__main__":
    main()