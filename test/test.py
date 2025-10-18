import streamlit as st
import edge_tts
import asyncio
from io import BytesIO

from langdetect import detect, LangDetectException

voices = asyncio.run(edge_tts.list_voices())
print(voices)