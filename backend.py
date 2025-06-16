import re
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs
import time
import logging
import os
import tempfile
import assemblyai as aai
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

# Load environment variables
load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
os.environ["STREAMLIT_WATCHDOG"] = "none"

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Utility Functions ===

def detect_ffmpeg_path() -> str:
    project_root = os.getcwd()
    default_paths = [
        os.path.join(project_root, "ffmpeg-7.1.1-essentials_build", "bin"),
        os.path.join(project_root, "ffmpeg", "bin"),
    ]

    logger.info(f"🔍 Checking these paths: {default_paths}")

    for path in default_paths:
        logger.info(f"📁 Looking inside: {path}")
        try:
            logger.info(f"📄 Files: {os.listdir(path)}")
        except FileNotFoundError:
            logger.warning(f"❌ Path not found: {path}")
            continue

        ffmpeg_exec = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        if os.path.isfile(os.path.join(path, ffmpeg_exec)):
            logger.info(f"✅ FFmpeg found at: {path}")
            return path

    logger.warning("⚠️ FFmpeg not found in default paths.")
    return ""



def get_youtube_video_id(url: str) -> str:
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        if 'v' in query_params:
            return query_params['v'][0]
    if 'youtu.be' in parsed_url.netloc:
        return parsed_url.path.lstrip('/')
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

def assemblyai_transcribe_youtube(url: str) -> str:
    try:
        video_id = get_youtube_video_id(url)
        if not video_id:
            return "Error: Invalid YouTube URL"

        ffmpeg_path = detect_ffmpeg_path()
        cookie_file_path = "cookies.txt" if os.path.isfile("cookies.txt") else None

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'ffmpeg_location': ffmpeg_path if ffmpeg_path else None,
                'cookiefile': cookie_file_path,
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_path = os.path.join(tmpdir, f"{video_id}.mp3")

            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_path)
            return transcript.text
    except Exception as e:
        return f"Error (AssemblyAI): {e}"

def get_youtube_transcript(url: str) -> str:
    try:
        video_id = get_youtube_video_id(url)
        if not video_id:
            return "Error: Invalid YouTube URL"

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        except:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en-US"])
            except:
                try:
                    available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                    transcript_obj = available_transcripts.find_transcript(["en", "en-US"])
                    transcript_list = transcript_obj.fetch()
                except:
                    logger.warning(f"🔁 Falling back to AssemblyAI for: {url}")
                    return assemblyai_transcribe_youtube(url)

        if isinstance(transcript_list, list) and all('text' in item for item in transcript_list):
            return " ".join(chunk["text"] for chunk in transcript_list)
        return "Error: Unexpected transcript format received."

    except TranscriptsDisabled:
        return assemblyai_transcribe_youtube(url)
    except Exception as e:
        return f"Error: {e}"

# === Video Extraction Functions ===

def extract_video_links_from_search_url(search_url: str, max_videos: int = 10) -> List[Tuple[str, str]]:
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'dump_single_json': True,
            'force_generic_extractor': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get('entries', [])
            video_links = []
            for entry in entries[:max_videos]:
                video_id = entry.get('id')
                title = entry.get('title')
                if video_id and title:
                    video_links.append((f"https://www.youtube.com/watch?v={video_id}", title))
            return video_links
    except Exception as e:
        logger.error(f"Error using yt_dlp to extract videos: {e}")
        return []

def extract_video_links_from_playlist(playlist_url: str, max_videos: int = 20) -> List[Tuple[str, str]]:
    try:
        playlist_id = playlist_url.split('list=')[1].split('&')[0] if 'list=' in playlist_url else None
        if not playlist_id:
            logger.error("No playlist ID found in URL")
            return []

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(playlist_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        video_links = []

        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'ytInitialData' in script.string:
                matches = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"[^}]*"title":\{"runs":\[\{"text":"([^"]+)"', script.string)
                for video_id, title in matches:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    if not any(existing_url == video_url for existing_url, _ in video_links):
                        video_links.append((video_url, title))
                        if len(video_links) >= max_videos:
                            break
                if video_links:
                    break
        return video_links
    except Exception as e:
        logger.error(f"Error extracting playlist links: {e}")
        return []

# === Processing and Embeddings ===

def process_youtube_video(url: str, google_api_key: str) -> Dict[str, Any]:
    transcript = get_youtube_transcript(url)
    if transcript.startswith("Error:") or transcript.startswith("No captions available"):
        return {"error": transcript}

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.create_documents([transcript])
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)
    vector_store = FAISS.from_documents(chunks, embeddings)
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    return {
        "transcript": transcript,
        "chunks": chunks,
        "vector_store": vector_store,
        "retriever": retriever
    }

def build_vectorstore_from_multiple_videos(video_urls: List[Tuple[str, str]], google_api_key: str, progress_callback=None) -> Dict[str, Any]:
    all_chunks = []
    processing_results = []

    logger.info(f"Starting to process {len(video_urls)} videos")

    for i, (url, title) in enumerate(video_urls):
        logger.info(f"Processing {i+1}/{len(video_urls)}: {title}")
        if progress_callback:
            progress_callback(i, len(video_urls), f"Processing: {title}")

        transcript = get_youtube_transcript(url)
        if transcript.startswith("Error:") or transcript.startswith("No captions"):
            logger.warning(f"Transcript failed for {title}")
            processing_results.append({"url": url, "title": title, "status": "failed", "error": transcript})
            continue

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.create_documents([transcript])
        for chunk in chunks:
            chunk.metadata = {"source": url, "title": title, "video_index": i}
        all_chunks.extend(chunks)
        processing_results.append({"url": url, "title": title, "status": "success", "chunks_count": len(chunks)})
        time.sleep(0.5)

    if not all_chunks:
        return {"error": "No transcripts processed", "processing_results": processing_results}

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)
    if progress_callback:
        progress_callback(len(video_urls), len(video_urls), "Creating embeddings...")
    vector_store = FAISS.from_documents(all_chunks, embeddings)
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    return {
        "retriever": retriever,
        "vector_store": vector_store,
        "chunks": all_chunks,
        "processing_results": processing_results,
        "total_chunks": len(all_chunks),
        "successful_videos": len([r for r in processing_results if r["status"] == "success"])
    }

# === Question Context ===

def get_context_from_question(retriever, question: str, k: int = 5) -> str:
    docs = retriever.get_relevant_documents(question)
    return "\n".join([doc.page_content for doc in docs])

def detect_url_type(url: str) -> str:
    if '/watch?v=' in url and 'list=' not in url:
        return "single_video"
    elif 'list=' in url:
        return "playlist"
    elif '/search?' in url or ('/@' in url and 'search' in url):
        return "channel_search"
    return "unknown"

# === Test ===
if __name__ == "__main__":
    search_url = "https://www.youtube.com/@pinkyshah19/search?query=multi"
    video_links = extract_video_links_from_search_url(search_url, max_videos=5)
    print(f"Found {len(video_links)} videos.")
    result = build_vectorstore_from_multiple_videos(video_links, google_api_key=os.getenv("GOOGLE_API_KEY"))
    print(result.get("error", f"Processed {result['successful_videos']} videos"))
