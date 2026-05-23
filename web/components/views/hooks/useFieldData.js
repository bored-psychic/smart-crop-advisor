// useFieldData — field-watch scan API call and WhatsApp message builder for ViewField
(function () {
  const { useState, useEffect, useCallback, useMemo } = React;

  function useFieldData(profile, fieldData, fieldLoading) {
    const [loading, setLoading] = useState(false);
    const [error, setError]     = useState(null);
    const [result, setResult]   = useState(fieldData || null);

    // Reflect prefetched data from App as it arrives
    useEffect(() => { if (fieldData) setResult(fieldData); }, [fieldData]);

    const doScan = useCallback(async (scanCity) => {
      const target = (scanCity || profile.village || '').trim();
      if (!target) return;
      setLoading(true);
      setError(null);
      try {
        const data = await window.api.fieldWatchScan(target);
        setResult(data);
      } catch (err) {
        let errObj = { status: err.status || 0, detail: '', message: err.message || 'Unknown error' };
        if (err.status === 401 || err.status === 403) {
          errObj.detail = 'Authentication error. Please refresh and try again.';
        } else if (!navigator.onLine) {
          errObj.detail = 'No internet connection. Check your network and retry.';
        } else {
          errObj.detail = err.detail || err.message || 'Could not reach server.';
        }
        setError(errObj);
      } finally {
        setLoading(false);
      }
    }, [profile.village]);

    // App-level prefetch covers village changes; doScan() remains for manual "Scan now"
    useEffect(() => { setLoading(!!fieldLoading); }, [fieldLoading]);

    const waMessage = useMemo(() => {
      if (!result) return '';
      return [
        '🌾 KisanOS Field Report',
        `Farmer: ${profile.name || 'Farmer'} | ${profile.village || result.city}`,
        `Crop: ${profile.crop || 'General'}`,
        `Location: ${result.city}`,
        `Risk: ${result.overall_risk}`,
        result.weather
          ? `Weather: ${result.weather.temp?.toFixed(1)}°C, ${result.weather.humidity}% humidity, ${result.weather.wind?.toFixed(0)} km/h wind`
          : '',
        result.weather?.description || '',
        result.flood  ? `Flood risk: ${result.flood.flood_risk}` : '',
        result.fire?.risk !== 'NONE' ? `Fire: ${result.fire.hotspots_nearby} hotspots (${result.fire.risk})` : '',
        'Sent via KisanOS',
      ].filter(Boolean).join('\n');
    }, [result, profile]);

    return { loading, error, result, doScan, waMessage };
  }

  window.useFieldData = useFieldData;
})();
