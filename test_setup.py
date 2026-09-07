#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print('='*60)
print('CHECKING PROJECT SETUP')
print('='*60)

# Check imports
try:
    from utils.audio_processor import process_input, download_youtube_audio
    print('✅ audio_processor.py')
except Exception as e:
    print(f'❌ audio_processor.py: {e}')
    sys.exit(1)

try:
    from core.transcriber import transcribe_all
    print('✅ transcriber.py')
except Exception as e:
    print(f'❌ transcriber.py: {e}')
    sys.exit(1)

try:
    from core.summarizer import summarize, generate_title
    print('✅ summarizer.py')
except Exception as e:
    print(f'❌ summarizer.py: {e}')
    sys.exit(1)

try:
    from core.extractor import extract_action_items, extract_key_decisions, extract_questions
    print('✅ extractor.py')
except Exception as e:
    print(f'❌ extractor.py: {e}')
    sys.exit(1)

try:
    from core.rag_engine import build_rag_chain, ask_question
    print('✅ rag_engine.py')
except Exception as e:
    print(f'❌ rag_engine.py: {e}')
    sys.exit(1)

try:
    from core.vector_store import build_vector_store
    print('✅ vector_store.py')
except Exception as e:
    print(f'❌ vector_store.py: {e}')
    sys.exit(1)

# Check environment
api_key = os.getenv('GROQ_API_KEY')
if api_key:
    print(f'✅ GROQ_API_KEY: {api_key[:10]}...')
else:
    print('❌ GROQ_API_KEY not found')
    sys.exit(1)

whisper = os.getenv('WHISPER_MODEL', 'base')
print(f'✅ WHISPER_MODEL: {whisper}')

print('='*60)
print('✅ ALL CHECKS PASSED - PROJECT READY')
print('='*60)
