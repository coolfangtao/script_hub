# shard/elements.py

import streamlit as st
import streamlit.components.v1 as components


def shin_chan_animation(
        gif_url: str = "https://img.alicdn.com/imgextra/i2/2210123621994/O1CN019ne3h11QbIltvPjB8_!!2210123621994.gif",
        position: str = "bottom",
        speed_seconds: int = 10,
        size_pixels: int = 120,
        distance_from_edge_pixels: int = 10
):
    """
    在Streamlit页面上渲染一个蜡笔小新左右移动的动画。

    参数:
    - gif_url (str): 蜡笔小新GIF的URL地址。
    - position (str): 动画显示的位置，'top' 或 'bottom'。
    - speed_seconds (int): 完成一次来回移动所需的秒数。
    - size_pixels (int): 动画的宽度（像素）。
    - distance_from_edge_pixels (int): 动画距离顶部或底部的距离（像素）。
    """

    # 根据传入的位置参数，决定CSS是使用'top'还是'bottom'
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
            z-index: 9999;
            animation: walk-across {speed_seconds}s linear infinite;
        }}
    </style>

    <img src="{gif_url}" class="shin-chan-animation">
    """

    # 使用components.html来渲染HTML/CSS
    # 高度设置为动画高度+边距，确保不会被截断
    components.html(animation_html, height=size_pixels + distance_from_edge_pixels + 20)