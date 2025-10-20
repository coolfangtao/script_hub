# shard/elements.py

import streamlit as st


# 我们不再需要 st.components.v1 了
# import streamlit.components.v1 as components

def shin_chan_animation(
        gif_url: str = "https://img.alicdn.com/imgextra/i2/2210123621994/O1CN019ne3h11QbIltvPjB8_!!2210123621994.gif",
        position: str = "top",
        speed_seconds: int = 18,
        size_pixels: int = 180,  # 从你的截图中看，动画尺寸较小，我把默认值改成了100
        distance_from_edge_pixels: int = 30
):
    """
    在Streamlit页面上渲染一个蜡笔小新左右移动的动画。
    """
    position_css = f"{position}: {distance_from_edge_pixels}px;"

    # CSS动画代码保持不变
    animation_html = f"""
    <style>
        @keyframes walk-across {{
            0%    {{ transform: translateX(-{size_pixels + 50}px); }}
            48%   {{ transform: translateX(calc(100vw - {size_pixels}px)); }}
            50%   {{ transform: translateX(calc(100vw - {size_pixels}px)) scaleX(-1); }}
            98%   {{ transform: translateX(-{size_pixels + 50}px) scaleX(-1); }}
            100%  {{ transform: translateX(-{size_pixels + 50}px) scaleX(1); }}
        }}

        .shin-chan-animation {{
            position: fixed;
            {position_css}
            left: 0;
            width: {size_pixels}px;
            height: auto;
            z-index: 9999;
            animation: walk-across {speed_seconds}s linear infinite;
        }}
    </style>

    <img src="{gif_url}" class="shin-chan-animation">
    """

    # 【关键修改】使用 st.markdown 来渲染，而不是 st.components.v1.html
    st.markdown(animation_html, unsafe_allow_html=True)