#!/bin/bash -l

# 首先，切换到你的项目根目录
# 这是为了确保所有相对路径（如 pages/, shared/）都正确
cd /Users/fangtao/Documents/Code/脚本集合2.0

# 关键：激活你的Python虚拟环境
source /Users/fangtao/Documents/Code/脚本集合2.0/venv1/bin/activate

# 运行Streamlit主应用
streamlit run streamlit_app.py