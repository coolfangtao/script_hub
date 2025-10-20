# 文件: particles_component.py

# 将完整的 HTML 和 JavaScript 代码赋值给一个变量
particles_js_code = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Particles.js</title>
  <style>
  #particles-js {
    position: fixed;
    width: 100vw;
    height: 100vh;
    top: 0;
    left: 0;
    z-index: -1;
  }
</style>
</head>
<body>
  <div id="particles-js"></div>
  <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
  <script>
    particlesJS("particles-js", {
      "particles": {
        "number": {"value": 300, "density": {"enable": true, "value_area": 800}},
        "color": {"value": "#ffffff"},
        "shape": {"type": "circle"},
        "opacity": {"value": 0.5, "random": false},
        "size": {"value": 2, "random": true},
        "line_linked": {"enable": true, "distance": 100, "color": "#ffffff", "opacity": 0.22, "width": 1},
        "move": {"enable": true, "speed": 0.2, "direction": "none", "out_mode": "out"}
      },
      "interactivity": {
        "detect_on": "canvas",
        "events": {
          "onhover": {"enable": true, "mode": "grab"},
          "onclick": {"enable": true, "mode": "repulse"},
          "resize": true
        },
        "modes": {
          "grab": {"distance": 100, "line_linked": {"opacity": 1}},
          "repulse": {"distance": 200}
        }
      },
      "retina_detect": true
    });
  </script>
</body>
</html>
"""