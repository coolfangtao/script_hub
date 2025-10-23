# app.py (版本 3 - 最终修正版 + 调试打印)

import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
import sys

# ------------------- 页面配置 -------------------
st.set_page_config(layout="wide", page_title="视频片段定位器", page_icon="🎬")


# ------------------- 核心功能函数 (带缓存) -------------------

# 注意：为了调试，我们暂时禁用缓存，以便每次都能看到 API 的真实响应
# @st.cache_data(ttl=3600)
def search_youtube_videos(api_key, query, max_results=5):
    """使用 YouTube API 搜索与查询相关的、带字幕的视频。"""
    print(f"\n[DEBUG] 正在调用 search_youtube_videos 函数...")
    print(f"[DEBUG] 搜索词: {query}")
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
        print(f"[DEBUG] YouTube API 原始响应: {response}")
        items = response.get('items', [])
        print(f"[DEBUG] API 返回了 {len(items)} 个视频。")
        return items
    except Exception as e:
        print(f"[DEBUG] !!! YouTube API 访问出错: {e}", file=sys.stderr)
        st.error(f"无法连接到 YouTube API。请检查你的 API 密钥和网络连接。错误详情: {e}")
        return []


# @st.cache_data(ttl=3600)
def find_keywords_in_transcript(video_id, query):
    """在字幕中查找包含所有关键词的片段。"""
    print(f"\n[DEBUG] ---- 正在调用 find_keywords_in_transcript ----")
    print(f"[DEBUG] 视频 ID: {video_id}")
    print(f"[DEBUG] 搜索词: {query}")
    try:
        keywords = [word.lower() for word in query.split()]
        print(f"[DEBUG] 生成的关键词列表: {keywords}")

        if not keywords:
            print("[DEBUG] 关键词列表为空，已跳过。")
            return None

        print("[DEBUG] 正在尝试获取字幕...")
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-CN', 'zh-Hans', 'zh', 'en'])
        print(f"[DEBUG] 成功获取字幕，共 {len(transcript)} 段。")

        for i, segment in enumerate(transcript):
            segment_text_lower = segment['text'].lower()

            # 检查所有关键词是否都在这段字幕中
            all_keywords_found = all(keyword in segment_text_lower for keyword in keywords)

            # (可选) 如果想看详细的字幕搜索过程，可以取消下面这行的注释
            # print(f"[DEBUG] 检查片段 {i}: '{segment_text_lower}'. 结果: {all_keywords_found}")

            if all_keywords_found:
                print(f"[DEBUG] 找到匹配！在片段 {i} 中。")
                context_start_index = max(0, i - 1)
                context_end_index = min(len(transcript) - 1, i + 1)
                full_context = " ".join(
                    [transcript[j]['text'] for j in range(context_start_index, context_end_index + 1)])

                highlighted_context = full_context
                for keyword in query.split():  # 使用原始query里的词来高亮，保持大小写
                    highlighted_context = re.sub(f"({re.escape(keyword)})", r"**\1**", highlighted_context,
                                                 flags=re.IGNORECASE)

                match_data = {
                    "start_time": int(segment['start']),
                    "context": f"...{highlighted_context}..."
                }
                print(f"[DEBUG] 构造的返回数据: {match_data}")
                return match_data

        print(f"[DEBUG] 遍历完所有字幕，未找到匹配项。")
        return None

    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"[DEBUG] !!! 字幕不可用 (TranscriptsDisabled 或 NoTranscriptFound)")
        return "TranscriptsDisabled"
    except Exception as e:
        print(f"[DEBUG] !!! 获取字幕时发生未知错误: {e}", file=sys.stderr)
        return None


# ------------------- Streamlit 界面布局 -------------------

st.title("🎬 视频片段智能定位器")
st.markdown("输入一段文字，程序将自动从 YouTube 中查找包含这段文字的视频，并直接跳转到该时间点播放。")
st.markdown("---")

print("\n[DEBUG] Streamlit 脚本开始执行。")

try:
    API_KEY = st.secrets["youtube_key"]
    print(f"[DEBUG] 成功从 Streamlit Secrets 加载 API 密钥。")
    # 为了安全，只打印密钥的最后4位
    print(f"[DEBUG] 密钥尾号: ...{API_KEY[-4:]}")
except (KeyError, FileNotFoundError):
    print("[DEBUG] !!! 严重错误：未在 Streamlit Secrets 中找到 'youtube_key'。", file=sys.stderr)
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
    print(f"\n[DEBUG] ====== 用户点击了搜索 ====== ")
    print(f"[DEBUG] 完整搜索词: '{search_query}'")

    status_placeholder = st.empty()
    status_placeholder.info("第一步：正在 YouTube 上搜索相关视频...")
    videos = search_youtube_videos(API_KEY, search_query)

    if not videos:
        print("[DEBUG] 结论：未能找到任何相关视频。")
        status_placeholder.warning("未能找到任何相关视频。请尝试更换关键词。")
    else:
        print(f"[DEBUG] 结论：找到 {len(videos)} 个视频，准备开始分析字幕。")
        status_placeholder.info(f"第二步：找到了 {len(videos)} 个视频，正在逐一分析字幕...")

        found_match = False
        results_placeholder = st.container()
        progress_bar = st.progress(0, text="分析进度")

        for i, video in enumerate(videos):
            video_id = video['id']['videoId']
            video_title = video['snippet']['title']
            print(f"\n[DEBUG] --- 正在处理视频 {i + 1}/{len(videos)} ---")
            print(f"[DEBUG] 视频标题: {video_title}")
            print(f"[DEBUG] 视频 ID: {video_id}")

            progress_text = f"分析中 ({i + 1}/{len(videos)}): {video_title}"
            progress_bar.progress((i + 1) / len(videos), text=progress_text)

            match_data = find_keywords_in_transcript(video_id, search_query)
            print(f"[DEBUG] find_keywords_in_transcript 返回: {match_data}")

            if match_data == "TranscriptsDisabled":
                with results_placeholder.expander(f"⚠️ **{video_title}** - 字幕不可用或受限"):
                    st.write("无法分析此视频，因为它关闭了字幕功能或不提供可访问的字幕。")
                continue

            if isinstance(match_data, dict):
                found_match = True
                print(f"[DEBUG] === 匹配成功！已找到结果！===")
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
            print("[DEBUG] === 最终结论：遍历了所有视频，但未找到匹配。 ===")
            progress_bar.empty()
            status_placeholder.warning("分析了所有相关视频，但未在字幕中找到同时包含所有关键词的片段。请尝试更简单、更核心的关键词。")

elif search_button and not search_query:
    st.warning("请输入你要搜索的内容。")
