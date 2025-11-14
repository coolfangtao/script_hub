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

    try:
        # 以二进制方式读取文件，避免编码问题
        with open(html_file_path, 'rb') as f:
            html_bytes = f.read()

        # 直接使用base64编码二进制数据，避免字符编码问题
        html_base64 = base64.b64encode(html_bytes).decode()

        # 自动跳转的JavaScript代码 - 修复版本
        auto_redirect_js = f"""
        <script>
        // 页面加载后执行跳转
        function redirectToHTML() {{
            try {{
                // 解码base64内容
                const htmlContent = atob("{html_base64}");
                // 创建blob URL
                const blob = new Blob([htmlContent], {{ type: 'text/html; charset=utf-8' }});
                const url = URL.createObjectURL(blob);

                // 尝试自动打开新窗口
                const newWindow = window.open(url, '_blank');

                // 检查是否打开成功
                if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {{
                    // 显示手动链接
                    document.getElementById('manualLink').style.display = 'block';
                    document.getElementById('autoRedirectMessage').innerHTML = 
                        '⚠️ 浏览器阻止了自动弹出窗口，请点击下方链接手动打开';
                    // 保存URL到全局变量供手动链接使用
                    window.htmlBlobUrl = url;
                }} else {{
                    document.getElementById('autoRedirectMessage').innerHTML = 
                        '✅ HTML页面已在新窗口打开！';
                    // 清理URL对象
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                }}
            }} catch (error) {{
                document.getElementById('autoRedirectMessage').innerHTML = 
                    '❌ 打开页面时出错：' + error.message;
                console.error('跳转错误:', error);
            }}
        }}

        // 手动打开函数
        function openManual() {{
            if (window.htmlBlobUrl) {{
                window.open(window.htmlBlobUrl, '_blank');
            }}
        }}

        // 页面加载完成后执行跳转
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', redirectToHTML);
        }} else {{
            redirectToHTML();
        }}
        </script>

        <div id="autoRedirectMessage" style="color: #0cce6b; font-weight: bold; margin: 10px 0;">
        🔄 正在尝试自动打开新页面...
        </div>

        <div id="manualLink" style="display: none; margin-top: 20px; padding: 15px; background: #1a1a1a; border-radius: 8px; border-left: 4px solid #ff6b6b;">
        <p style="margin: 0 0 10px 0; color: #ff6b6b;">⚠️ 浏览器阻止了自动弹出窗口</p>
        <button onclick="openManual()" style="background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
            点击手动打开HTML页面
        </button>
        </div>
        """

        # 执行JavaScript
        components.html(auto_redirect_js, height=200)

        # 添加重新打开按钮
        if st.button("🔄 重新尝试打开"):
            st.rerun()

        st.info("""
        **说明：**
        - 页面加载后将自动尝试在新标签页打开HTML文件
        - 如果浏览器阻止了弹出窗口，请允许该网站的弹出窗口
        - 或者使用上方显示的手动链接
        - 如果仍有问题，请检查浏览器是否阻止了弹出窗口
        """)

        # 调试信息（可选）
        with st.expander("🔧 调试信息"):
            st.write(f"文件路径: `{html_file_path}`")
            st.write(f"文件大小: {len(html_bytes)} 字节")
            st.write(f"Base64 长度: {len(html_base64)} 字符")

            # 显示文件前几行内容（用于调试）
            try:
                content_preview = html_bytes.decode('utf-8', errors='ignore')[:500]
                st.text_area("文件内容预览:", content_preview, height=150)
            except:
                st.write("无法预览文件内容")

    except Exception as e:
        st.error(f"读取文件时出错: {str(e)}")
        st.info("请检查文件编码或文件是否完整")


if __name__ == "__main__":
    main()