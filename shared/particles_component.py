# 文件: shared/particles_component.py

import streamlit as st


def render_particles():
    """
    在Streamlit页面上渲染全屏的粒子动画作为背景。
    """

    # 抽取核心的HTML, CSS, 和 JavaScript
    # 注意:
    # 1. CSS中的 z-index 设置为 -1，这是让它成为背景的关键！
    # 2. position 设置为 fixed，确保它覆盖整个视口，并且在滚动时保持不动。
    particles_js_html = """
    <style>
      #particles-js {
        position: fixed; /* 固定位置，不随滚动条滚动 */
        width: 100vw;    /* 100% 视口宽度 */
        height: 100vh;   /* 100% 视口高度 */
        top: 0;
        left: 0;
        z-index: -1;     /* 将其置于所有内容的背景层 */
      }
    </style>

    <div id="particles-js"></div>

    <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>

    <script>
      particlesJS("particles-js", {
        "particles": {
          "number": {"value": 100, "density": {"enable": true, "value_area": 800}},
          "color": {"value": "#ffffff"},
          "shape": {"type": "circle"},
          "opacity": {"value": 0.5, "random": false},
          "size": {"value": 2, "random": true},
          "line_linked": {"enable": true, "distance": 150, "color": "#ffffff", "opacity": 0.2, "width": 1},
          "move": {"enable": true, "speed": 0.5, "direction": "none", "out_mode": "out"}
        },
        "interactivity": {
          "detect_on": "canvas",
          "events": {
            "onhover": {"enable": true, "mode": "grab"},
            "onclick": {"enable": true, "mode": "push"},
            "resize": true
          },
          "modes": {
            "grab": {"distance": 140, "line_linked": {"opacity": 1}},
            "push": {"particles_nb": 4}
          }
        },
        "retina_detect": true
      });
    </script>
    """

    # 使用 st.markdown 将HTML内容注入到页面
    st.markdown(particles_js_html, unsafe_allow_html=True)