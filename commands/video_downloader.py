import os
import subprocess
from telethon import TelegramClient, events
import yt_dlp as youtube_dl
from translations import translations
from urllib.parse import urlparse, parse_qs

def check_ffmpeg():
    """Check if ffmpeg is installed on the system"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def clean_url(url: str) -> str:
    """
    Clean YouTube URLs from unnecessary parameters (&t=, &list=, etc.)
    Returns a minimal valid URL (only watch?v=VIDEO_ID).
    """
    try:
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            qs = parse_qs(parsed.query)
            if "v" in qs:
                # Build clean URL with only the video ID
                return f"https://www.youtube.com/watch?v={qs['v'][0]}"
            # Handle short links like https://youtu.be/VIDEO_ID
            if parsed.netloc == "youtu.be":
                return f"https://www.youtube.com/watch?v={parsed.path.strip('/')}"
        return url.strip()
    except Exception:
        return url.strip()


async def download_video(event, url):
    try:
        # Validate URL
        if not url or not url.strip():
            await event.reply(translations['error_downloading_video'].format(error="Invalid URL provided"))
            return

        # Clean the URL before passing it to yt-dlp
        url = clean_url(url.strip())

        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.path.dirname(__file__), '..', 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)

        # Path to the cookies file
        cookies_path = os.path.join(os.path.dirname(__file__), '..', 'cookies', 'cookies.txt')

        # Check if cookies file exists and is not empty
        use_cookies = os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0

        # Check if ffmpeg is available
        ffmpeg_available = check_ffmpeg()

        ydl_opts = {
            'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
            'format': 'best[height<=1080]/best',  # Choose best format up to 1080p
            'noplaylist': True,
            'ignoreerrors': False,
            'no_warnings': False,
            'extractaudio': False,
            'audioformat': 'mp3',
            'prefer_ffmpeg': ffmpeg_available,
            'keepvideo': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'geo_bypass_country': 'IT',
            'geo_bypass_ip_block': '1.1.1.1',
            'postprocessors': [],
        }

        # Add post-processor for ffmpeg if available
        if ffmpeg_available:
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            })

        # Add cookies only if the file exists and is not empty
        if use_cookies:
            ydl_opts['cookiefile'] = cookies_path

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            # Extract video info first, without downloading
            try:
                print(f"DEBUG: Extracting info for URL: {url}")
                info_dict = ydl.extract_info(url, download=False)
                print(f"DEBUG: Info dict extracted: {info_dict is not None}")
            except Exception as e:
                print(f"DEBUG: Error extracting info: {str(e)}")
                await event.reply(translations['error_downloading_video'].format(error=f"Error extracting info: {str(e)}"))
                return

            if not info_dict:
                print("DEBUG: No info dict returned")
                await event.reply(translations['error_downloading_video'].format(error="Unable to extract video information"))
                return

            video_title = info_dict.get('title', 'video')
            print(f"DEBUG: Video title: {video_title}")

            # Start the actual download
            try:
                print("DEBUG: Starting download...")
                ydl.download([url])
                print("DEBUG: Download completed")
            except Exception as e:
                print(f"DEBUG: Error during download: {str(e)}")
                await event.reply(translations['error_downloading_video'].format(error=f"Error downloading: {str(e)}"))
                return

            # Try to locate the downloaded file
            file_path = None
            try:
                print("DEBUG: Preparing filename...")
                expected_filename = ydl.prepare_filename(info_dict)
                print(f"DEBUG: Expected filename: {expected_filename}")
                if expected_filename and os.path.exists(expected_filename):
                    file_path = expected_filename
                    print(f"DEBUG: File found at expected path: {file_path}")
                else:
                    print(f"DEBUG: File not found at expected path: {expected_filename}")
            except Exception as e:
                print(f"DEBUG: Error preparing filename: {str(e)}")
                import traceback
                traceback.print_exc()

            # If the expected filename was not found, search manually in downloads directory
            if not file_path:
                print("DEBUG: Searching for video files in downloads directory...")
                try:
                    for filename in os.listdir(downloads_dir):
                        print(f"DEBUG: Found file: {filename}")
                        if filename.endswith(('.mp4', '.webm', '.mkv', '.avi', '.mov')):
                            file_path = os.path.join(downloads_dir, filename)
                            print(f"DEBUG: Video file found: {file_path}")
                            break
                except Exception as e:
                    print(f"DEBUG: Error searching for video files: {str(e)}")
                    import traceback
                    traceback.print_exc()

        # Final check for file existence
        print(f"DEBUG: Final file_path: {file_path}")
        print(f"DEBUG: File exists: {file_path and os.path.exists(file_path) if file_path else False}")

        if file_path and os.path.exists(file_path):
            try:
                print("DEBUG: Sending file...")
                await event.reply(translations['video_downloaded_successfully'].format(video_title=video_title))
                await event.client.send_file(
                    event.chat_id,
                    file_path,
                    caption=f"{translations['video'].format(video_title=video_title)}",
                    supports_streaming=True
                )
                os.remove(file_path)
                print("DEBUG: File sent and removed successfully")
            except Exception as e:
                print(f"DEBUG: Error sending file: {str(e)}")
                await event.reply(translations['error_downloading_video'].format(error=f"Error sending file: {str(e)}"))
        else:
            print("DEBUG: File not found after download")
            await event.reply(translations['error_downloading_video'].format(error="File not found after download"))

    except youtube_dl.utils.DownloadError as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            await event.reply(translations['error_downloading_video'].format(error="Video unavailable or private"))
        elif "Sign in" in error_msg:
            await event.reply(translations['error_downloading_video'].format(error="Video requires login. Try adding valid cookies."))
        elif "This video is not available" in error_msg:
            await event.reply(translations['error_downloading_video'].format(error="Video not available in this region"))
        else:
            await event.reply(translations['error_downloading_video'].format(error=f"Download error: {error_msg}"))
        print(f"DownloadError: {error_msg}")

    except Exception as e:
        await event.reply(translations['error_downloading_video'].format(error=f"Generic error: {str(e)}"))
        print(f"Exception: {str(e)}")


def register(client):
    @client.on(events.NewMessage(pattern=r'^\.dlyt (.+)$', outgoing=True))
    async def handler(event):
        url = event.pattern_match.group(1)
        await download_video(event, url)
