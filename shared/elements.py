# shard/elements.py
import streamlit as st


def shin_chan_animation(
        gif_url: str = "https://img.alicdn.com/imgextra/i2/2210123621994/O1CN019ne3h11QbIltvPjB8_!!2210123621994.gif",
        position: str = "top",
        speed_seconds: int = 100,  # 可以适当减少时间，因为路径更复杂
        size_pixels: int = 100,
        distance_from_edge_pixels: int = 25,
        random_walk: bool = True  # 新增参数，控制是否启用“随机”行走模式
):
    """
    在Streamlit页面上渲染一个蜡笔小新移动的动画。

    :param gif_url: 蜡笔小新GIF的URL。
    :param position: 动画元素的垂直位置 ('top' or 'bottom')。
    :param speed_seconds: 走完整个动画循环需要的时间（秒）。
    :param size_pixels: 蜡笔小新的高度（像素）。
    :param distance_from_edge_pixels: 距离页面顶部或底部的距离（像素）。
    :param random_walk: 如果为True，则使用带有停顿和变速的复杂行走路径。
    """
    position_css = f"{position}: {distance_from_edge_pixels}px;"

    # 原始的左右往返动画
    walk_across_keyframes = f"""
        @keyframes walk-across {{
            0%    {{ transform: translateX(-{size_pixels + 50}px); }}
            48%   {{ transform: translateX(calc(100vw - {size_pixels}px)); }}
            50%   {{ transform: translateX(calc(100vw - {size_pixels}px)) scaleX(-1); }}
            98%   {{ transform: translateX(-{size_pixels + 50}px) scaleX(-1); }}
            100%  {{ transform: translateX(-{size_pixels + 50}px) scaleX(1); }}
        }}
    """

    # 新的、更复杂的“随机”行走动画（带停顿）
    random_walk_keyframes = f"""
        @keyframes random-walk {{
            0%      {{ transform: translateX(-{size_pixels}px) scaleX(1); }} /* 从左边屏幕外开始 */
            15%     {{ transform: translateX(30vw) scaleX(1); }} /* 走到屏幕30%处 */
            20%     {{ transform: translateX(30vw) scaleX(1); }} /* 在30%处停顿 */
            35%     {{ transform: translateX(85vw) scaleX(1); }} /* 快速走到屏幕85%处 */
            40%     {{ transform: translateX(85vw) scaleX(1); }} /* 在85%处停顿 */
            45%     {{ transform: translateX(85vw) scaleX(-1); }} /* 转身 */
            60%     {{ transform: translateX(20vw) scaleX(-1); }} /* 走回屏幕20%处 */
            65%     {{ transform: translateX(20vw) scaleX(-1); }} /* 在20%处停顿 */
            85%     {{ transform: translateX(-{size_pixels}px) scaleX(-1); }} /* 走回左边屏幕外 */
            100%    {{ transform: translateX(-{size_pixels + 50}px) scaleX(1); }} /* 转身，为下一次循环做准备 */
        }}
    """

    if random_walk:
        animation_name = "random-walk"
        animation_keyframes = random_walk_keyframes
    else:
        animation_name = "walk-across"
        animation_keyframes = walk_across_keyframes

    animation_html = f"""
    <style>
        {animation_keyframes}

        .shin-chan-animation {{
            position: fixed;
            {position_css}
            left: 0;
            width: {size_pixels}px;
            height: auto;
            z-index: 999999;
            /* 根据参数选择使用的动画名称 */
            animation: {animation_name} {speed_seconds}s linear infinite;
        }}
    </style>

    <img src="{gif_url}" class="shin-chan-animation">
    """

    st.markdown(animation_html, unsafe_allow_html=True)