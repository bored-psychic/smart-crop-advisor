import streamlit as st
import pandas as pd
import io
import wave
import numpy as np
from frontend.api_client import APIClient, run_async
from frontend.ui_helpers import card, page_hero
from core.language import T

PEST_META = {
    'Healthy Plant':         {'severity': 'low',    'freq_range': '<100 Hz (flat)',  'pattern': 'Flat noise floor',               'energy_level': 'Background',     'icon': '✅'},
    'Aphid Colony':          {'severity': 'medium', 'freq_range': '200–400 Hz',      'pattern': 'Clustered mid-freq bursts',       'energy_level': 'Moderate',       'icon': '🟡'},
    'Whitefly Infestation':  {'severity': 'medium', 'freq_range': '400–700 Hz',      'pattern': 'Wing-beat harmonic series',       'energy_level': 'Low-moderate',   'icon': '🟡'},
    'Locust Activity':       {'severity': 'high',   'freq_range': '50–200 Hz',       'pattern': 'High-amplitude low-freq pulses',  'energy_level': 'Very High',      'icon': '🔴'},
    'Stem Borer':            {'severity': 'high',   'freq_range': '50–150 Hz',       'pattern': 'Low-freq gnawing rhythm',         'energy_level': 'High',           'icon': '🔴'},
    'Early Fungal Infection':{'severity': 'high',   'freq_range': '800–1200 Hz',     'pattern': 'High-freq crackling',             'energy_level': 'Elevated',       'icon': '🔴'},
    'Spider Mite':           {'severity': 'medium', 'freq_range': '1200–4000 Hz',    'pattern': 'Ultra-high freq scratching',      'energy_level': 'Moderate-high',  'icon': '🟡'},
    'Thrips Infestation':    {'severity': 'medium', 'freq_range': '350–500 Hz',      'pattern': 'Rapid mid-freq staccato',         'energy_level': 'Low-moderate',   'icon': '🟡'},
}


_WARNING_LABEL = {
    'truncated_to_10s': '✂️ Recording was longer than 10s — only the first 10s were analyzed.',
    'too_short':         '⏱️ Recording too short for reliable analysis.',
    'below_noise_floor': '🔇 Recording is essentially silent.',
    'decode_failed':     '🛑 Could not decode this audio format on the server.',
    'empty_upload':      '🛑 Empty upload — no audio data received.',
    'feature_extract_failed': '⚠️ Feature extraction failed after decode.',
}


def _warning_text(code: str) -> str:
    if code in _WARNING_LABEL:
        return _WARNING_LABEL[code]
    if code.startswith('low_sample_rate_'):
        return f'⚠️ Low sample rate ({code.split("_")[-1]}) — accuracy reduced.'
    if code.startswith('high_sample_rate_'):
        return f'ℹ️ Unusually high sample rate ({code.split("_")[-1]}).'
    return f'ℹ️ {code}'


