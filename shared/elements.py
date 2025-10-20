# shard/elements.py (健壮性优化版)

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
    """
    position_css = f"{position}: {distance_from_edge_pixels}px;"

    animation_html = f"""
    <style>
        .shin-chan-element {{
            position: fixed;
            {position_css}
            left: 0;
            width: {size_pixels}px;
            height: auto;
            z-index: 9999;
            transform: scaleX(1);
        }}
    </style>

    <img src="{gif_url}" id="shin-chan-element" class="shin-chan-element">

    <script>
        // 【关键修改】将所有代码包裹在一个事件监听器中
        // 这可以确保在页面的所有基本元素都加载完毕后，再执行我们的脚本
        document.addEventListener('DOMContentLoaded', (event) => {{
            const shinChan = document.getElementById('shin-chan-element');

            // 如果找不到元素，就直接退出，防止报错
            if (!shinChan) return;

            let positionX = 0;
            let direction = 1;
            let isPaused = false;

            const speed = {movement_speed};
            const size = {size_pixels};
            const screenWidth = window.innerWidth;

            function animate() {{
                if (isPaused) {{
                    requestAnimationFrame(animate);
                    return;
                }}

                positionX += speed * direction;
                shinChan.style.transform = `translateX(${{positionX}}px) scaleX(${{direction}})`;

                if (positionX > screenWidth - size) {{
                    direction = -1;
                }} else if (positionX < 0) {{
                    direction = 1;
                }}

                if (Math.random() < {pause_chance}) {{
                    isPaused = true;
                    const pauseDuration = Math.random() * 3000 + 1000;

                    setTimeout(() => {{
                        isPaused = false;
                        if (Math.random() < 0.5) {{
                            direction *= -1;
                        }}
                    }}, pauseDuration);
                }}

                requestAnimationFrame(animate);
            }}

            // 启动动画
            animate();
        }});
    </script>
    """

    st.markdown(animation_html, unsafe_allow_html=True)