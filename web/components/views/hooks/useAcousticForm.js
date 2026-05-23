// useAcousticForm — form state, file pre-check, and API call for ViewAcoustic
(function () {
  const { useState, useEffect, useRef, useMemo } = React;

  const BAR_COUNT = window.innerWidth <= 640 ? 28 : 40;

  function useAcousticForm(t) {
    const [file, setFile]                         = useState(null);
    const [preCheckWarnings, setPreCheckWarnings] = useState([]);
    const [preCheckError, setPreCheckError]       = useState(null);
    const [loading, setLoading]                   = useState(false);
    const [error, setError]                       = useState(null);
    const [result, setResult]                     = useState(null);
    const [cropType, setCropType]                 = useState('Unknown');
    const [drag, setDrag]                         = useState(false);
    const [bars, setBars]                         = useState(Array(BAR_COUNT).fill(0.1));
    const inputRef = useRef();

    // Animate bars while loading
    useEffect(() => {
      if (loading) {
        const id = setInterval(() => setBars(Array.from({ length: BAR_COUNT }, () => 0.2 + Math.random() * 0.7)), 100);
        return () => clearInterval(id);
      } else {
        setBars(Array(BAR_COUNT).fill(0.1));
      }
    }, [loading]);

    // Object URL — create once per file, revoke on change/unmount
    const audioUrl = useMemo(() => {
      if (!file) return null;
      return URL.createObjectURL(file);
    }, [file]);
    useEffect(() => {
      return () => { if (audioUrl) URL.revokeObjectURL(audioUrl); };
    }, [audioUrl]);

    // Pre-check: size + AudioContext decode
    async function runPreCheck(f) {
      setPreCheckWarnings([]);
      setPreCheckError(null);
      setResult(null);
      setError(null);

      // 1. Size gate (hard block)
      if (f.size > 20 * 1024 * 1024) {
        setPreCheckError(t('File too large (max 20 MB)'));
        return;
      }

      // 2. AudioContext decode (advisory warnings only)
      try {
        const arrayBuf = await f.arrayBuffer();
        const Ctx = window.AudioContext || window.webkitAudioContext;
        const ctx = new Ctx();
        const buf = await ctx.decodeAudioData(arrayBuf);
        ctx.close();

        const duration   = buf.duration;
        const sampleRate = buf.sampleRate;
        const samples    = buf.getChannelData(0);
        const rms        = Math.sqrt(samples.reduce((s, v) => s + v * v, 0) / samples.length);

        const warns = [];
        if (duration < 3)      warns.push('too_short');
        if (rms < 0.002)       warns.push('below_noise_floor');
        if (sampleRate < 8000) warns.push('low_sample_rate');
        setPreCheckWarnings(warns);
      } catch (_) {
        // Unsupported format — advisory only, allow submit
        setPreCheckError(t("Cannot preview this audio format — upload anyway to let the server analyze it."));
      }
    }

    function handleFile(f) {
      if (!f) return;
      setFile(f);
      runPreCheck(f);
    }

    function onDrop(e) {
      e.preventDefault();
      setDrag(false);
      handleFile(e.dataTransfer.files[0]);
    }

    function clearAll() {
      setFile(null);
      setPreCheckWarnings([]);
      setPreCheckError(null);
      setResult(null);
      setError(null);
      setLoading(false);
    }

    function normalizeError(err) {
      if (!err) return { status: null, detail: t('Unknown error'), message: t('Unknown error') };
      const status = err.status || null;
      const detail = err.detail || err.message || String(err);
      let message;
      if (status === 401 || status === 403) message = t('Invalid or missing API key.');
      else if (!status)                     message = t('Network error — check your connection.');
      else                                  message = detail;
      return { status, detail, message };
    }

    async function analyze() {
      if (!file) return;
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const res = await window.api.acousticAnalyze(file, cropType || 'Unknown');
        setResult(res);
      } catch (err) {
        setError(normalizeError(err));
      } finally {
        setLoading(false);
      }
    }

    const isSizeBlock     = file && file.size > 20 * 1024 * 1024;
    const analyzeDisabled = loading || isSizeBlock || !file;

    return {
      file, cropType, setCropType,
      drag, setDrag,
      bars, BAR_COUNT,
      audioUrl, inputRef,
      preCheckWarnings, preCheckError,
      loading, error, result,
      analyzeDisabled,
      handleFile, onDrop, clearAll, analyze,
    };
  }

  window.useAcousticForm = useAcousticForm;
})();
