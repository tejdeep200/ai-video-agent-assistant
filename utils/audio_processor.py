import os
import shutil

import yt_dlp
from pydub import AudioSegment

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _configure_ffmpeg() -> tuple[str | None, str | None]:
    """Configure ffmpeg/ffprobe for local Windows or Streamlit Cloud Linux."""
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')

    # Local Windows fallback: use a user-installed FFmpeg bundle if present.
    win_ffmpeg_dir = os.path.expanduser(r'~\ffmpeg\ffmpeg-master-latest-win64-gpl\bin')
    if os.name == 'nt' and os.path.isdir(win_ffmpeg_dir):
        ffmpeg_path = os.path.join(win_ffmpeg_dir, 'ffmpeg.exe')
        ffprobe_path = os.path.join(win_ffmpeg_dir, 'ffprobe.exe')

    if ffmpeg_path:
        os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')
        AudioSegment.converter = ffmpeg_path
    if ffprobe_path:
        AudioSegment.ffprobe = ffprobe_path

    return ffmpeg_path, ffprobe_path


_configure_ffmpeg()


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
    ffmpeg_loc, _ = _configure_ffmpeg()
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'ffmpeg_location': ffmpeg_loc or 'ffmpeg',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }
        ],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).replace('.webm', '.wav').replace('.m4a', '.wav')
    return filename


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + '_converted.wav'
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # 16khz
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
    if source.startswith('http://') or source.startswith('https://'):
        print('Detected YouTube URL. Downloading audio...')
        wav_path = download_youtube_audio(source)
    else:
        print('Detected local file. Converting to WAV...')
        wav_path = convert_to_wav(source)

    print('Chunking audio...')
    chunks = chunk_audio(wav_path)
    print(f'Audio ready — {len(chunks)} chunk(s) created.')
    return chunks


