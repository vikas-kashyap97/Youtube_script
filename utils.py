import streamlit as st
import re
from typing import List, Dict, Any
import json
import os
from datetime import datetime

def validate_youtube_url(url: str) -> bool:
    """
    Validate if the provided URL is a valid YouTube URL.
    """
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+/search\?query=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/c/[\w-]+/search\?query=[\w-]+',
    ]
    
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human readable format.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length with ellipsis.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def save_processing_results(results: List[Dict[str, Any]], filename: str = None) -> str:
    """
    Save processing results to a JSON file.
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processing_results_{timestamp}.json"
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "total_videos": len(results),
        "successful_videos": len([r for r in results if r["status"] == "success"]),
        "failed_videos": len([r for r in results if r["status"] == "failed"]),
        "results": results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    return filename

def load_processing_results(filename: str) -> Dict[str, Any]:
    """
    Load processing results from a JSON file.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"File {filename} not found.")
        return {}
    except json.JSONDecodeError:
        st.error(f"Invalid JSON format in {filename}.")
        return {}

def display_processing_summary(results: List[Dict[str, Any]]):
    """
    Display a summary of processing results in Streamlit.
    """
    if not results:
        st.warning("No processing results to display.")
        return
    
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Videos", len(results))
    
    with col2:
        st.metric("Successful", len(successful), delta=len(successful))
    
    with col3:
        st.metric("Failed", len(failed), delta=-len(failed) if failed else 0)
    
    # Show details in expandable sections
    if successful:
        with st.expander(f"✅ Successful Videos ({len(successful)})"):
            for result in successful:
                st.success(f"**{truncate_text(result['title'], 80)}**")
                st.caption(f"Chunks: {result.get('chunks_count', 'N/A')} | URL: {result['url']}")
    
    if failed:
        with st.expander(f"❌ Failed Videos ({len(failed)})"):
            for result in failed:
                st.error(f"**{truncate_text(result['title'], 80)}**")
                st.caption(f"Error: {result.get('error', 'Unknown error')} | URL: {result['url']}")

def create_download_link(data: str, filename: str, link_text: str) -> str:
    """
    Create a download link for text data.
    """
    import base64
    
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def estimate_processing_time(num_videos: int) -> str:
    """
    Estimate processing time based on number of videos.
    """
    # Rough estimate: 3-5 seconds per video for transcript + embedding
    estimated_seconds = num_videos * 4
    return format_duration(estimated_seconds)

def check_api_key_validity(api_key: str) -> bool:
    """
    Basic validation for Google API key format.
    """
    if not api_key:
        return False
    
    # Google API keys typically start with 'AIza' and are 39 characters long
    if api_key.startswith('AIza') and len(api_key) == 39:
        return True
    
    return False

def get_video_stats(processing_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from processing results.
    """
    if not processing_results:
        return {}
    
    successful = [r for r in processing_results if r["status"] == "success"]
    failed = [r for r in processing_results if r["status"] == "failed"]
    
    total_chunks = sum(r.get("chunks_count", 0) for r in successful)
    
    stats = {
        "total_videos": len(processing_results),
        "successful_videos": len(successful),
        "failed_videos": len(failed),
        "success_rate": len(successful) / len(processing_results) * 100 if processing_results else 0,
        "total_chunks": total_chunks,
        "average_chunks_per_video": total_chunks / len(successful) if successful else 0,
    }
    
    return stats

def clean_filename(filename: str) -> str:
    """
    Clean filename by removing invalid characters.
    """
    # Remove invalid characters for filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:97] + "..."
    
    return filename

@st.cache_data
def get_example_urls() -> List[Dict[str, str]]:
    """
    Return a list of example URLs for testing.
    """
    return [
        {
            "type": "Single Video",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "description": "Rick Astley - Never Gonna Give You Up"
        },
        {
            "type": "Playlist",
            "url": "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy5Y9BYdAPuRJ8LEO-8Q4n5",
            "description": "Python Tutorial Playlist"
        },
        {
            "type": "Channel Search",
            "url": "https://www.youtube.com/@3blue1brown/search?query=calculus",
            "description": "3Blue1Brown calculus videos"
        }
    ]

def display_example_urls():
    """
    Display example URLs in an organized format.
    """
    st.subheader("🔗 Example URLs")
    
    examples = get_example_urls()
    
    for example in examples:
        with st.expander(f"{example['type']}: {example['description']}"):
            st.code(example['url'])
            st.caption(f"Type: {example['type']}")

if __name__ == "__main__":
    # Test functions
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"URL valid: {validate_youtube_url(test_url)}")
    print(f"Duration format: {format_duration(3661)}")
    print(f"Text truncated: {truncate_text('This is a very long text that should be truncated', 20)}")