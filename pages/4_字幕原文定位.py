# app.py (版本 3 - 最终修正版)

import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re

# ------------------- 页面配置 -------------------
st.set_page_config(layout="wide", page_title="视频片段定位器", page_icon="🎬")


# ------------------- 核心功能函数 (带缓存) -------------------

@st.cache_data(ttl=3600)
def search_youtube_videos(api_key, query, max_results=5):
    """使用 YouTube API 搜索与查询相关的、带字幕的视频。"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            videoCaption='closedCaption',
            maxResults=max_results
        )
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        st.error(f"无法连接到 YouTube API。请检查你的 API 密钥和网络连接。错误详情: {e}")
        return []


@st.cache_data(ttl=3600)
def find_keywords_in_transcript(video_id, query):
    """在字幕中查找包含所有关键词的片段。"""
    try:
        # --- 核心修正：移除了 len(word) > 2 的过滤器 ---
        keywords = [word.lower() for word in query.split()]

        # 如果用户只输入了空格，关键词列表可能为空，直接返回
        if not keywords:
            return None

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-CN', 'zh-Hans', 'zh', 'en'])

        for i, segment in enumerate(transcript):
            segment_text_lower = segment['text'].lower()

            if all(keyword in segment_text_lower for keyword in keywords):
                context_start_index = max(0, i - 1)
                context_end_index = min(len(transcript) - 1, i + 1)
                full_context = " ".join(
                    [transcript[j]['text'] for j in range(context_start_index, context_end_index + 1)])

                highlighted_context = full_context
                for keyword in query.split():  # 使用原始query里的词来高亮，保持大小写
                    highlighted_context = re.sub(f"({re.escape(keyword)})", r"**\1**", highlighted_context,
                                                 flags=re.IGNORECASE)

                return {
                    "start_time": int(segment['start']),
                    "context": f"...{highlighted_context}..."
                }
        return None

    except (TranscriptsDisabled, NoTranscriptFound):
        return "TranscriptsDisabled"
    except Exception:
        return None


# ------------------- Streamlit 界面布局 -------------------

st.title("🎬 视频片段智能定位器")
st.markdown("输入一段文字，程序将自动从 YouTube 中查找包含这段文字的视频，并直接跳转到该时间点播放。")
st.markdown("---")

try:
    API_KEY = st.secrets["youtube_key"]
except (KeyError, FileNotFoundError):
    st.error("错误：未找到 YouTube API 密钥。请在 Streamlit Secrets 中配置 `youtube_key`。")
    st.stop()

col1, col2 = st.columns([4, 1])
with col1:
    search_query = st.text_input(
        "输入你想查找的文字或对话：",
        "What is AI",
        label_visibility="collapsed",
        placeholder="建议使用英文核心关键词以提高成功率"
    )
with col2:
    search_button = st.button("🔍 开始搜索", use_container_width=True, type="primary")

if search_button and search_query:
    status_placeholder = st.empty()
    status_placeholder.info("第一步：正在 YouTube 上搜索相关视频...")
    videos = search_youtube_videos(API_KEY, search_query)

    if not videos:
        status_placeholder.warning("未能找到任何相关视频。请尝试更换关键词。")
    else:
        status_placeholder.info(f"第二步：找到了 {len(videos)} 个视频，正在逐一分析字幕...")

        found_match = False
        results_placeholder = st.container()
        progress_bar = st.progress(0, text="分析进度")

        for i, video in enumerate(videos):
            video_id = video['id']['videoId']
            video_title = video['snippet']['title']
            progress_text = f"分析中 ({i + 1}/{len(videos)}): {video_title}"
            progress_bar.progress((i + 1) / len(videos), text=progress_text)

            match_data = find_keywords_in_transcript(video_id, search_query)

            if match_data == "TranscriptsDisabled":
                with results_placeholder.expander(f"⚠️ **{video_title}** - 字幕不可用或受限"):
                    st.write("无法分析此视频，因为它关闭了字幕功能或不提供可访问的字幕。")
                continue

            if isinstance(match_data, dict):
                found_match = True
                status_placeholder.success("🎉 找到了！已定位到匹配的视频片段。")

                with results_placeholder.container(border=True):
                    st.subheader(video_title)
                    st.caption(f"频道: {video['snippet']['channelTitle']}")
                    st.markdown(f"**找到的文本上下文：**\n\n{match_data['context']}")
                    start_seconds = match_data['start_time']
                    video_url = f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s"
                    st.video(video_url)
                    st.markdown(f"🔗 [在 YouTube 上打开]({video_url})")

                progress_bar.empty()
                break

        if not found_match:
            progress_bar.empty()
            status_placeholder.warning("分析了所有相关视频，但未在字幕中找到同时包含所有关键词的片段。请尝试更简单、更核心的关键词。")

elif search_button and not search_query:
    st.warning("请输入你要搜索的内容。")