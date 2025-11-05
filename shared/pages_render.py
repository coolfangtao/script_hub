# 文件路径: shared/pages_render.py

"""
核心数据结构: 统一管理所有脚本和分组
"""

SCRIPTS_BY_GROUP = {
    "🤖 AI工具": [
        {
            "label": "💬 AI对话",
            "path": r"pages/7_AI_对话页面.py",
            "description": None
        },
        {
            "label": "🎵 音变分析",
            "path": r"pages/3_音变分析.py",
            "description": None
        },
        {
            "label": "📈 杂质统计",
            "path": r"pages/8_杂质统计.py",
            "description": None
        },
    ],
    "📊 运营工具": [
        {
            "label": "🔍 关键词统计",
            "path": r"pages/2_关键词统计.py",
            "description": None
        },
        {
            "label": "📝 Listing生成",
            "path": r"pages/2_Listing生成.py",
            "description": None
        },
        {
            "label": "✅ 任务看板",
            "path": r"pages/0_任务看板.py",
            "description": "高效记录并管理日常任务，清晰掌握工作进度，提升个人时间管理效率。"
        },
        {
            "label": "🛍️ 商品信息提取",
            "path": r"pages/4_一键提取亚马逊页面关键信息.py",
            "description": None
        },
        {
            "label": "📦 Amazon评论提取",
            "path": r"pages/2_Amazon评论获取.py",
            "description": None
        },
        {
            "label": "🛍️ 妙手链接采集器",
            "path": r"pages/4_链接采集.py",
            "description": None
        },
        {
            "label": "🕸️ 浏览器抓取编排",
            "path": r"pages/4_网页元素梳理.py",
            "description": None
        },
    ],
    "📝 文本处理": [
        {
            "label": "🎬 B站标题提取",
            "path": r"pages/4_提取B站标题.py",
            "description": "输入B站视频链接，自动提取页面中视频合集的所有标题内容，支持批量导出。"
        },
        {
            "label": "📚 读书笔记转换",
            "path": r"pages/4_读书笔记转markdown文档.py",
            "description": None
        },
        {
            "label": "🔊 文字转语音",
            "path": r"pages/3_文本转语音.py",
            "description": None
        },
        {
            "label": "📄 文本对比",
            "path": r"pages/4_文本对比.py",
            "description": "快速比对两个文本内容的差异，直观显示修改位置，轻松找出变动之处。"
        },
        {
            "label": "🧹 去除空行",
            "path": r"pages/4_去除空白行.py",
            "description": None
        },
    ],
    "🖼️ 图像处理": [
        {
            "label": "🎨 替换背景",
            "path": r"pages/5_替换图片背景.py",
            "description": None
        },
        {
            "label": "📦 图像压缩",
            "path": r"pages/6_图像压缩.py",
            "description": None
        },
        {
            "label": "🌐 图片翻译",
            "path": r"pages/6_图片翻译.py",
            "description": None
        },
        {
            "label": "🔗 在线图床",
            "path": r"pages/6_生成图片在线地址.py",
            "description": "上传本地图片，一键生成可分享的在线访问链接，方便快捷地获取图片网络地址。"
        },
        {
            "label": "🎬 视频压缩",
            "path": r"pages/6_视频压缩.py",
            "description": None
        },
    ],
    "🧩 其他工具": [
        {
            "label": "📈 基金盯盘",
            "path": r"pages/8_基金涨跌.py",
            "description": None
        },
        {
            "label": "🧪 测试页面",
            "path": r"pages/8_测试页面.py",
            "description": None
        },
    ],
}