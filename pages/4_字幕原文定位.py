import streamlit as st
from googleapiclient.discovery import build
# 我们现在需要导入 NoTranscriptFound 来辅助查找
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
import sys

# ------------------- 页面配置 -------------------
st.set_page_config(layout="wide", page_title="视频片段定位器", page_icon="🎬")


# ------------------- 核心功能函数 (带缓存) -------------------

# 我们把缓存加回来，因为网络已经通了
@st.cache_data(ttl=3600)
def search_youtube_videos(api_key, query, max_results=15):  # <-- 核心修正 1: 将 10000 改为 15 (API最大50)
    """使用 YouTube API 搜索与查询相关的、带字幕的视频。"""
    print(f"\n[DEBUG] 正在调用 search_youtube_videos 函数...")
    print(f"[DEBUG] 搜索词: {query}, max_results: {max_results}")
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            videoCaption='any',  # 保持 'any'，我们依赖后续的字幕库来过滤
            maxResults=max_results
        )
        response = request.execute()
        # print(f"[DEBUG] YouTube API 原始响应: {response}") # 日志太长，暂时注释
        items = response.get('items', [])
        print(f"[DEBUG] API 返回了 {len(items)} 个视频。")
        return items
    except Exception as e:
        print(f"[DEBUG] !!! YouTube API 访问出错: {e}", file=sys.stderr)
        st.error(f"无法连接到 YouTube API。请检查你的 API 密钥和网络连接。错误详情: {e}")
        return []


@st.cache_data(ttl=3600)
def find_keywords_in_transcript(video_id, query):
    """在字幕中查找包含所有关键词的片段。"""
    print(f"\n[DEBUG] ---- 正在调用 find_keywords_in_transcript ----")
    print(f"[DEBUG] 视频 ID: {video_id}")
    print(f"[DEBUG] 搜索词: {query}")
    try:
        keywords = [word.lower() for word in query.split()]
        if not keywords:
            print("[DEBUG] 关键词列表为空，已跳过。")
            return None

        # --- 核心修正：使用兼容旧版本的方法 ---
        print("[DEBUG] 正在尝试获取字幕 (使用 list_transcripts 兼容模式)...")

        # 步骤 1: 列出所有可用的字幕
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print(f"[DEBUG] 成功 list_transcripts，找到 {len(transcript_list)} 个字幕条目。")

        # 步骤 2: 尝试找到一个我们支持的语言（中文优先，其次英文）
        transcript_to_fetch = None
        supported_languages = ['zh-CN', 'zh-Hans', 'zh', 'en', 'en-US']

        try:
            # 优先查找用户手动上传的、准确的字幕
            transcript_to_fetch = transcript_list.find_transcript(supported_languages)
            print(f"[DEBUG] 找到了手动字幕: {transcript_to_fetch.language_code}")
        except NoTranscriptFound:
            print("[DEBUG] 未找到手动上传的中/英文字幕，尝试查找自动生成字幕...")
            # 如果没有，再尝试查找自动生成的
            for tr in transcript_list:
                if tr.is_generated and tr.language_code in supported_languages:
                    transcript_to_fetch = tr
                    print(f"[DEBUG] 找到了自动字幕: {transcript_to_fetch.language_code}")
                    break

        # 如果连自动生成的都找不到
        if not transcript_to_fetch:
            print("[DEBUG] 找到了字幕列表，但没有可用的中/英文字幕。")
            return None  # 无法分析，返回 None

        print(f"[DEBUG] 最终选择字幕，语言: {transcript_to_fetch.language_code}")

        # 步骤 3: 获取该字幕的实际内容
        transcript_data = transcript_to_fetch.fetch()
        print(f"[DEBUG] 成功获取字幕内容，共 {len(transcript_data)} 段。")

        # 步骤 4: 循环遍历获取到的字幕数据
        for i, segment in enumerate(transcript_data):
            segment_text_lower = segment['text'].lower()

            if all(keyword in segment_text_lower for keyword in keywords):
                print(f"[DEBUG] 找到匹配！在片段 {i} 中。")
                context_start_index = max(0, i - 1)
                context_end_index = min(len(transcript_data) - 1, i + 1)
                full_context = " ".join(
                    [transcript_data[j]['text'] for j in range(context_start_index, context_end_index + 1)])

                highlighted_context = full_context
                for keyword in query.split():
                    highlighted_context = re.sub(f"({re.escape(keyword)})", r"**\1**", highlighted_context,
                                                 flags=re.IGNORECASE)

                match_data = {
                    "start_time": int(segment['start']),
                    "context": f"...{highlighted_context}..."
                }
                print(f"[DEBUG] 构造的返回数据: {match_data}")
                return match_data

        print(f"[DEBUG] 遍历完所有字幕，未找到匹配项。")
        return None  # <-- 未找到关键词，返回 None

    except (TranscriptsDisabled):
        print(f"[DEBUG] !!! 视频 {video_id} 的字幕已被禁用 (TranscriptsDisabled)。")
        return "TranscriptsDisabled"  # 这个是正确的

    # --- 核心修正 2: 在通用 Exception 之前捕获 NoTranscriptFound ---
    # 这会捕获 list_transcripts(video_id) 抛出的错误，意味着视频*根本没有*字幕
    except (NoTranscriptFound):
        print(f"[DEBUG] !!! 视频 {video_id} 没有任何字幕 (NoTranscriptFound)。")
        return None  # 返回 None (无匹配)，而不是 "TranscriptsDisabled" (错误)

    except Exception as e:
        # 捕获其他可能的错误
        print(f"[DEBUG] !!! 获取字幕时发生未知错误: {e}", file=sys.stderr)
        return "TranscriptsDisabled"  # 统一归为字幕不可用


