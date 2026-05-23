// usePhotoPanelForm — crop list fetch, file selection, disease analysis, and price estimation for ViewDisease
(function () {
  const { useState, useEffect, useRef, useCallback } = React;

  const FALLBACK_CROPS = ['Tomato', 'Potato', 'Rice', 'Cotton', 'Wheat', 'Maize', 'Banana', 'Sugarcane'];

  function usePhotoPanelForm(areaAcres) {
    const [cropList, setCropList]       = useState(null);
    const [cropsLoading, setCropsLoading] = useState(true);
    const [cropType, setCropType]       = useState('Tomato');
    const [drag, setDrag]               = useState(false);
    const [loading, setLoading]         = useState(false);
    const [result, setResult]           = useState(null);
    const [error, setError]             = useState(null);
    const [price, setPrice]             = useState(null);
    const [priceLoading, setPriceLoading] = useState(false);
    const [file, setFile]               = useState(null);
    const fileRef = useRef();

    useEffect(() => {
      window.api.diseaseCrops()
        .then(data => {
          const names = Object.keys(data);
          setCropList(names.length > 0 ? names : FALLBACK_CROPS);
          setCropType(prev => names.includes(prev) ? prev : names[0] || FALLBACK_CROPS[0]);
        })
        .catch(() => {
          setCropList(FALLBACK_CROPS);
        })
        .finally(() => setCropsLoading(false));
    }, []);

    const analyzeFile = useCallback((f) => {
      if (!f) return;
      setLoading(true);
      setResult(null);
      setError(null);
      setPrice(null);
      setPriceLoading(false);
      window.api.diseasePhoto(f, cropType)
        .then(r => {
          setResult(r);
          setLoading(false);
          if (r.treatment) {
            setPriceLoading(true);
            window.api.diseaseTreatmentPrice({
              disease: r.disease,
              treatment: r.treatment,
              crop_type: cropType,
              area_acres: areaAcres,
            }).then(p => setPrice(p)).catch(() => {}).finally(() => setPriceLoading(false));
          }
        })
        .catch(e => {
          setError({
            status: e.status || null,
            detail: e.detail || e.message || String(e),
            message: e.message || String(e),
          });
          setLoading(false);
        });
    }, [cropType, areaAcres]);

    const handleFileChange = useCallback((e) => {
      const chosen = e.target.files?.[0];
      if (chosen) {
        setFile(chosen);
        analyzeFile(chosen);
      }
      e.target.value = '';
    }, [analyzeFile]);

    const onDrop = useCallback((e) => {
      e.preventDefault();
      setDrag(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) {
        setFile(dropped);
        analyzeFile(dropped);
      }
    }, [analyzeFile]);

    return {
      cropList, cropsLoading, cropType, setCropType,
      drag, setDrag,
      loading, result, error,
      price, priceLoading,
      file, fileRef,
      analyzeFile, handleFileChange, onDrop,
    };
  }

  window.usePhotoPanelForm = usePhotoPanelForm;
  window._FALLBACK_CROPS   = FALLBACK_CROPS;
})();
