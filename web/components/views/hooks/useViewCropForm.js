// useViewCropForm — form state, weather auto-fill, and API calls for ViewCrop
(function () {
  const { useState, useCallback, useEffect, useRef } = React;

  function useViewCropForm(profile, areaAcres, setAreaAcres) {
    const [N, setN]               = useState(90);
    const [P, setP]               = useState(42);
    const [K, setK]               = useState(43);
    const [ph, setPh]             = useState(6.5);
    const [temperature, setTemp]  = useState(25);
    const [humidity, setHum]      = useState(80);
    const [rainfall, setRain]     = useState(200);

    const [loading, setLoading]       = useState(false);
    const [error, setError]           = useState(null);
    const [result, setResult]         = useState(null);
    const [soilResult, setSoilResult] = useState(null);
    const [wxNote, setWxNote]         = useState('');
    const [wxLoading, setWxLoading]   = useState(false);
    const wxDebounceRef = useRef(null);
    const wxLastCityRef = useRef('');

    useEffect(() => () => clearTimeout(wxDebounceRef.current), []);

    useEffect(() => {
      const val = (profile.village || '').trim();
      if (wxDebounceRef.current) clearTimeout(wxDebounceRef.current);
      if (val.length < 3 || val.toLowerCase() === wxLastCityRef.current) return;
      wxDebounceRef.current = setTimeout(async () => {
        setWxLoading(true);
        try {
          const data = await window.api.fieldWatchScan(val);
          const w = data && data.weather;
          if (w) {
            if (w.temp != null)     setTemp(Math.min(45, Math.max(8, parseFloat(w.temp))));
            if (w.humidity != null) setHum(Math.min(100, Math.max(14, parseFloat(w.humidity))));
            const rf24 = (w.rain_1h != null ? parseFloat(w.rain_1h) : 0) * 24;
            if (rf24 > 0) setRain(Math.min(300, Math.max(20, rf24)));
            wxLastCityRef.current = val.toLowerCase();
            setWxNote(`Live weather · ${data.city || val}: ${w.temp?.toFixed(1)}°C, ${w.humidity}% humidity${w.description ? ' · ' + w.description : ''}`);
          } else {
            setWxNote(`No live weather for "${val}"`);
          }
        } catch (_) {
          setWxNote(`Couldn't fetch weather for "${val}"`);
        } finally {
          setWxLoading(false);
        }
      }, 500);
    }, [profile.village]);

    const handleSubmit = useCallback(() => {
      setLoading(true);
      setError(null);
      setSoilResult(null);

      const cropPromise = window.api.cropRecommend({ N, P, K, temperature, humidity, ph, rainfall });
      const soilPromise = window.api.soilAnalyze({
        N, P, K, ph,
        organic_matter_pct: 1.2,
        target_crop: profile.crop || undefined,
        area_acres: areaAcres,
      }).catch(() => null);

      Promise.all([cropPromise, soilPromise])
        .then(([cropData, soilData]) => {
          setResult(cropData);
          setSoilResult(soilData);
          setLoading(false);
        })
        .catch(e => {
          setError({
            status: e.status || null,
            detail: e.detail || e.message || String(e),
            message: e.message || String(e),
          });
          setLoading(false);
        });
    }, [N, P, K, temperature, humidity, ph, rainfall, areaAcres, profile.crop]);

    const handleReset = useCallback(() => {
      setN(90); setP(42); setK(43); setPh(6.5); setTemp(25); setHum(80); setRain(200);
      setAreaAcres(1.0);
      setResult(null); setError(null); setSoilResult(null);
    }, [setAreaAcres]);

    return {
      N, setN, P, setP, K, setK, ph, setPh,
      temperature, setTemp, humidity, setHum, rainfall, setRain,
      loading, error, result, soilResult,
      wxNote, wxLoading,
      handleSubmit, handleReset,
    };
  }

  window.useViewCropForm = useViewCropForm;
})();