# ------------------- Streamlit 界面布局 -------------------

st.title("🎬 视频片段智能定位器")
st.markdown("输入一段文字，程序将自动从 YouTube 中查找包含这段文字的视频，并直接跳转到该时间点播放。")
st.markdown("---")

print("\n[DEBUG] Streamlit 脚本开始执行。")

try:
    API_KEY = st.secrets["youtube_key"]
    print(f"[DEBUG] 成功从 Streamlit Secrets 加载 API 密钥。")
    # print(f"[DEBUG] 密钥尾号: ...{API_KEY[-4:]}") # 安全起见，注释掉
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

    # 注意：这里调用时没有传递 max_results，所以会使用函数定义中的默认值 15
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
            print(f"\n[DEBUG] --- ---------------------- ---")
            print(f"[DEBUG] --- 正在处理视频 {i + 1}/{len(videos)} ---")
            print(f"[DEBUG] --- 视频标题: {video_title}")
            print(f"[DEBUG] --- 视频 ID: {video_id}")

            progress_text = f"分析中 ({i + 1}/{len(videos)}): {video_title}"
            progress_bar.progress((i + 1) / len(videos), text=progress_text)

            match_data = find_keywords_in_transcript(video_id, search_query)
            print(f"[DEBUG] find_keywords_in_transcript 返回: {match_data}")

            if match_data == "TranscriptsDisabled":
                with results_placeholder.expander(f"⚠️ **{video_title}** - 字幕不可用或受限"):
                    st.write("无法分析此视频，因为它关闭了字幕功能或不提供可访问的字幕。")
                continue

            # --- 修正：检查 match_data 是否为 None ---
            # 如果 match_data 是 None (无字幕 或 无关键词匹配)，我们也应该 continue
            if match_data is None:
                print("[DEBUG] 无可用字幕或未找到关键词，跳过此视频。")
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
                print("[DEBUG] 已找到匹配，停止搜索循环。")
                break  # 找到一个就停止

        # 循环结束后的检查
        if not found_match:
            print("[DEBUG] === 最终结论：遍历了所有视频，但未找到匹配。 ===")
            progress_bar.empty()
            status_placeholder.warning("分析了所有相关视频，但未在字幕中找到同时包含所有关键词的片段。请尝试更简单、更核心的关键词。")

elif search_button and not search_query:
    st.warning("请输入你要搜索的内容。")
