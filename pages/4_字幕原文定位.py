# app.py

import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re

# ------------------- 页面配置 -------------------
# 使用 wide 布局让界面更舒展
st.set_page_config(layout="wide", page_title="视频片段定位器", page_icon="🎬")


# ------------------- 核心功能函数 (带缓存) -------------------

# 使用缓存避免重复调用API，提高性能并节省配额
@st.cache_data(ttl=3600)  # 缓存1小时
def search_youtube_videos(api_key, query, max_results=5):
    """使用 YouTube API 搜索与查询相关的、带字幕的视频。"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            videoCaption='closedCaption',  # 关键：只搜索有字幕的视频
            maxResults=max_results
        )
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        # 向用户显示一个更友好的错误信息
        st.error(f"无法连接到 YouTube API。请检查你的 API 密钥和网络连接。错误详情: {e}")
        return []


@st.cache_data(ttl=3600)
def find_text_in_transcript(video_id, text_to_find):
    """在视频字幕中查找指定文本，返回第一个匹配项的时间和上下文。"""
    try:
        # 优先获取中文，其次是英文，可以根据你的需要调整
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-CN', 'zh-Hans', 'zh', 'en'])

        # 为了更好的上下文，我们将字幕拼接起来搜索
        full_transcript_text = " ".join([seg['text'] for seg in transcript])

        # 使用正则表达式查找（不区分大小写）
        match = re.search(f"(.{{0,50}}){re.escape(text_to_find)}(.{{0,50}})", full_transcript_text,
                          re.IGNORECASE | re.DOTALL)

        if not match:
            return None

        # 找到匹配后，再定位到具体的时间戳
        for segment in transcript:
            if text_to_find.lower() in segment['text'].lower():
                context = f"...{match.group(1).strip() if match.group(1) else ''} **{text_to_find}** {match.group(2).strip() if match.group(2) else ''}..."
                return {
                    "start_time": int(segment['start']),
                    "context": context
                }
        return None

    except (TranscriptsDisabled, NoTranscriptFound):
        # 这是一个预期的“错误”，所以使用 st.info 提示而不是 st.error
        return "TranscriptsDisabled"
    except Exception:
        return None


# ------------------- Streamlit 界面布局 -------------------

# 1. 标题和介绍
st.title("🎬 视频片段智能定位器")
st.markdown("输入一段文字，程序将自动从 YouTube 中查找包含这段文字的视频，并直接跳转到该时间点播放。")
st.markdown("---")  # 添加一条分割线

# 2. API 密钥检查
try:
    API_KEY = st.secrets["youtube_key"]
except (KeyError, FileNotFoundError):
    st.error("错误：未找到 YouTube API 密钥。请在 Streamlit Secrets 中配置 `youtube_key`。")
    st.stop()  # 如果没有密钥，停止执行

# 3. 搜索输入区
col1, col2 = st.columns([4, 1])
with col1:
    search_query = st.text_input(
        "输入你想查找的文字或对话：",
        "什么是人工智能",
        label_visibility="collapsed",
        placeholder="例如：什么是人工智能"
    )
with col2:
    search_button = st.button("🔍 开始搜索", use_container_width=True, type="primary")

# 4. 结果展示区
if search_button and search_query:
    # 使用状态容器，让用户知道后台正在发生什么
    status_placeholder = st.empty()

    status_placeholder.info("第一步：正在 YouTube 上搜索相关视频...")
    videos = search_youtube_videos(API_KEY, search_query)

    if not videos:
        status_placeholder.warning("未能找到任何相关视频。请尝试更换关键词。")
    else:
        status_placeholder.info(f"第二步：找到了 {len(videos)} 个视频，正在逐一分析字幕内容...")

        found_match = False
        results_placeholder = st.container()  # 创建一个容器来存放所有结果卡片

        for video in videos:
            video_id = video['id']['videoId']
            video_title = video['snippet']['title']
            channel_title = video['snippet']['channelTitle']

            match_data = find_text_in_transcript(video_id, search_query)

            if isinstance(match_data, dict):
                found_match = True
                status_placeholder.success("🎉 找到了！已定位到视频片段。")

                # 使用带边框的容器来创建卡片效果
                with results_placeholder.container(border=True):
                    st.subheader(video_title)
                    st.caption(f"频道: {channel_title}")

                    st.info(f"**找到的文本上下文：**\n\n{match_data['context']}")

                    # 生成带时间戳的URL并在st.video中播放
                    start_seconds = match_data['start_time']
                    video_url = f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s"
                    st.video(video_url)
                    st.markdown(f"🔗 [在 YouTube 上打开]({video_url})")

                # 找到第一个就停止，以获得最快的响应。如果想找所有匹配项，可以去掉 break。
                break

        if not found_match:
            status_placeholder.warning("分析了所有相关视频，但未在字幕中找到你输入的精确文字。")

elif search_button and not search_query:
    st.warning("请输入你要搜索的内容。")