def _precheck_audio_upload(audio_bytes: bytes, filename: str, mime_type: str) -> tuple[bool, list[str], list[str]]:
    """
    Frontend quality gate to avoid sending accidental taps/silence to backend.
    Returns (is_valid, blocking_errors, non_blocking_warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not audio_bytes:
        return False, ["Empty file uploaded."], warnings

    if len(audio_bytes) < 6000:
        errors.append("File is too small and looks like an accidental tap. Please record 4-10 seconds.")

    lower_name = (filename or "").lower()
    is_wav = "wav" in (mime_type or "").lower() or lower_name.endswith(".wav")

    if not is_wav:
        if len(audio_bytes) < 12000:
            errors.append("Audio is likely too short. Record at least 1.5 seconds (recommended 4-10 seconds).")
        warnings.append("Detailed sample-rate/silence checks are available for WAV previews only.")
        return len(errors) == 0, errors, warnings

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            duration = (n_frames / sample_rate) if sample_rate else 0.0
            pcm_bytes = wf.readframes(n_frames)
    except Exception:
        errors.append("Could not parse WAV metadata. Re-record and upload again.")
        return False, errors, warnings

    if duration < 1.5:
        errors.append(f"Recording is only {duration:.1f}s. Minimum is 1.5s (recommended 4-10s).")
    if sample_rate < 8000:
        errors.append(f"Sample rate is {sample_rate} Hz. Please re-record at 8 kHz or higher.")

    dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sampwidth)
    if dtype is not None and len(pcm_bytes) > 0:
        raw = np.frombuffer(pcm_bytes, dtype=dtype)
        if n_channels > 1:
            raw = raw.reshape(-1, n_channels)[:, 0]

        if sampwidth == 1:
            signal = (raw.astype(np.float32) - 128.0) / 128.0
        elif sampwidth == 2:
            signal = raw.astype(np.float32) / 32768.0
        else:
            signal = raw.astype(np.float32) / 2147483648.0

        rms = float(np.sqrt(np.mean(signal ** 2))) if signal.size else 0.0
        if rms < 1e-4:
            errors.append("Recording is essentially silent. Move closer to the crop and re-record.")
    else:
        warnings.append("Could not run silence check for this WAV encoding.")

    return len(errors) == 0, errors, warnings


def render():
    page_hero("LISTEN TO FIELD", "Hear what's hidden", "under the leaves.", "Upload a field recording. The AI reads frequency patterns to find pests 7 days before they're visible.")

    st.warning(f"""
    **{T('How to record')}:**
    1. {T('Go to your field and open your phone voice recorder app')}
    2. {T('Hold the phone 15–30cm from the base of the crop plant or under the leaves')}
    3. {T('Record for 4–10 seconds. Keep still and breathe slowly.')}
    4. {T('Save and upload the file here')}
    """)

    acoustic_crop = st.selectbox(
        T("Which crop did you record?"),
        ['Tomato', 'Rice', 'Wheat', 'Cotton', 'Maize', 'Potato', 'Banana', 'Chickpea'],
        key="acoustic_crop"
    )

    audio_file = st.file_uploader(
        T("Upload field audio recording"),
        type=["wav", "mp3", "ogg", "webm", "m4a", "aac"],
        help=T("Any format from your phone voice recorder works.")
    )

    if audio_file is not None:
        st.audio(audio_file, format=audio_file.type)
        st.markdown(f"**{T('File')}:** {audio_file.name} · **{T('Size')}:** {audio_file.size // 1024} KB")
        audio_bytes = audio_file.getvalue()
        can_analyze, gate_errors, gate_warnings = _precheck_audio_upload(
            audio_bytes, audio_file.name, audio_file.type
        )

        for err in gate_errors:
            st.error(err)
        for warn in gate_warnings:
            st.warning(warn)

        if st.button(
            f"🔊 {T('Analyze for Pests')}",
            use_container_width=True,
            type="primary",
            disabled=not can_analyze,
        ):
            with st.spinner("▶ Decoding audio · analysing audio..."):
                result = run_async(APIClient.analyze_acoustic(audio_bytes, crop_type=acoustic_crop))
            if result:
                st.session_state['tab5_result'] = result
            else:
                card(T("Acoustic API unavailable. Check backend connection."), severity="error")

    if 'tab5_result' in st.session_state:
        r = st.session_state['tab5_result']
        st.divider()

        warnings = r.get('quality_warnings') or []
        for w in warnings:
            st.warning(_warning_text(w))

        method = r.get('analysis_method', '')
        if method == 'rejected':
            card(T(r.get('action', 'Analysis rejected.')), severity="error")
            return

        if method == 'uncertain':
            stage = r.get('claude_failure_stage') or 'unknown'
            detail = r.get('claude_failure_detail') or '—'
            model_tried = r.get('claude_model_used') or '—'
            card(T(r.get('action', 'AI could not produce a confident reading.')),
                 severity="info")
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;'
                f'color:#9AA0A6;margin-top:6px">'
                f'Stage: <b>{stage}</b> &middot; '
                f'Detail: {detail} &middot; '
                f'Model tried: {model_tried}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown("")
            st.caption(T("Tip: re-record closer to the crop, or open the Disease tab "
                         "to upload a leaf photo instead."))
            return

        if method == 'random_forest_offline_demo':
            cv_acc = r.get('cv_accuracy')
            cv_lbl = r.get('cv_label') or 'cross-validation'
            badge_text = "🟡 OFFLINE DEMO — synthetic-data model · NOT a real prediction"
            if isinstance(cv_acc, (int, float)) and cv_acc > 0:
                badge_text = (
                    f"🟡 OFFLINE DEMO — synthetic-data model · NOT a real prediction · "
                    f"{cv_acc * 100:.1f}% on {cv_lbl}"
                )
            st.markdown(
                f'<span style="background:#3B2F0F;color:#FBE7A1;padding:4px 12px;border-radius:20px;'
                f'font-size:12px;font-weight:600">{badge_text}</span>',
                unsafe_allow_html=True
            )
            st.caption(T("Set ANTHROPIC_API_KEY to enable real Claude bioacoustics. "
                         "This synthetic Random Forest is for offline UI demos only."))
            st.markdown("")
        elif method == 'gemini_audio':
            model_used = r.get('claude_model_used') or 'gemini+claude'
            st.markdown(
                f'<span style="background:#0F1F3A;color:#93C5FD;padding:4px 12px;border-radius:20px;'
                f'font-size:12px;font-weight:600">🎵 Gemini Audio → Claude · {model_used} · '
                f'native audio understanding</span>',
                unsafe_allow_html=True
            )
            st.markdown("")
        elif method == 'claude_vision':
            model_used = r.get('claude_model_used') or 'claude vision'
            st.markdown(
                f'<span style="background:#0F2A1F;color:#B7E4C7;padding:4px 12px;border-radius:20px;'
                f'font-size:12px;font-weight:600">👁️ Claude Vision · {model_used} · '
                f'spectrogram + DSP features</span>',
                unsafe_allow_html=True
            )
            st.markdown("")

        meta_cols = st.columns(3)
        with meta_cols[0]:
            st.caption(f"**Analyzed:** {r.get('analyzed_seconds', 0)}s of {r.get('duration_seconds', 0)}s")
        with meta_cols[1]:
            st.caption(f"**Sample rate:** {r.get('sample_rate', 0)} Hz")
        with meta_cols[2]:
            st.caption(f"**Decoder:** {r.get('decode_method', '–')}")

        pest_name = r.get('pest', 'Unknown')
        severity  = r.get('severity', 'low')
        icon      = r.get('icon', '⚠️')
        _smap_a   = {'high': 'error', 'medium': 'warning', 'low': 'success'}
        _conf_a   = r.get('confidence', 0)
        card(f"""
        <div style='font-family:Space Grotesk,sans-serif;'>
          <div style='font-size:1.3rem;font-weight:700;color:#E2F5DF;margin-bottom:3px;'>
            {icon}&nbsp;{T(pest_name)}
          </div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#4ADE80;margin-bottom:10px;'>
            {T('severity')} &middot; {severity.upper()}{f" &nbsp;&#183;&nbsp; {T('confidence')} {_conf_a}%" if _conf_a > 0 else ""}
          </div>
          <div style='font-size:0.88rem;color:#E2F5DF;'>
            <b style='color:#22C55E;'>&#128138; {T('Action')}:</b> {T(r.get('action', ''))}
          </div>
        </div>
        """, severity=_smap_a.get(severity, 'warning'))

        if _conf_a > 0:
            st.progress(_conf_a / 100)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(T("Dominant Frequency"), r.get('freq_range', 'N/A'))
            st.metric(T("Signal Energy"), r.get('energy_level', 'N/A'))
        with col2:
            st.metric(T("Spectral Pattern"), r.get('pattern', 'N/A'))
            st.metric(T("Risk Level"), severity.upper())

        if r.get('top3'):
            st.markdown(f"#### 📊 {T('Top Predictions')}")
            for p_name, pct in r['top3']:
                meta = PEST_META.get(p_name, {'icon': '🐛', 'severity': 'medium'})
                sev_color = {'high': '#FF4B4B', 'medium': '#FFA500', 'low': '#21BA45'}.get(meta.get('severity', 'low'), '#888')
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
                    f'<div style="width:130px;font-size:13px">{meta.get("icon","🐛")}&nbsp;{p_name}</div>'
                    f'<div style="flex:1;height:10px;background:#eee;border-radius:5px;overflow:hidden">'
                    f'<div style="width:{pct}%;height:100%;background:{sev_color};border-radius:5px"></div></div>'
                    f'<div style="width:38px;font-size:13px;font-weight:600;text-align:right">{pct}%</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        if r.get('claude_advice'):
            card(f"<b style='color:#22C55E;'>&#129302; {T('AI Farm Advisor')}:</b> {r['claude_advice']}", severity="info")

        if r.get('band_energy'):
            st.markdown(f"#### 📊 {T('Frequency Band Energy')}")
            chart_df = pd.DataFrame.from_dict(r['band_energy'], orient='index', columns=[T('Energy')])
            st.bar_chart(chart_df)

        if r.get('methodology_note'):
            st.caption(f"ℹ️ {r['methodology_note']}")

    st.divider()
    with st.expander(f"🔬 {T('Reference Signatures (8 well-known) — Claude can also detect others')}"):
        st.caption(T("These eight signatures are the ones the tool was originally tuned for. "
                     "Claude can return any pest, disease, or non-pest sound it identifies — "
                     "the table below is just the canonical reference set."))
        data = {
            T('Pest / Condition'): list(PEST_META.keys()),
            T('Frequency Range'):  [m['freq_range'] for m in PEST_META.values()],
            T('Pattern'):          [m['pattern']    for m in PEST_META.values()],
            T('Risk'):             [m['severity'].upper() for m in PEST_META.values()],
        }
        st.table(pd.DataFrame(data))
