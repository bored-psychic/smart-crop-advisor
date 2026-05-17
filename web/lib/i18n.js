// Loads bundles.json and exposes a translator factory.
// Accepts both legacy flat ({key: "text"}) and structured ({key: {text,...}}) entries.
window.I18N = { bundles: null, _ready: null };
window.I18N._ready = fetch('/lib/bundles.json')
  .then(r => r.json())
  .then(b => { window.I18N.bundles = b; })
  .catch(e => { console.warn('i18n: failed to load bundles', e); });

function _entryText(entry, key) {
  if (entry == null) return null;
  if (typeof entry === 'string') return entry;
  if (typeof entry === 'object' && typeof entry.text === 'string') return entry.text;
  return null;
}

window.makeT = (lang) => (key) => {
  const b = window.I18N.bundles;
  if (!b) return key;
  const langEntry = b[lang] && b[lang][key];
  const enEntry = b['en'] && b['en'][key];
  return _entryText(langEntry, key) || _entryText(enEntry, key) || key;
};
