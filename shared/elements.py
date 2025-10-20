# shard/elements.py
import streamlit as st


def shin_chan_animation(
        gif_url: str = "https://img.alicdn.com/imgextra/i2/2210123621994/O1CN019ne3h11QbIltvPjB8_!!2210123621994.gif",
        position: str = "top",
        speed_seconds: int = 100,  # 走完整个页面需要多少秒
        size_pixels: int = 180,  # 蜡笔小新身高
        distance_from_edge_pixels: int = 25  # 距离顶部距离
):
    """
    在Streamlit页面上渲染一个蜡笔小新左右移动的动画。
    """
    position_css = f"{position}: {distance_from_edge_pixels}px;"

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
            /* 【关键修改】提高 z-index 的值，确保它在最顶层 */
            z-index: 999999;
            animation: walk-across {speed_seconds}s linear infinite;
        }}
    </style>

    <img src="{gif_url}" class="shin-chan-animation">
    """

    st.markdown(animation_html, unsafe_allow_html=True)