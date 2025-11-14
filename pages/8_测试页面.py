import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from pathlib import Path


def main():
    st.set_page_config(
        page_title="ai模型计算器（自动跳转）",
        page_icon="🚀",
        layout="centered"
    )

    st.title("🚀 ai模型计算器")

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

        # 自动跳转的JavaScript代码 - 增强用户指导
        auto_redirect_js = f"""
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

                // 手动打开函数：当自动跳转被阻止时，用户点击此按钮
                function openManual() {{
                    if (window.htmlBlobUrl) {{
                        // 打开新窗口，使用户可以点击
                        window.open(window.htmlBlobUrl, '_blank');
                    }} else {{
                        document.getElementById('manualLinkMessage').innerHTML = 
                            '<p style="color: #ff6b6b;">❌ 无法获取页面链接，请尝试刷新页面。</p>';
                    }}
                }}


                // 页面加载后执行跳转
                function redirectToHTML() {{
                    try {{
                        // 1. 解码 Base64 字符串为二进制数组
                        const htmlUint8Array = base64ToUint8Array("{html_base64}");

                        // 2. 创建 Blob 对象和 URL
                        const blob = new Blob([htmlUint8Array], {{ type: 'text/html; charset=utf-8' }});
                        const url = URL.createObjectURL(blob);
                        window.htmlBlobUrl = url; // 保存 URL 供手动打开使用

                        // 3. 尝试自动打开新窗口
                        const newWindow = window.open(url, '_blank');

                        // 4. 检查是否打开成功
                        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {{
                            // 自动打开失败：显示手动链接/按钮
                            document.getElementById('manualLinkContainer').style.display = 'block';
                            document.getElementById('autoRedirectMessage').innerHTML = 
                                '⚠️ **自动跳转失败**：浏览器阻止了弹出窗口。';
                        }} else {{
                            // 自动打开成功
                            document.getElementById('autoRedirectMessage').innerHTML = 
                                '✅ HTML页面已在新窗口打开！';
                            // 清理 URL 对象
                            setTimeout(() => URL.revokeObjectURL(url), 1000);
                        }}

                    }} catch (error) {{
                        document.getElementById('autoRedirectMessage').innerHTML = 
                            '❌ 打开页面时出错：' + error.message;
                        console.error('跳转错误:', error);
                        // 出错时也显示手动链接
                        document.getElementById('manualLinkContainer').style.display = 'block';
                    }}
                }}

                // 确保页面加载完成后执行跳转
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', redirectToHTML);
                }} else {{
                    redirectToHTML();
                }}
                </script>

                <div id="autoRedirectMessage" style="color: #0cce6b; font-weight: bold; margin: 10px 0;">
                🔄 正在尝试自动打开新页面...
                </div>

                <div id="manualLinkContainer" style="display: none; margin-top: 20px; padding: 15px; background: #1a1a1a; border-radius: 8px; border-left: 4px solid #ff6b6b;">
                    <div id="manualLinkMessage" style="margin-bottom: 15px;">
                        <p style="margin: 0 0 5px 0; color: #ff6b6b; font-weight: bold;">🚨 浏览器阻止了自动弹出窗口！</p>
                        <p style="margin: 0; font-size: 0.9em; color: #aaaaaa;">
                            请执行以下操作之一：
                        </p>
                        <ol style="margin: 5px 0 0 20px; padding: 0; font-size: 0.9em; color: #aaaaaa;">
                            <li>点击下方的按钮 **手动打开** 页面。</li>
                            <li>允许本网站的 **弹出窗口** (在地址栏末尾查看阻止图标)。</li>
                            <li>然后点击页面底部的 **重新尝试打开** 按钮。</li>
                        </ol>
                    </div>

                    <button onclick="openManual()" style="background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                        点击手动打开HTML页面
                    </button>
                </div>
                """

        # 执行JavaScript
        components.html(auto_redirect_js, height=10)

        # 添加重新打开按钮
        if st.button("🔄 重新尝试打开"):
            st.rerun()

        st.info("""
        **💡 页面跳转说明：**
        1. 页面加载时，系统会**自动尝试**在新标签页打开 HTML 文件。
        2. 如果您看到上方显示 **"浏览器阻止了自动弹出窗口"**，请点击 **“点击手动打开HTML页面”** 按钮。
        3. 如果您想恢复自动跳转功能，请在浏览器地址栏处设置，**允许本网站的弹出窗口**。
        """)

    except Exception as e:
        st.error(f"读取文件时出错: {str(e)}")
        st.info("请检查文件编码或文件是否完整")


if __name__ == "__main__":
    main()