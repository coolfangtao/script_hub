# app.py

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


# --- YouTube API 功能 ---

def get_youtube_service():
    """
    使用Streamlit的secrets功能安全地构建并返回YouTube API服务对象。
    """
    try:
        api_key = st.secrets["youtube_key"]
        youtube = build('youtube', 'v3', developerKey=api_key)
        return youtube
    except KeyError:
        st.error("错误：未找到YouTube API密钥。请确保在 .streamlit/secrets.toml 文件中设置了 'youtube_key'。")
        return None
    except Exception as e:
        st.error(f"构建YouTube服务时发生错误: {e}")
        return None


def search_videos(youtube_service, query, max_results=5):
    """
    根据查询词在YouTube上搜索视频。
    """
    try:
        request = youtube_service.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
            relevanceLanguage="zh-CN"  # 优先搜索中文内容
        )
        response = request.execute()
        return response.get('items', [])
    except HttpError as e:
        st.error(f"YouTube搜索时发生HTTP错误: {e.resp.status} {e.content}")
        return []


def find_subtitle_in_transcript(video_id, subtitle_text):
    """
    获取指定视频的字幕，并查找包含目标文本的片段。
    """
    found_segments = []
    try:
        # 尝试获取多种常用语言的字幕
        transcript_list = YouTubeTranscriptApi.fetch(video_id, languages=['zh-CN', 'zh-TW', 'en', 'ja', 'ko'])

        for item in transcript_list:
            # 不区分大小写进行匹配
            if subtitle_text.lower() in item['text'].lower():
                found_segments.append({
                    'text': item['text'],
                    'start': int(item['start']),
                    'duration': item['duration']
                })
        return found_segments
    except (NoTranscriptFound, TranscriptsDisabled):
        # 如果视频没有字幕或禁用了字幕，则静默处理
        return []
    except Exception:
        # 其他可能的异常
        return []


# --- Streamlit 页面布局 ---

def main():
    st.set_page_config(page_title="视频字幕片段查找器", layout="wide", initial_sidebar_state="collapsed")

    st.title("🎬 视频字幕片段查找器")
    st.markdown("输入一句台词或字幕，此工具将查找包含该文本的YouTube视频，并直接定位到相关片段，方便您进行剪辑。")

    youtube_service = get_youtube_service()
    if not youtube_service:
        st.stop()

    # 使用表单来组织输入和提交按钮
    with st.form(key='search_form'):
        search_query = st.text_input(
            "输入您要查找的字幕文本:",
            placeholder="例如：'我真是个天才' 或 'this is where the fun begins'"
        )
        submit_button = st.form_submit_button(label='🔍 开始查找')

    if submit_button and search_query:
        with st.spinner('正在搜索视频并分析字幕，请稍候...'):
            videos = search_videos(youtube_service, search_query, max_results=5)

            if not videos:
                st.warning("未能根据您的输入找到相关视频，请尝试更换关键词。")
                st.stop()

            results_found_in_any_video = False

            for video in videos:
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                segments = find_subtitle_in_transcript(video_id, search_query)

                if segments:
                    results_found_in_any_video = True
                    st.subheader(f"在视频 “[ {video_title} ]” 中找到结果")

                    for seg in segments:
                        with st.container(border=True):
                            start_time = seg['start']

                            col1, col2 = st.columns([3, 2])

                            with col1:
                                # 直接播放定位到关键时间的视频
                                st.video(video_url, start_time=start_time)

                            with col2:
                                st.info(f"**匹配到的字幕:**")
                                st.write(f"“...{seg['text']}...”")
                                st.success(f"**片段开始时间:** {start_time} 秒")
                                st.page_link(video_url, label="在新标签页中打开YouTube视频", icon="🔗")

            if not results_found_in_any_video:
                st.info("已搜索相关视频，但未在其可用字幕中找到您输入的文本。可能是视频没有字幕，或文本不匹配。")


if __name__ == "__main__":
    main()