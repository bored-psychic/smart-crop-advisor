import base64
from io import BytesIO
import streamlit as st

def speak(text, lang_code='en'):
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_b64 = base64.b64encode(audio_buffer.read()).decode()
        st.markdown(
            f'<audio autoplay><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>',
            unsafe_allow_html=True
        )
        st.audio(audio_buffer.getvalue(), format='audio/mp3')
    except Exception as e:
        st.warning(f"Audio unavailable: {e}")


