# --- 核心数据结构: 统一管理所有脚本和分组 ---
SCRIPTS_BY_GROUP = {
    "🤖 AI工具": [
        {
            "label": "💬 AI对话",
            "path": r"pages/7_AI_对话页面.py"
        },
        # {
        #     "label": "🎵 语句分析（已废弃）",
        #     "path": r"pages/3_英语句子语音现象分析.py"
        # },
        {
            "label": "🎵 音变分析",
            "path": r"pages/3_音变分析.py"
        },
        {
            "label": "📈 杂质统计",
            "path": r"pages/8_杂质统计.py"
        },
    ],
    "📊 运营工具": [
        {
            "label": "🔍 关键词统计",
            "path": r"pages/2_关键词统计.py"
        },
        {
            "label": "📝 Listing生成",
            "path": r"pages/2_Listing生成.py"
        },
        {
            "label": "✅ 任务看板",
            "path": r"pages/0_任务看板.py"
        },
        {
            "label": "🛍️ 商品信息提取",
            "path": r"pages/4_一键提取亚马逊页面关键信息.py"
        },
        # {
        #     "label": "👬 群成员名称提取",
        #     "path": r"pages/4_提取掌上大学群成员名称.py"
        # },
        {
            "label": "📦 Amazon评论提取",
            "path": r"pages/2_Amazon评论获取.py"
        },
        {
            "label": "🛍️ 妙手链接采集器",
            "path": r"pages/4_链接采集.py"
        },
        {
            "label": "🕸️ 浏览器抓取编排",
            "path": r"pages/4_网页元素梳理.py"
        },
    ],
    "📝 文本处理": [
        {
            "label": "🎬 B站标题提取",
            "path": r"pages/4_提取B站标题.py"
        },
        {
            "label": "📚 读书笔记转换",
            "path": r"pages/4_读书笔记转markdown文档.py"
        },
        {
            "label": "🔊 文字转语音",
            "path": r"pages/3_文本转语音.py"
        },
        {
            "label": "📄 文本对比",
            "path": r"pages/4_文本对比.py"
        },
        {
            "label": "🧹 去除空行",
            "path": r"pages/4_去除空白行.py"
        },
    ],
    "🖼️ 图像处理": [
        {
            "label": "🎨 替换背景",
            "path": r"pages/5_替换图片背景.py"
        },
        {
            "label": "📦 图像压缩",
            "path": r"pages/6_图像压缩.py"
        },
        {
            "label": "🌐 图片翻译",
            "path": r"pages/6_图片翻译.py"
        },
        {
            "label": "🔗 在线图床",
            "path": r"pages/6_生成图片在线地址.py"
        },
        {
            "label": "🎬 视频压缩",
            "path": r"pages/6_视频压缩.py"
        },
    ],
    "🧩 其他工具": [
        {
            "label": "📈 基金盯盘",
            "path": r"pages/8_基金涨跌.py"
        },
        {
            "label": "🧪 测试页面",
            "path": r"pages/8_测试页面.py"
        },
    ],
}