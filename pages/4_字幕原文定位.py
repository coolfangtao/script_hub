import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import logging

# --- 日志配置 ---
# 配置日志记录，使其输出到控制台
logging.basicConfig(
    level=logging.DEBUG,  # 记录 DEBUG 及以上级别的日志
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# --- YouTube API 功能 ---

def get_youtube_service():
    """
    使用Streamlit的secrets功能安全地构建并返回YouTube API服务对象。
    """
    try:
        api_key = st.secrets["youtube_key"]
        youtube = build('youtube', 'v3', developerKey=api_key)
        logging.info("YouTube API 服务初始化成功。")
        return youtube
    except KeyError:
        logging.error("错误：未找到YouTube API密钥。请确保在 .streamlit/secrets.toml 文件中设置了 'youtube_key'。")
        st.error("错误：未找到YouTube API密钥。请确保在 .streamlit/secrets.toml 文件中设置了 'youtube_key'。")
        return None
    except Exception as e:
        logging.error(f"构建YouTube服务时发生错误: {e}", exc_info=True)
        st.error(f"构建YouTube服务时发生错误: {e}")
        return None


def search_videos(youtube_service, query, max_results=5):
    """
    根据查询词在YouTube上搜索视频。
    (注意：我将 max_results 改回了 5，因为 50 会消耗大量 API 配额并且非常慢。如果您确实需要50，请改回。)
    """
    logging.info(f"开始搜索视频，查询词：'{query}', 最大结果数：{max_results}")
    try:
        request = youtube_service.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
            relevanceLanguage="zh-CN"  # 优先搜索中文内容
        )
        response = request.execute()
        items = response.get('items', [])
        logging.info(f"YouTube API 搜索到 {len(items)} 个视频。")
        return items
    except HttpError as e:
        logging.error(f"YouTube搜索时发生HTTP错误: {e.resp.status} {e.content}", exc_info=True)
        st.error(f"YouTube搜索时发生HTTP错误: {e.resp.status} {e.content}")
        return []


def find_subtitle_in_transcript(video_id, subtitle_text):
    """
    获取指定视频的字幕，并查找包含目标文本的片段。
    此函数已根据最新的 youtube_transcript_api 版本进行更新。
    """
    logging.debug(f"开始为视频 {video_id} 查找字幕: '{subtitle_text}'")
    found_segments = []
    # 首先，实例化YouTubeTranscriptApi类
    ytt_api = YouTubeTranscriptApi()
    try:
        # 使用实例的 fetch 方法，这是对 list().find_transcript().fetch() 的快捷方式
        # fetch方法返回一个FetchedTranscript对象，它包含了FetchedTranscriptSnippet对象的列表
        transcript = ytt_api.fetch(video_id, languages=['zh-CN', 'zh-TW', 'en', 'ja', 'ko'])
        logging.debug(f"视频 {video_id}：成功获取 {len(transcript)} 个字幕片段。")

        # FetchedTranscript 对象是可迭代的
        # 迭代的每一项都是一个 FetchedTranscriptSnippet 数据类实例
        for snippet in transcript:
            # 不区分大小写进行匹配
            # 使用属性访问 .text, .start, .duration
            if subtitle_text.lower() in snippet.text.lower():
                logging.info(f"视频 {video_id}：找到匹配！文本：'{snippet.text}'")
                found_segments.append({
                    'text': snippet.text,
                    'start': int(snippet.start),
                    'duration': snippet.duration
                })

        if not found_segments:
            logging.debug(f"视频 {video_id}：获取了字幕，但未找到匹配文本 '{subtitle_text}'。")

        return found_segments

    except (NoTranscriptFound, TranscriptsDisabled) as e:
        # 如果视频没有字幕或禁用了字幕，则静默处理
        logging.warning(f"视频 {video_id}：未找到字幕或字幕已禁用。错误：{e}")
        return []
    except Exception as e:
        # 其他可能的异常
        logging.error(f"视频 {video_id}：查找字幕时发生未知错误：{e}", exc_info=True)
        return []


# --- Streamlit 页面布局 ---

def main():
    logging.info("Streamlit 应用启动。")
    st.set_page_config(page_title="视频字幕片段查找器", layout="wide", initial_sidebar_state="collapsed")

    st.title("🎬 视频字幕片段查找器")
    st.markdown("输入一句台词或字幕，此工具将查找包含该文本的YouTube视频，并直接定位到相关片段，方便您进行剪辑。")

    youtube_service = get_youtube_service()
    if not youtube_service:
        logging.warning("YouTube 服务未成功初始化，应用停止。")
        st.stop()

    # 使用表单来组织输入和提交按钮
    with st.form(key='search_form'):
        search_query = st.text_input(
            "输入您要查找的字幕文本:",
            placeholder="例如：'我真是个天才' 或 'this is where the fun begins'"
        )
        submit_button = st.form_submit_button(label='🔍 开始查找')

    if submit_button and search_query:
        logging.info(f"表单已提交，查询词：'{search_query}'")
        with st.spinner('正在搜索视频并分析字幕，请稍候...'):
            videos = search_videos(youtube_service, search_query, max_results=5)  # 同样，我改回了 5

            if not videos:
                logging.warning("search_videos 返回了空列表。")
                st.warning("未能根据您的输入找到相关视频，请尝试更换关键词。")
                st.stop()

            logging.debug(f"搜索到的视频列表 (原始数据): {videos}")

            results_found_in_any_video = False

            logging.info(f"开始遍历 {len(videos)} 个搜索到的视频...")
            for i, video in enumerate(videos):
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logging.debug(f"--- 正在处理第 {i + 1} 个视频 ---")
                logging.debug(f"  ID: {video_id}")
                logging.debug(f"  标题: {video_title}")

                segments = find_subtitle_in_transcript(video_id, search_query)
                logging.debug(f"  find_subtitle_in_transcript 返回 {len(segments)} 个片段。")

                if segments:
                    results_found_in_any_video = True
                    logging.info(f"  视频 {video_id} 找到 {len(segments)} 个匹配项，将显示在UI上。")
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
                else:
                    logging.debug(f"  视频 {video_id} 未找到匹配片段。")

            if not results_found_in_any_video:
                logging.warning("所有视频均未找到匹配的字幕。这是显示“未找到”信息的原因。")
                st.info("已搜索相关视频，但未在其可用字幕中找到您输入的文本。可能是视频没有字幕，或文本不匹配。")


if __name__ == "__main__":
    main()
