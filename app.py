import streamlit as st
import backend
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import time
import json
from datetime import datetime

os.environ["STREAMLIT_WATCHDOG"] = "none"

# Load environment variables
load_dotenv()

# Configuration
st.set_page_config(
    page_title="YouTube Transcript RAG Chat",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get API key from secrets or environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Custom CSS for better UI
st.markdown("""
<style>
    .transcript-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff6b6b;
        margin: 10px 0;
        max-height: 400px;
        overflow-y: auto;
    }
    .video-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 5px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    .success-card {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
    }
    .error-card {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎬 YouTube Transcript RAG Chat")
st.markdown("### Analyze and chat with YouTube content using AI")

# --- Session State Initialization ---
if 'retriever' not in st.session_state:
    st.session_state['retriever'] = None
if 'chunks' not in st.session_state:
    st.session_state['chunks'] = None
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'videos_processed' not in st.session_state:
    st.session_state['videos_processed'] = False
if 'processing_results' not in st.session_state:
    st.session_state['processing_results'] = []
if 'total_chunks' not in st.session_state:
    st.session_state['total_chunks'] = 0
if 'successful_videos' not in st.session_state:
    st.session_state['successful_videos'] = 0
if 'transcripts' not in st.session_state:
    st.session_state['transcripts'] = []
if 'show_transcripts' not in st.session_state:
    st.session_state['show_transcripts'] = False

# --- Helper Functions ---
def display_transcript(transcript, title, max_length=1000):
    """Display transcript in a styled box with expand/collapse"""
    preview = transcript[:max_length] + "..." if len(transcript) > max_length else transcript
    
    with st.expander(f"📝 Transcript: {title}", expanded=False):
        st.markdown(f'<div class="transcript-box">{preview}</div>', unsafe_allow_html=True)
        if len(transcript) > max_length:
            if st.button(f"Show Full Transcript - {title}", key=f"show_full_{title}"):
                st.text_area("Full Transcript", transcript, height=300, key=f"full_transcript_{title}")

def format_chat_message(message, role):
    """Format chat messages with better styling"""
    if role == "user":
        st.markdown(f"**You:** {message}")
    else:
        st.markdown(f"**AI:** {message}")

# --- Sidebar: Video Processing Section ---
with st.sidebar:
    st.header("🔧 Step 1: Process Videos")
    
    # URL input with validation
    youtube_url = st.text_input(
        "Enter YouTube URL:",
        placeholder="Paste your YouTube URL here...",
        help="Supports: Single videos, playlists, and channel searches"
    )
    
    # URL validation
    if youtube_url:
        url_type = backend.detect_url_type(youtube_url)
        if url_type == "unknown":
            st.error("❌ Invalid URL format. Please enter a valid YouTube URL.")
        else:
            st.success(f"✅ Detected: {url_type.replace('_', ' ').title()}")
    
    # Max videos setting
    max_videos = st.slider(
        "Maximum videos to process:",
        min_value=1, 
        max_value=50, 
        value=10,
        help="Limit to prevent API quota issues and long processing times"
    )
    
    # Estimated processing time
    if youtube_url:
        st.info(f"⏱️ Estimated processing time: {max_videos * 3}-{max_videos * 5} seconds")
    
    # Process button
    if st.button("🚀 Process Videos", type="primary", disabled=not youtube_url or not GOOGLE_API_KEY):
        if not GOOGLE_API_KEY:
            st.error("❌ Google API Key not found. Please set it in .env file or Streamlit secrets.")
        else:
            url_type = backend.detect_url_type(youtube_url)
            
            with st.spinner("🔍 Analyzing URL and extracting videos..."):
                if url_type == "single_video":
                    st.info("📹 Processing single video...")
                    video_urls = [(youtube_url, "Single Video")]
                    
                elif url_type == "playlist":
                    st.info("📋 Extracting videos from playlist...")
                    video_urls = backend.extract_video_links_from_playlist(youtube_url, max_videos)
                    
                elif url_type == "channel_search":
                    st.info("🔍 Extracting videos from channel search...")
                    video_urls = backend.extract_video_links_from_search_url(youtube_url, max_videos)
                    
                else:
                    st.error("❌ Unsupported URL format")
                    video_urls = []
            
            if not video_urls:
                st.error("❌ No videos found. Please check the URL and try again.")
            else:
                st.success(f"✅ Found {len(video_urls)} videos to process")
                
                # Show video list
                with st.expander("📋 Videos to Process"):
                    for i, (url, title) in enumerate(video_urls[:5]):  # Show first 5
                        st.markdown(f"{i+1}. **{title[:60]}...**")
                    if len(video_urls) > 5:
                        st.markdown(f"... and {len(video_urls) - 5} more videos")
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total, message):
                    progress = current / total if total > 0 else 0
                    progress_bar.progress(progress)
                    status_text.text(f"Progress: {current}/{total} - {message}")
                
                # Process videos
                with st.spinner("🔄 Processing videos and creating knowledge base..."):
                    start_time = time.time()
                    result = backend.build_vectorstore_from_multiple_videos(
                        video_urls, 
                        GOOGLE_API_KEY, 
                        progress_callback=update_progress
                    )
                    processing_time = time.time() - start_time
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                    st.session_state['videos_processed'] = False
                else:
                    st.success(f"✅ Processing completed in {processing_time:.1f} seconds!")
                    
                    # Update session state
                    st.session_state['retriever'] = result['retriever']
                    st.session_state['chunks'] = result['chunks']
                    st.session_state['processing_results'] = result['processing_results']
                    st.session_state['total_chunks'] = result['total_chunks']
                    st.session_state['successful_videos'] = result['successful_videos']
                    st.session_state['transcripts'] = result.get('transcripts', [])
                    st.session_state['videos_processed'] = True
                    st.session_state['chat_history'] = []  # Clear previous chat
                    
                    # Show summary metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("✅ Videos Processed", result['successful_videos'])
                    with col2:
                        st.metric("📝 Text Chunks", result['total_chunks'])
                    
                    st.balloons()  # Celebration animation
    
    # Show processing results
    if st.session_state['videos_processed'] and st.session_state['processing_results']:
        st.subheader("📊 Processing Results")
        
        successful = [r for r in st.session_state['processing_results'] if r['status'] == 'success']
        failed = [r for r in st.session_state['processing_results'] if r['status'] == 'failed']
        
        # Success rate
        success_rate = len(successful) / len(st.session_state['processing_results']) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Detailed results
        for result in st.session_state['processing_results'][:3]:  # Show first 3
            if result['status'] == 'success':
                st.markdown(f'<div class="video-card success-card">✅ <strong>{result["title"][:40]}...</strong><br>Chunks: {result.get("chunks_count", "N/A")}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="video-card error-card">❌ <strong>{result["title"][:40]}...</strong><br>Error: {result.get("error", "Unknown")[:30]}...</div>', unsafe_allow_html=True)
        
        if len(st.session_state['processing_results']) > 3:
            with st.expander(f"Show All Results ({len(st.session_state['processing_results'])})"):
                for result in st.session_state['processing_results']:
                    status_icon = "✅" if result['status'] == 'success' else "❌"
                    st.markdown(f"{status_icon} **{result['title']}**")
                    if result['status'] == 'failed':
                        st.caption(f"Error: {result.get('error', 'Unknown error')}")
    
    # Export results
    if st.session_state['videos_processed']:
        st.subheader("💾 Export Options")
        
        if st.button("📄 Export Processing Results"):
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "total_videos": len(st.session_state['processing_results']),
                "successful_videos": st.session_state['successful_videos'],
                "results": st.session_state['processing_results']
            }
            st.download_button(
                label="Download JSON",
                data=json.dumps(results_data, indent=2),
                file_name=f"youtube_rag_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        if st.button("🗑️ Clear All Data"):
            for key in ['retriever', 'chunks', 'processing_results', 'videos_processed', 'chat_history', 'transcripts']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# --- Main Area ---
if st.session_state['videos_processed']:
    # Tab layout for better organization
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Transcripts", "📊 Analytics"])
    
    with tab1:
        st.header("Chat with Your Videos")
        
        # Quick stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card"><h3>📹</h3><p>Videos Processed</p><h2>{}</h2></div>'.format(st.session_state['successful_videos']), unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card"><h3>📝</h3><p>Text Chunks</p><h2>{}</h2></div>'.format(st.session_state['total_chunks']), unsafe_allow_html=True)
        with col3:
            avg_chunks = st.session_state['total_chunks'] / st.session_state['successful_videos'] if st.session_state['successful_videos'] > 0 else 0
            st.markdown('<div class="metric-card"><h3>📊</h3><p>Avg Chunks/Video</p><h2>{:.1f}</h2></div>'.format(avg_chunks), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Chat interface
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            for message in st.session_state['chat_history']:
                role = message['role']
                content = message['content']
                
                with st.chat_message(role):
                    st.markdown(content)
                    
                    # Show sources for assistant messages
                    if role == "assistant" and 'sources' in message and message['sources']:
                        with st.expander("📚 Sources Used"):
                            unique_sources = []
                            seen_urls = set()
                            for source in message['sources']:
                                if source['url'] not in seen_urls:
                                    unique_sources.append(source)
                                    seen_urls.add(source['url'])
                            
                            for source in unique_sources:
                                st.markdown(f"🔗 **[{source['title']}]({source['url']})**")
            
            # Suggested questions
            if not st.session_state['chat_history']:
                st.subheader("💡 Suggested Questions")
                suggestions = [
                    "What are the main topics covered in these videos?",
                    "Can you summarize the key points from all videos?",
                    "What specific techniques or methods are mentioned?",
                    "Are there any common themes across the videos?"
                ]
                
                cols = st.columns(2)
                for i, suggestion in enumerate(suggestions):
                    with cols[i % 2]:
                        if st.button(suggestion, key=f"suggestion_{i}"):
                            # Simulate user input
                            st.session_state['chat_history'].append({
                                'role': 'user', 
                                'content': suggestion
                            })
                            st.rerun()
        
        # Chat input
        user_input = st.chat_input("Ask me anything about the videos...")
        
        if user_input:
            # Add user message to chat history
            st.session_state['chat_history'].append({
                'role': 'user', 
                'content': user_input
            })
            
            # Process with AI
            with st.spinner("🤔 Analyzing your question..."):
                # Retrieve relevant context
                retriever = st.session_state['retriever']
                docs = retriever.get_relevant_documents(user_input)
                
                # Prepare context and sources
                context_parts = []
                sources = []
                
                for doc in docs:
                    context_parts.append(doc.page_content)
                    if hasattr(doc, 'metadata') and doc.metadata:
                        sources.append({
                            'title': doc.metadata.get('title', 'Unknown'),
                            'url': doc.metadata.get('source', 'Unknown')
                        })
                
                context_text = "\n".join(context_parts)
                
                # Create enhanced prompt
                prompt = PromptTemplate(
                    template="""You are an expert AI assistant analyzing YouTube video transcripts. Your task is to provide comprehensive, accurate answers based solely on the provided transcript content.

INSTRUCTIONS:
- Answer ONLY using the provided transcript context
- Be specific and detailed in your responses
- If the context doesn't contain enough information, clearly state what information is missing
- When referencing information, be specific about which part of the content it comes from
- If multiple videos are relevant, synthesize information from all sources
- Use bullet points or numbered lists when appropriate for clarity
- Maintain a helpful and engaging tone

CONTEXT FROM VIDEO TRANSCRIPTS:
{context}

USER QUESTION: {question}

COMPREHENSIVE ANSWER:""",
                    input_variables=['context', 'question']
                )
                
                final_prompt = prompt.invoke({
                    "context": context_text, 
                    "question": user_input
                })
                
                # Get LLM response
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    temperature=0.2,
                    max_tokens=None,
                    timeout=None,
                    max_retries=2,
                    google_api_key=GOOGLE_API_KEY
                )
                
                answer = llm.invoke(final_prompt)
                answer_content = answer.content.strip()
                
                # Add assistant message to chat history
                st.session_state['chat_history'].append({
                    'role': 'assistant', 
                    'content': answer_content,
                    'sources': sources
                })
            
            st.rerun()
    
    with tab2:
        st.header("📝 Video Transcripts")
        
        if st.session_state['processing_results']:
            st.markdown("Browse the full transcripts of all processed videos:")
            
            for i, result in enumerate(st.session_state['processing_results']):
                if result['status'] == 'success':
                    # Get transcript for this video
                    video_url = result['url']
                    video_title = result['title']
                    
                    with st.expander(f"📹 {video_title}", expanded=False):
                        with st.spinner("Loading transcript..."):
                            transcript = backend.get_youtube_transcript(video_url)
                            
                            if not transcript.startswith("Error"):
                                st.markdown(f'<div class="transcript-box">{transcript}</div>', unsafe_allow_html=True)
                                
                                # Transcript stats
                                word_count = len(transcript.split())
                                char_count = len(transcript)
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Words", word_count)
                                with col2:
                                    st.metric("Characters", char_count)
                                with col3:
                                    est_read_time = word_count / 200  # Average reading speed
                                    st.metric("Est. Read Time", f"{est_read_time:.1f} min")
                                
                                # Download option
                                st.download_button(
                                    label="📄 Download Transcript",
                                    data=transcript,
                                    file_name=f"{video_title[:50]}_transcript.txt",
                                    mime="text/plain",
                                    key=f"download_{i}"
                                )
                            else:
                                st.error(f"Could not load transcript: {transcript}")
        else:
            st.info("No transcripts available. Please process some videos first.")
    
    with tab3:
        st.header("📊 Processing Analytics")
        
        if st.session_state['processing_results']:
            # Success/failure analysis
            successful = [r for r in st.session_state['processing_results'] if r['status'] == 'success']
            failed = [r for r in st.session_state['processing_results'] if r['status'] == 'failed']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Success Rate")
                success_rate = len(successful) / len(st.session_state['processing_results']) * 100
                st.metric("Overall Success Rate", f"{success_rate:.1f}%")
                
                # Create a simple bar chart
                chart_data = {
                    'Status': ['Successful', 'Failed'],
                    'Count': [len(successful), len(failed)]
                }
                st.bar_chart(chart_data, x='Status', y='Count')
            
            with col2:
                st.subheader("📝 Content Analysis")
                if successful:
                    chunk_counts = [r.get('chunks_count', 0) for r in successful]
                    avg_chunks = sum(chunk_counts) / len(chunk_counts)
                    
                    st.metric("Average Chunks per Video", f"{avg_chunks:.1f}")
                    st.metric("Total Text Chunks", sum(chunk_counts))
                    st.metric("Largest Video (chunks)", max(chunk_counts))
            
            # Detailed breakdown
            st.subheader("🔍 Detailed Breakdown")
            
            for result in st.session_state['processing_results']:
                with st.expander(f"{'✅' if result['status'] == 'success' else '❌'} {result['title']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Status:** {result['status'].title()}")
                        st.write(f"**URL:** {result['url']}")
                        
                    with col2:
                        if result['status'] == 'success':
                            st.write(f"**Chunks Created:** {result.get('chunks_count', 'N/A')}")
                        else:
                            st.write(f"**Error:** {result.get('error', 'Unknown error')}")
        else:
            st.info("No analytics available. Please process some videos first.")

else:
    # Welcome screen
    st.markdown("""
    ## 👋 Welcome to YouTube Transcript RAG Chat!
    
    This app allows you to:
    - **Process YouTube content** from various sources (videos, playlists, channel searches)
    - **Extract transcripts** automatically using AI
    - **Chat with the content** using advanced AI to get insights and answers
    
    ### 🚀 Getting Started
    1. Enter a YouTube URL in the sidebar
    2. Click "Process Videos" to extract and analyze content
    3. Start chatting with your processed content!
    
    ### 📋 Supported URL Types
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🎬 Single Video**
        ```
        youtube.com/watch?v=...
        ```
        Perfect for analyzing individual videos
        """)
    
    with col2:
        st.markdown("""
        **📋 Playlist**
        ```
        youtube.com/playlist?list=...
        ```
        Process entire playlists at once
        """)
    
    with col3:
        st.markdown("""
        **🔍 Channel Search**
        ```
        youtube.com/@channel/search?query=...
        ```
        Find specific content from channels
        """)
    
    # Example URLs
    st.subheader("🔗 Try These Examples")
    
    examples = [
        ("Single Video Example", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Famous music video"),
        ("Playlist Example", "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy5Y9BYdAPuRJ8LEO-8Q4n5", "Educational content series"),
        ("Channel Search Example", "https://www.youtube.com/@3blue1brown/search?query=calculus", "Math education videos")
    ]
    
    for title, url, description in examples:
        with st.expander(title):
            st.code(url)
            st.caption(description)
            if st.button(f"Use This URL", key=title):
                st.session_state['example_url'] = url
                st.info(f"Copy this URL to the sidebar: {url}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🎬 Built with ❤️ using Streamlit, LangChain, and Google Gemini</p>
        <p>💡 <strong>Tip:</strong> For best results, use clear and specific questions when chatting with your videos!</p>
    </div>
    """, 
    unsafe_allow_html=True
)