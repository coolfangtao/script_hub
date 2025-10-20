# shard/elements.py

import streamlit as st


def shin_chan_animation(
        gif_url: str = "https://img.alicdn.com/imgextra/i2/2210123621994/O1CN019ne3h11QbIltvPjB8_!!2210123621994.gif",
        position: str = "top",
        size_pixels: int = 180,
        distance_from_edge_pixels: int = 25,
        movement_speed: float = 2.5,
        pause_chance: float = 0.005
):
    """
    在Streamlit页面上渲染一个行为更随机的蜡笔小新动画。

    参数:
    - gif_url (str): GIF的URL地址。
    - position (str): 'top' 或 'bottom'。
    - size_pixels (int): 动画的宽度（像素）。
    - distance_from_edge_pixels (int): 距离顶部或底部的距离（像素）。
    - movement_speed (float): 移动速度，数字越大走得越快。
    - pause_chance (float): 在每一帧停下来的几率 (0.0 到 1.0 之间的一个很小的数, e.g., 0.005)。
    """

    position_css = f"{position}: {distance_from_edge_pixels}px;"

    # HTML 包含一个 img 标签用于显示小新
    # CSS 用于初始定位和样式
    # JavaScript (<script>) 用于控制所有动态行为
    animation_html = f"""
    <style>
        /* CSS现在只负责基础样式，不再处理动画 */
        .shin-chan-element {{
            position: fixed;
            {position_css}
            left: 0;
            width: {size_pixels}px;
            height: auto;
            z-index: 9999;
            /* 初始时图片是朝右的 */
            transform: scaleX(1);
        }}
    </style>

    <img src="{gif_url}" id="shin-chan-element" class="shin-chan-element">

    <script>
        const shinChan = document.getElementById('shin-chan-element');

        let positionX = 0;
        let direction = 1; // 1 表示向右, -1 表示向左
        let isPaused = false;

        const speed = {movement_speed};
        const size = {size_pixels};
        const screenWidth = window.innerWidth;

        function animate() {{
            // 如果处于暂停状态，则什么都不做
            if (isPaused) {{
                requestAnimationFrame(animate);
                return;
            }}

            // 更新位置
            positionX += speed * direction;
            shinChan.style.transform = `translateX(${{positionX}}px) scaleX(${{direction}})`;

            // 边界检测，撞到墙就转身
            if (positionX > screenWidth - size) {{
                direction = -1;
            }} else if (positionX < 0) {{
                direction = 1;
            }}

            // 随机暂停的逻辑
            if (Math.random() < {pause_chance}) {{
                isPaused = true;
                // 随机决定暂停多久 (1到4秒)
                const pauseDuration = Math.random() * 3000 + 1000;

                setTimeout(() => {{
                    isPaused = false;
                    // 暂停结束后，有50%的几率会换个方向
                    if (Math.random() < 0.5) {{
                        direction *= -1;
                    }}
                }}, pauseDuration);
            }}

            // 请求下一帧动画
            requestAnimationFrame(animate);
        }}

        // 启动动画
        animate();
    </script>
    """

    st.markdown(animation_html, unsafe_allow_html=True)