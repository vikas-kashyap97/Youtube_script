# 🎬 YouTube Playlist Transcript RAG App

A powerful Streamlit application that lets you chat with multiple YouTube videos using AI. Extract transcripts from playlists, channel searches, or individual videos, and ask questions using Retrieval-Augmented Generation (RAG).

## ✨ Features

- **Multiple Input Types**: Support for single videos, playlists, and channel searches
- **Automatic Transcript Extraction**: Uses `youtube_transcript_api` to get English captions
- **Smart Video Discovery**: Extracts video URLs from playlist and search pages
- **RAG-Powered Chat**: Ask questions and get AI responses based on video content
- **Progress Tracking**: Real-time progress updates during processing
- **Source Attribution**: See which videos your answers come from
- **Configurable Limits**: Set maximum number of videos to process

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd youtube-playlist-rag

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Google API Key
# Get your key from: https://aistudio.google.com/app/apikey
```

### 3. Run the App

```bash
streamlit run app.py
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

### Streamlit Secrets (Alternative)

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = "your_google_api_key_here"
```

## 📱 Usage

### Step 1: Enter YouTube URL

The app supports three types of URLs:

**Single Video:**
```
https://www.youtube.com/watch?v=VIDEO_ID
```

**Playlist:**
```
https://www.youtube.com/playlist?list=PLAYLIST_ID
```

**Channel Search:**
```
https://www.youtube.com/@channel/search?query=search_term
```

### Step 2: Configure Settings

- Set the maximum number of videos to process (1-50)
- Click "Process Videos" to start

### Step 3: Chat with Videos

Once processing is complete:
- Ask questions in natural language
- Get AI-powered answers based on video transcripts
- View source attribution for each answer

## 🛠️ Technical Architecture

### Backend Components (`backend.py`)

- **`get_youtube_video_id()`**: Extract video IDs from various YouTube URL formats
- **`get_youtube_transcript()`**: Fetch English transcripts using YouTube API
- **`extract_video_links_from_search_url()`**: Scrape video URLs from channel search pages
- **`extract_video_links_from_playlist()`**: Extract videos from playlist pages
- **`build_vectorstore_from_multiple_videos()`**: Process multiple videos into FAISS vector store
- **`process_youtube_video()`**: Handle single video processing with embeddings

### Frontend Components (`app.py`)

- **Sidebar Interface**: URL input, settings, and processing controls
- **Progress Tracking**: Real-time updates during video processing
- **Chat Interface**: Interactive Q&A with source attribution
- **Results Display**: Processing status and video statistics

### Key Technologies

- **Streamlit**: Web application framework
- **LangChain**: RAG pipeline and document processing
- **Google Gemini**: AI model for embeddings and chat responses
- **FAISS**: Vector database for similarity search
- **BeautifulSoup**: Web scraping for video discovery
- **YouTube Transcript API**: Automated caption extraction

## 📋 Supported URL Formats

### ✅ Supported
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/playlist?list=PLAYLIST_ID`
- `https://www.youtube.com/@channel/search?query=TERM`
- `https://www.youtube.com/c/channel/search?query=TERM`

### ❌ Not Supported
- Private videos or playlists
- Videos without English captions
- Age-restricted content
- Live streams

## ⚙️ Configuration Options

### Video Processing Limits

```python
# In app.py, adjust the slider range
max_videos = st.slider(
    "Maximum videos to process:",
    min_value=1, 
    max_value=50,  # Adjust this limit
    value=10
)
```

### Chunk Size Settings

```python
# In backend.py, modify text splitting
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,    # Adjust chunk size
    chunk_overlap=200   # Adjust overlap
)
```

### Retrieval Parameters

```python
# Modify number of chunks retrieved
retriever = vector_store.as_retriever(
    search_type="similarity", 
    search_kwargs={"k": 5}  # Adjust k value
)
```

## 🔍 Troubleshooting

### Common Issues

**1. "No captions available" Error**
- The video doesn't have English captions
- Try videos with auto-generated or manual captions

**2. "Error extracting video links"**
- The URL format might not be supported
- Try copying the URL directly from YouTube

**3. API Rate Limiting**
- Reduce the number of videos processed
- Add delays between requests (already implemented)

**4. Memory Issues**
- Reduce chunk size or maximum videos
- Process videos in smaller batches

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Deployment

### Local Development

```bash
streamlit run app.py
```

### Streamlit Cloud

1. Push code to GitHub
2. Connect repository to Streamlit Cloud
3. Add secrets in Streamlit Cloud dashboard
4. Deploy automatically

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api)
- [LangChain](https://github.com/langchain-ai/langchain)
- [Streamlit](https://streamlit.io/)
- [Google Gemini](https://deepmind.google/technologies/gemini/)

## 📞 Support

For issues and questions:
- Check the [Issues](../../issues) page
- Review the troubleshooting section above
- Ensure your Google API key is valid and has quota

---

**Built with ❤️ using Streamlit, LangChain, and Google Gemini**