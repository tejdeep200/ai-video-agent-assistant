import os
import shutil
import tempfile
from urllib.parse import urlparse

import yt_dlp
from pydub import AudioSegment


class AudioProcessingError(RuntimeError):
    """Base error for media acquisition failures."""


class FFmpegNotFoundError(AudioProcessingError):
    """Raised when FFmpeg/FFprobe is missing from PATH."""


class UnsupportedURLError(AudioProcessingError):
    """Raised when the URL is missing or unsupported for download."""


class DownloadBlockedError(AudioProcessingError):
    """Raised when a site blocks automated downloading (HTTP 403/Forbidden)."""


class NetworkDownloadError(AudioProcessingError):
    """Raised when the network fails while downloading media."""


DOWNLOAD_DIR = os.environ.get('VIDEO_DOWNLOAD_DIR', os.path.join(tempfile.gettempdir(), 'video_agent_downloads'))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _configure_ffmpeg() -> tuple[str | None, str | None]:
    """Resolve ffmpeg/ffprobe from PATH and configure pydub for Linux/Streamlit Cloud."""
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')

    if not ffmpeg_path or not ffprobe_path:
        raise FFmpegNotFoundError(
            "FFmpeg/FFprobe not found. Install the 'ffmpeg' package in Streamlit Cloud via `packages.txt` and ensure both binaries are on PATH."
        )

    os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffprobe = ffprobe_path

    return ffmpeg_path, ffprobe_path


def _make_ydl_options(ffmpeg_path: str, format_value: str) -> dict:
    return {
        'format': format_value,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'restrictfilenames': False,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 30,
        'retries': 2,
        'extractor_retries': 2,
        'geo_bypass': True,
        'ffmpeg_location': ffmpeg_path,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
        },
        'extractor_args': {
            'youtube': ['player_client=tv_embedded', 'player_client=android', 'player_client=web'],
        },
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }
        ],
    }


def download_youtube_audio(url: str) -> str:
    """Download a public YouTube audio/video stream and convert it to WAV with FFmpeg."""
    safe_url = (url or '').strip()
    parsed = urlparse(safe_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise UnsupportedURLError(
            f"Unsupported URL: '{safe_url}'. Please provide a valid public http(s) URL or a local file path."
        )

    ffmpeg_path, _ = _configure_ffmpeg()
    format_candidates = [
        'bestaudio[ext=mp4]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'bestaudio/best',
    ]
    last_error: Exception | None = None

    for format_value in format_candidates:
        try:
            with yt_dlp.YoutubeDL(_make_ydl_options(ffmpeg_path, format_value)) as ydl:
                info = ydl.extract_info(safe_url, download=True)
                if not info:
                    raise UnsupportedURLError(f"The URL could not be resolved to downloadable media: {safe_url}")
                filename = os.path.splitext(ydl.prepare_filename(info))[0] + '.wav'
                if os.path.exists(filename):
                    return filename
                raise FileNotFoundError(f'Expected extracted audio file was not created: {filename}')
        except yt_dlp.utils.UnsupportedError as exc:
            raise UnsupportedURLError(f"Unsupported URL or unsupported media source: {safe_url}") from exc
        except yt_dlp.utils.DownloadError as exc:
            last_error = exc
            message = str(exc).lower()
            if '403' in message or 'forbidden' in message or 'access denied' in message or 'blocked' in message:
                raise DownloadBlockedError(
                    'Download blocked (HTTP 403 / Forbidden). This public YouTube URL may be rejecting automated downloads, or the site is blocking the current request from this environment.'
                ) from exc
            if any(token in message for token in ['network', 'connection', 'timed out', 'unable to connect', 'ssl']):
                raise NetworkDownloadError(
                    'Network error while downloading the media. Please check the URL and network connectivity.'
                ) from exc
            continue
        except Exception as exc:
            last_error = exc
            if isinstance(exc, (FileNotFoundError, UnsupportedURLError, DownloadBlockedError, NetworkDownloadError)):
                raise
            continue

    if last_error is not None:
        raise NetworkDownloadError(f'Download failed: {last_error}')
    raise UnsupportedURLError(f"Could not download media from: {safe_url}")


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub and FFmpeg."""
    _configure_ffmpeg()
    if not os.path.exists(input_path):
        raise FileNotFoundError(f'Input file not found: {input_path}')

    output_path = os.path.splitext(input_path)[0] + '_converted.wav'
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format='wav')
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        chunk_path = f'{wav_path}_chunk_{i}.wav'
        chunk.export(chunk_path, format='wav')
        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list:
    clean_source = (source or '').strip()
    if not clean_source:
        raise ValueError('No source URL or file path provided.')

    if clean_source.startswith('http://') or clean_source.startswith('https://'):
        print('Detected remote URL. Downloading audio...')
        wav_path = download_youtube_audio(clean_source)
    else:
        print('Detected local file. Converting to WAV...')
        wav_path = convert_to_wav(clean_source)

    print('Chunking audio...')
    chunks = chunk_audio(wav_path)
    print(f'Audio ready — {len(chunks)} chunk(s) created.')
    return chunks


