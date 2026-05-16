window.I18N = { bundles: null, _ready: null };
window.I18N._ready = fetch('/lib/bundles.json')
  .then(r => r.json())
  .then(b => { window.I18N.bundles = b; })
  .catch(e => { console.warn('i18n: failed to load bundles', e); });

window.makeT = (lang) => (key) => {
  const b = window.I18N.bundles;
  if (!b) return key;
  return (b[lang] && b[lang][key]) || (b['en'] && b['en'][key]) || key;
};
