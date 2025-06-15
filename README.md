
# 🎬 YouTube Playlist Transcript RAG App

A powerful Streamlit application that lets you chat with multiple YouTube videos using AI. Extract transcripts from playlists, channel searches, or individual videos, and ask questions using Retrieval-Augmented Generation (RAG).

## ✨ Features


- **Multiple Input Types**: Support for single videos, playlists, and channel searches
- **Automatic Transcript Extraction**: Uses `youtube_transcript_api` and AssemblyAI fallback
- **Smart Video Discovery**: Extracts video URLs from playlist and search pages using `yt_dlp`
- **Cookie File Upload Support**: Use age-restricted/private videos by uploading `cookies.txt`
- **RAG-Powered Chat**: Ask questions and get AI responses based on video content
- **Suggested Prompts**: Quick-start prompts to help users explore content
- **Progress Tracking**: Real-time progress updates during processing
- **Source Attribution**: See which videos your answers come from
- **Downloadable Results**: Export processing summaries and transcripts

## 🚀 Quick Start

### 1. Installation & Setup

## Note: If you encounter issues related to ffmpeg, please ensure it is installed correctly.
You can download ffmpeg (version 7.1.1 Windows 64-bit) from:
(https://github.com/vikas-kashyap97/Youtube_script/tree/main/ffmpeg-7.1.1-essentials_build)

```bash
# Clone the repository
git clone https://github.com/vikas-kashyap97/Youtube_script.git
cd Youtube_script

# Make virtual .env variables and activate them
python -m venv venv 
venv\Scripts\activate  

# Install dependencies
pip install -r requirements.txt

# Set your GOOGLE_API_KEY and ASSEMBLYAI_API_KEY

echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
echo "ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here" > .env
```

### 2. Run the App

```bash
streamlit run app.py
```

## 📱 Usage

### Step 0: Upload Cookies for Authenticated Video Access

1. Install this Chrome extension: [cookies.txt LOCALLY 0.7.0](https://chromewebstore.google.com/search/cookies.txt%20LOCALLY%200.7.0?hl=en-US&utm_source=ext_sidebar)
2. Visit `youtube.com`, login, click the extension, and export cookies.
3. Rename the file to `cookies.txt` and upload it inside the app (Sidebar Step 0).

### Step 1: Enter YouTube URL

The app supports these formats:

```
https://www.youtube.com/watch?v=VIDEO_ID
https://www.youtube.com/playlist?list=PLAYLIST_ID
https://www.youtube.com/@channel/search?query=search_term
```

### Step 2: Configure & Process

- Set max videos (1–50)
- Click "🚀 Process Videos"

### Step 3: Chat with Videos

- Use the chatbox or suggested prompts
- Get detailed AI answers with source attribution

## 🛠️ Technical Architecture

### Backend Components (`backend.py`)

- `get_youtube_transcript()` — fallback from YouTubeTranscriptAPI to AssemblyAI
- `build_vectorstore_from_multiple_videos()` — builds embeddings & vectorstore
- `extract_video_links_from_playlist/search_url()` — collects video URLs with `yt_dlp`
- `detect_ffmpeg_path()` — detects ffmpeg for audio conversion

### Frontend Components (`app.py`)

- Cookie uploader for `cookies.txt`
- Sidebar controls for YouTube URL, max video selection
- Chat tab with streaming answers and suggested prompts
- Transcript tab with download option
- Analytics tab with success/failure stats

## ⚙️ Configuration Options

### Change Max Videos

```python
# app.py
max_videos = st.slider("Maximum videos to process:", 1, 50, value=10)
```

### Embedding & Retrieval

```python
# backend.py
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
```

## 🔍 Troubleshooting

- **"No captions available"**: Try another video or upload cookies.
- **"Error extracting video links"**: URL not supported? Use direct playlist/video URLs.
- **Age-restricted videos**: Upload `cookies.txt` to fix.
- **Memory/Timeouts**: Reduce video count or chunk size.

Enable debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Deployment

### Docker (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 📄 License

This project is licensed under the MIT License - see the [MIT License](LICENSE) file for details

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain)
- [Streamlit](https://streamlit.io/)
- [AssemblyAI](https://www.assemblyai.com/)
- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Google Gemini](https://deepmind.google/technologies/gemini/)

---

