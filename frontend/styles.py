"""
CSS styles and botanical overlay HTML for KisanOS.
Import STYLES and BOTANICAL_OVERLAY and inject via st.markdown / components.html.
"""

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,ital,wght@9..144,0,300;9..144,0,400;9..144,0,500;9..144,1,300;9..144,1,400&family=Inter:wght@300;400;500;600&family=Kalam:wght@300;400;700&display=swap');

/* === BASE === */
html, body, [class*="css"] {
  font-family: 'Inter', system-ui, sans-serif !important;
  background-color: #F4EFE3 !important;
  color: #2A3328 !important;
}
.stApp { background-color: #F4EFE3 !important; }

/* Warm radial background glow */
section[data-testid="stMain"] > div::before {
  content: '';
  position: fixed; inset: 0;
  background-image:
    radial-gradient(1200px 600px at 90% -10%, rgba(217,182,107,0.18), transparent 60%),
    radial-gradient(900px 500px at -10% 110%, rgba(107,155,107,0.14), transparent 60%);
  pointer-events: none; z-index: 0;
}

/* Paper texture */
section[data-testid="stMain"]::before {
  content: '';
  position: fixed; inset: 0;
  pointer-events: none; z-index: 0; opacity: 0.45;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.16 0 0 0 0 0.20 0 0 0 0 0.15 0 0 0 0.06 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
}

/* === TABS === */
.stTabs [data-baseweb="tab-list"] {
  gap: 2px;
  background: #FBF7EC !important;
  border-radius: 999px;
  padding: 5px;
  border: 1px solid rgba(42,51,40,0.14) !important;
  box-shadow: 0 2px 12px -6px rgba(42,51,40,0.18);
  overflow: hidden;
  position: relative;
}
.stTabs [data-baseweb="tab-list"]::before {
  content: '';
  position: absolute; inset: 0; pointer-events: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 60'><path d='M-10 30 q 60 -22 120 0 q 60 22 120 0 q 60 -22 120 0 q 60 22 120 0 q 60 -22 120 0' fill='none' stroke='%233E6B3E' stroke-width='0.8' opacity='0.18'/></svg>");
  background-repeat: no-repeat; background-size: 100% 100%; background-position: center;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 999px !important;
  color: #3A4A35 !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  padding: 9px 18px !important;
  border: 1px solid transparent !important;
  transition: all 0.2s ease;
  letter-spacing: 0.01em !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #2A3328 !important; }
.stTabs [aria-selected="true"] {
  background: white !important;
  color: #2A3328 !important;
  border-color: rgba(42,51,40,0.10) !important;
  box-shadow: 0 1px 4px rgba(42,51,40,0.10) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* === BUTTONS === */
.stButton > button {
  background: #3E6B3E !important;
  border: none !important;
  color: #fff !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  border-radius: 999px !important;
  padding: 10px 24px !important;
  box-shadow: 0 4px 14px -4px rgba(62,107,62,0.5) !important;
  transition: all 0.2s ease !important;
}
.stButton > button:hover {
  background: #345A35 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 18px -4px rgba(62,107,62,0.4) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* === SLIDERS === */
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {
  background: #3E6B3E !important;
}
[data-testid="stSlider"] [data-testid="stSliderThumb"] {
  background: #FBF7EC !important;
  border: 2px solid #3E6B3E !important;
  box-shadow: 0 2px 6px rgba(62,107,62,0.3) !important;
}

/* === SIDEBAR === */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #FBF7EC 0%, #F7F1E1 100%) !important;
  border-right: 1px solid rgba(42,51,40,0.10) !important;
  background-image: repeating-linear-gradient(0deg, transparent 0, transparent 22px, rgba(62,107,62,0.04) 22px, rgba(62,107,62,0.04) 23px) !important;
}
[data-testid="stSidebar"] * { color: #2A3328 !important; }
[data-testid="stSidebar"] .stTextInput input {
  font-family: 'Kalam', cursive !important;
  font-size: 15px !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 1px dashed rgba(42,51,40,0.20) !important;
  border-radius: 0 !important;
  padding: 2px 4px !important;
  color: #2A3328 !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .stTextInput input:focus {
  border-bottom-color: #3E6B3E !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] label {
  font-family: 'Inter', sans-serif !important;
  font-size: 11px !important;
  color: #4A5545 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
}
[data-testid="stSidebarCollapseButton"] {
  visibility: visible !important; display: block !important;
  position: fixed !important; top: 10px !important; left: 10px !important;
  z-index: 1000000 !important;
  background: rgba(62,107,62,0.08) !important; border-radius: 5px !important;
}
[data-testid="stSidebarCollapseButton"] svg {
  fill: #3E6B3E !important; width: 28px !important; height: 28px !important;
}

/* === INPUTS & SELECTS === */
.stTextInput input,
.stNumberInput input,
div[data-baseweb="select"] > div {
  background: rgba(255,255,255,0.7) !important;
  border: 1px solid rgba(42,51,40,0.18) !important;
  color: #2A3328 !important;
  border-radius: 12px !important;
  font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus { border-color: #3E6B3E !important; box-shadow: 0 0 0 3px rgba(62,107,62,0.12) !important; }

/* === FILE UPLOADER === */
[data-testid="stFileUploader"] {
  background: rgba(255,255,255,0.4) !important;
  border: 2px dashed rgba(42,51,40,0.22) !important;
  border-radius: 18px !important;
  transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover { border-color: #3E6B3E !important; }

/* === METRICS === */
[data-testid="stMetric"] {
  background: #FBF7EC !important;
  border: 1px solid rgba(42,51,40,0.10) !important;
  border-radius: 14px !important;
  padding: 14px 16px !important;
  box-shadow: 0 4px 12px -8px rgba(42,51,40,0.15) !important;
}
[data-testid="stMetricLabel"] p {
  color: #4A5545 !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.7rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
}
[data-testid="stMetricValue"] { color: #2A3328 !important; font-weight: 600 !important; }

/* === PROGRESS BAR === */
.stProgress > div > div > div { background: #3E6B3E !important; border-radius: 99px !important; }

/* === EXPANDERS === */
[data-testid="stExpander"] {
  background: #FBF7EC !important;
  border: 1px solid rgba(42,51,40,0.10) !important;
  border-radius: 14px !important;
}
[data-testid="stExpander"] summary svg { fill: #3E6B3E !important; }

/* === DIVIDER === */
[data-testid="stDivider"] hr { border-color: rgba(42,51,40,0.10) !important; }

/* === AUDIO PLAYER === */
audio { border-radius: 8px; }

/* === SCROLLBAR === */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #F4EFE3; }
::-webkit-scrollbar-thumb { background: #C7D6BD; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #6B9B6B; }

/* === HEADINGS === */
h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; font-weight: 500 !important; letter-spacing: -0.02em !important; color: #2A3328 !important; }

/* === HEADER === */
header[data-testid="stHeader"] { background-color: transparent !important; z-index: 999999 !important; }

/* === SPINNER (vine sweep) === */
@keyframes vine-sweep {
  0%   { width: 0%; opacity: 0; }
  10%  { opacity: 1; }
  65%  { width: 100%; opacity: 1; }
  85%  { width: 100%; opacity: 0.3; }
  100% { width: 0%; opacity: 0; }
}
div[data-testid="stSpinner"] { padding: 16px 0 22px; }
div[data-testid="stSpinner"] svg { display: none !important; }
div[data-testid="stSpinner"] p {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.82rem !important;
  color: #3A4A35 !important;
  letter-spacing: 0.03em !important;
  margin-bottom: 8px !important;
}
div[data-testid="stSpinner"] > div::after {
  content: '';
  display: block; height: 2px; width: 0;
  background: linear-gradient(90deg, #3E6B3E 0%, #6B9B6B 55%, #C7D6BD 100%);
  border-radius: 2px;
  animation: vine-sweep 2.4s cubic-bezier(.4,0,.2,1) infinite;
  margin-top: 2px;
}

/* === CENTERED TABS === */
.stTabs [data-baseweb="tab-list"] {
  width: fit-content !important;
  max-width: 100% !important;
  margin: 0 auto !important;
  flex-shrink: 0 !important;
}

/* === TAB CONTENT BLOOM === */
@keyframes tab-bloom {
  from { opacity: 0; transform: translateY(10px) scale(0.94); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
[data-baseweb="tab-panel"] > div { animation: tab-bloom 0.28s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
</style>
"""

BOTANICAL_OVERLAY = """
<script>
(function() {
  var pdoc;
  try { pdoc = window.parent.document; } catch(e) { return; }

  // Clean up previous run
  ['kisan-overlay','kisan-overlay-css'].forEach(function(id){
    var el = pdoc.getElementById(id); if(el) el.remove();
  });

  /* ── CSS ── */
  var css = pdoc.createElement('style');
  css.id = 'kisan-overlay-css';
  css.textContent = [
    /* Vine layer */
    '#kisan-bg-vines{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}',
    '#kisan-bg-vines svg{position:absolute;width:100%;height:100%}',
    /* Footer creeper */
    '#kisan-footer-creeper{position:fixed;bottom:-30px;right:-30px;width:380px;height:300px;pointer-events:none;z-index:0;opacity:0.20}',
    '#kisan-footer-creeper svg{width:100%;height:100%}',
    /* Vine animations */
    '.kv-climb{fill:none;stroke:#3E6B3E;stroke-width:1.4;stroke-linecap:round;stroke-dasharray:2400;stroke-dashoffset:2400;animation:kvDraw 4s cubic-bezier(0.5,0,0.3,1) forwards}',
    '.kv-climb.d{animation-delay:0.4s;opacity:0.55;stroke:#6B9B6B}',
    '.kv-thin{fill:none;stroke:#3E6B3E;stroke-width:0.8;opacity:0.35;stroke-linecap:round;stroke-dasharray:2200;stroke-dashoffset:2200;animation:kvDraw 5s ease 0.8s forwards}',
    '@keyframes kvDraw{to{stroke-dashoffset:0}}',
    '.kv-lf{opacity:0;transform-origin:center;animation:kvPop 0.55s cubic-bezier(0.34,1.56,0.64,1) forwards}',
    '@keyframes kvPop{to{opacity:0.82}}',
    '.kv-sw{transform-box:fill-box;transform-origin:50% 50%;animation:kvSway 5s ease-in-out infinite}',
    '@keyframes kvSway{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(3deg)}}',
    /* Caterpillar host */
    '#kisan-cat-host{position:fixed;bottom:22px;left:0;width:100%;height:80px;pointer-events:none;z-index:50}',
    '.kcat{position:absolute;bottom:0;left:0;will-change:transform;transform-origin:center bottom}',
    '.kcat .cat-svg{animation:kBreathe 3s ease-in-out infinite}',
    '@keyframes kBreathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(0.97)}}',
    '.kcat .seg{animation:kBob 0.9s ease-in-out infinite}',
    '.kcat .s2{animation-delay:.05s}.kcat .s3{animation-delay:.10s}.kcat .s4{animation-delay:.15s}.kcat .s5{animation-delay:.20s}.kcat .s6{animation-delay:.25s}',
    '@keyframes kBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}',
    '.kcat.excited .seg{animation-duration:0.45s!important}',
    '.kcat.thinking .seg{animation-duration:1.6s!important}',
    /* Tools */
    '.kcat .tool{opacity:0;transition:opacity .25s ease}',
    '.kcat.tool-wrench .wrench{opacity:1}',
    '.kcat.tool-lens .lens{opacity:1}',
    '.kcat.tool-lens .head{animation:kLensLean 1s ease forwards}',
    '@keyframes kLensLean{to{transform:translate(-2px,-3px) rotate(-8deg)}}',
    '.kcat .wrench{transform-origin:96px 24px;animation:kWrenchTwist 0.4s ease-in-out infinite}',
    '.kcat:not(.tool-wrench) .wrench{animation:none}',
    '@keyframes kWrenchTwist{0%{transform:rotate(-20deg)}50%{transform:rotate(20deg)}100%{transform:rotate(-20deg)}}',
    '.kcat .glint{animation:kLensGlint 1.5s ease-in-out infinite}',
    '@keyframes kLensGlint{0%,80%{opacity:0;transform:translateX(-4px)}40%{opacity:0.9;transform:translateX(2px)}100%{opacity:0}}',
    '.kcat.tool-wrench .seg{animation:kWiggle 0.4s ease-in-out infinite!important}',
    '@keyframes kWiggle{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-2px) rotate(2deg)}}',
    '.kcat .lid{transform-origin:center;transform-box:fill-box}',
    '.kcat.blink .lid{animation:kBlink 0.3s ease}',
    '@keyframes kBlink{0%,100%{transform:scaleY(0)}50%{transform:scaleY(1)}}',
    '.kcat.bounce{animation:kBounce 0.5s cubic-bezier(0.34,1.56,0.64,1)}',
    '@keyframes kBounce{0%{transform:translateY(0)}30%{transform:translateY(-10px)}100%{transform:translateY(0)}}',
    '.kcat.antwig .antennae{animation:kAntWig 0.5s ease 2}',
    '@keyframes kAntWig{0%,100%{transform:rotate(0)}25%{transform:rotate(8deg)}75%{transform:rotate(-8deg)}}',
    '.kcat .antennae{transform-origin:103px 22px;transform-box:fill-box}',
  ].join('');
  pdoc.head.appendChild(css);

  /* ── HTML ── */
  var ov = pdoc.createElement('div');
  ov.id = 'kisan-overlay';

  /* Full-viewport vine SVG */
  ov.innerHTML +=
    '<div id="kisan-bg-vines">' +
    '<svg viewBox="0 0 1440 900" preserveAspectRatio="none">' +
    '<defs>' +
      '<linearGradient id="kvLg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#3E6B3E"/><stop offset="100%" stop-color="#82B082"/></linearGradient>' +
      '<linearGradient id="kvLs" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#6B9B6B"/><stop offset="100%" stop-color="#C7D6BD"/></linearGradient>' +
    '</defs>' +
    /* Main vine paths */
    '<path class="kv-climb" d="M-20 880 C 60 760, 90 600, 70 460 S 30 240, 80 100 C 110 30, 200 0, 320 20 C 520 50, 760 60, 1000 40 C 1200 25, 1340 30, 1460 50"/>' +
    '<path class="kv-climb d" d="M-10 760 C 80 660, 50 480, 100 320 S 180 120, 320 80 C 540 50, 800 90, 1080 80 C 1260 75, 1380 80, 1460 100"/>' +
    /* Tendrils */
    '<path class="kv-thin" d="M70 440 q 30 -10 50 10"/>' +
    '<path class="kv-thin" d="M85 280 q 30 -20 60 -10"/>' +
    '<path class="kv-thin" d="M120 140 q -10 -20 10 -40"/>' +
    '<path class="kv-thin" d="M260 60 q 0 -20 30 -30"/>' +
    '<path class="kv-thin" d="M520 50 q 10 -20 30 -10"/>' +
    '<path class="kv-thin" d="M820 60 q 20 -20 50 -10"/>' +
    '<path class="kv-thin" d="M1180 50 q 20 -20 40 -10"/>' +
    '<path class="kv-thin" d="M1420 100 q -20 100 0 220 q 20 120 -10 240 q -20 100 10 220"/>' +
    /* Leaves — left vertical */
    '<g stroke="#3E6B3E" stroke-width="0.6">' +
    '<g class="kv-lf kv-sw" style="animation-delay:1.6s,0s" transform="translate(80 720) rotate(-30)"><path d="M0 0 C 14 -14, 30 -10, 30 6 C 30 22, 12 28, 0 16 Z" fill="url(#kvLg)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:1.7s,0.3s" transform="translate(60 600) rotate(160)"><path d="M0 0 C 14 -14, 30 -10, 30 6 C 30 22, 12 28, 0 16 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:1.8s,0.6s" transform="translate(80 460) rotate(-40)"><path d="M0 0 C 14 -14, 30 -10, 30 6 C 30 22, 12 28, 0 16 Z" fill="url(#kvLg)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:1.9s,0.9s" transform="translate(60 320) rotate(150)"><path d="M0 0 C 14 -14, 30 -10, 30 6 C 30 22, 12 28, 0 16 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.0s,1.2s" transform="translate(90 180) rotate(-50)"><path d="M0 0 C 14 -14, 30 -10, 30 6 C 30 22, 12 28, 0 16 Z" fill="url(#kvLg)"/></g>' +
    /* Leaves — top horizontal */
    '<g class="kv-lf kv-sw" style="animation-delay:2.1s,0.2s" transform="translate(180 70) rotate(-50)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLg)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.2s,0.5s" transform="translate(360 40) rotate(160)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.3s,0.8s" transform="translate(540 50) rotate(-60)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLg)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.4s,1.1s" transform="translate(720 40) rotate(170)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.5s,1.4s" transform="translate(900 50) rotate(-50)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLg)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.6s,1.7s" transform="translate(1080 40) rotate(160)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.7s,2.0s" transform="translate(1260 50) rotate(-50)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLg)"/></g>' +
    /* Leaves — right edge */
    '<g class="kv-lf kv-sw" style="animation-delay:2.8s,0.4s" transform="translate(1410 200) rotate(-90)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.9s,0.8s" transform="translate(1410 380) rotate(-90)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLg)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:3.0s,1.2s" transform="translate(1410 560) rotate(-90)"><path d="M0 0 C 12 -12, 26 -8, 26 6 C 26 20, 10 24, 0 14 Z" fill="url(#kvLs)"/></g>' +
    /* Small accent leaves */
    '<g class="kv-lf kv-sw" style="animation-delay:2.0s,0.1s" transform="translate(120 380) rotate(-10)" opacity="0.6"><path d="M0 0 C 8 -8, 18 -6, 18 4 C 18 14, 6 16, 0 10 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.2s,0.4s" transform="translate(110 240) rotate(170)" opacity="0.6"><path d="M0 0 C 8 -8, 18 -6, 18 4 C 18 14, 6 16, 0 10 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.4s,0.7s" transform="translate(150 100) rotate(-20)" opacity="0.6"><path d="M0 0 C 8 -8, 18 -6, 18 4 C 18 14, 6 16, 0 10 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.6s,1.0s" transform="translate(420 70) rotate(-40)" opacity="0.6"><path d="M0 0 C 8 -8, 18 -6, 18 4 C 18 14, 6 16, 0 10 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:2.8s,1.3s" transform="translate(800 70) rotate(170)" opacity="0.6"><path d="M0 0 C 8 -8, 18 -6, 18 4 C 18 14, 6 16, 0 10 Z" fill="url(#kvLs)"/></g>' +
    '<g class="kv-lf kv-sw" style="animation-delay:3.0s,1.6s" transform="translate(1180 70) rotate(-40)" opacity="0.6"><path d="M0 0 C 8 -8, 18 -6, 18 4 C 18 14, 6 16, 0 10 Z" fill="url(#kvLs)"/></g>' +
    '</g>' +
    '</svg>' +
    '</div>';

  /* Footer creeper cluster */
  ov.innerHTML +=
    '<div id="kisan-footer-creeper">' +
    '<svg viewBox="0 0 380 300">' +
    '<defs><linearGradient id="kvCrp" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#3E6B3E"/><stop offset="100%" stop-color="#C7D6BD"/></linearGradient></defs>' +
    '<path d="M380 280 C 320 240, 280 200, 230 220 C 180 240, 140 200, 100 220 C 70 235, 40 220, 10 250" fill="none" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>' +
    '<path d="M340 300 C 300 260, 260 250, 220 270 C 180 290, 140 270, 100 290" fill="none" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>' +
    '<path d="M260 220 C 240 180, 220 160, 200 140 C 180 120, 170 100, 180 80" fill="none" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>' +
    '<g fill="url(#kvCrp)" stroke="#3E6B3E" stroke-width="0.8">' +
      '<path d="M250 200 C 220 170, 230 130, 270 130 C 310 130, 320 170, 290 200 Z"/>' +
      '<path d="M170 200 C 130 180, 130 130, 170 120 C 210 110, 230 160, 200 200 Z"/>' +
      '<path d="M310 240 C 290 220, 290 180, 330 180 C 360 180, 360 220, 340 240 Z"/>' +
      '<path d="M120 240 C 90 220, 90 180, 130 180 C 160 180, 160 220, 140 240 Z"/>' +
      '<path d="M200 130 C 170 110, 180 70, 220 70 C 260 70, 260 110, 230 130 Z"/>' +
      '<path d="M60 270 C 30 250, 30 220, 70 220 C 100 220, 100 250, 80 270 Z"/>' +
    '</g>' +
    '</svg>' +
    '</div>';

  /* Caterpillar host */
  ov.innerHTML +=
    '<div id="kisan-cat-host">' +
    '<div class="kcat">' +
    '<svg class="cat-svg" width="140" height="64" viewBox="0 0 140 64">' +
      /* Antennae */
      '<g class="seg antennae">' +
        '<line x1="100" y1="22" x2="106" y2="6" stroke="#3E6B3E" stroke-width="1.4" stroke-linecap="round"/>' +
        '<circle cx="106" cy="6" r="2.2" fill="#B6553A"/>' +
        '<line x1="106" y1="22" x2="114" y2="8" stroke="#3E6B3E" stroke-width="1.4" stroke-linecap="round"/>' +
        '<circle cx="114" cy="8" r="2.2" fill="#B6553A"/>' +
      '</g>' +
      /* Body segments */
      '<g class="seg s2"><circle cx="20" cy="35" r="7" fill="#82B082"/><ellipse cx="20" cy="38" rx="5" ry="2" fill="#C7D6BD" opacity="0.6"/></g>' +
      '<g class="seg s3"><circle cx="34" cy="34" r="8" fill="#3E6B3E"/><ellipse cx="34" cy="37" rx="6" ry="2.5" fill="#C7D6BD" opacity="0.6"/></g>' +
      '<g class="seg s4"><circle cx="49" cy="33" r="8.5" fill="#82B082"/><ellipse cx="49" cy="36" rx="6.5" ry="2.5" fill="#C7D6BD" opacity="0.6"/></g>' +
      '<g class="seg s5"><circle cx="65" cy="32" r="9" fill="#3E6B3E"/><ellipse cx="65" cy="35" rx="7" ry="3" fill="#C7D6BD" opacity="0.6"/></g>' +
      '<g class="seg s6"><circle cx="82" cy="30" r="10" fill="#82B082"/><ellipse cx="82" cy="33" rx="7.5" ry="3" fill="#C7D6BD" opacity="0.6"/></g>' +
      /* Head */
      '<g class="seg head">' +
        '<circle cx="100" cy="28" r="11" fill="#3E6B3E"/>' +
        '<ellipse cx="100" cy="32" rx="8" ry="3" fill="#C7D6BD" opacity="0.6"/>' +
        '<circle cx="96" cy="25" r="2.8" fill="#FBF7EC"/>' +
        '<circle class="pupil" cx="96" cy="25" r="1.5" fill="#2A3328"/>' +
        '<ellipse class="lid" cx="96" cy="25" rx="2.8" ry="2.8" fill="#3E6B3E"/>' +
        '<path class="mouth" d="M95 32 q5 2 10 0" stroke="#2A3328" stroke-width="1.2" fill="none" stroke-linecap="round"/>' +
        '<circle cx="92" cy="30" r="2" fill="#B6553A" opacity="0.35"/>' +
      '</g>' +
      /* Legs */
      '<g stroke="#3E6B3E" stroke-width="1.2" stroke-linecap="round">' +
        '<line x1="20" y1="42" x2="20" y2="46"/><line x1="34" y1="42" x2="34" y2="46"/>' +
        '<line x1="49" y1="42" x2="49" y2="46"/><line x1="65" y1="41" x2="65" y2="45"/>' +
        '<line x1="82" y1="40" x2="82" y2="44"/><line x1="100" y1="39" x2="100" y2="43"/>' +
      '</g>' +
      /* Wrench tool */
      '<g class="tool wrench">' +
        '<rect x="92" y="14" width="3" height="14" fill="#8C9684" rx="0.6"/>' +
        '<path d="M88 8 L88 16 L91 16 L91 11 L97 11 L97 16 L100 16 L100 8 Z" fill="#8C9684"/>' +
        '<circle cx="93.5" cy="13.5" r="1" fill="#5A6655"/>' +
        '<rect x="92" y="22" width="3" height="6" fill="#B6553A" rx="0.6"/>' +
        '<line x1="100" y1="33" x2="96" y2="28" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>' +
      '</g>' +
      /* Lens tool */
      '<g class="tool lens">' +
        '<line x1="106" y1="26" x2="118" y2="38" stroke="#5A6655" stroke-width="2.2" stroke-linecap="round"/>' +
        '<circle cx="104" cy="14" r="9" fill="rgba(199,214,189,0.35)" stroke="#5A6655" stroke-width="1.8"/>' +
        '<circle cx="104" cy="14" r="9" fill="none" stroke="#FBF7EC" stroke-width="0.6"/>' +
        '<path class="glint" d="M99 10 q3 -3 7 -3" stroke="#FFFCF1" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0"/>' +
        '<line x1="100" y1="22" x2="100" y2="16" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>' +
        '<line x1="100" y1="16" x2="104" y2="14" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>' +
      '</g>' +
    '</svg>' +
    '</div>' +
    '</div>';

  pdoc.body.appendChild(ov);

  /* ── Caterpillar logic — adapted from garden.jsx ── */
  var pwin = window.parent;
  var cat = pdoc.querySelector('.kcat');
  var pupil = cat.querySelector('.pupil');
  var mouth = cat.querySelector('.mouth');
  var head  = cat.querySelector('.head');

  var curX    = pwin.innerWidth * 0.3;
  var targetX = curX;
  var mouseX  = curX;
  var mouseY  = pwin.innerHeight / 2;
  var facing  = 1;
  var mood    = 'idle';
  var moodUntil = 0;

  pwin.__catMood = function(m, ms) {
    ms = ms || 1500;
    mood = m; moodUntil = performance.now() + ms;
    cat.classList.toggle('excited',  m === 'excited');
    cat.classList.toggle('thinking', m === 'thinking');
  };

  var activeSlider = null;
  function setTool(t) {
    cat.classList.toggle('tool-wrench', t === 'wrench');
    cat.classList.toggle('tool-lens',   t === 'lens');
    if (!t) cat.classList.remove('tool-wrench','tool-lens');
  }
  function satisfiedBounce() {
    cat.classList.add('bounce');
    setTimeout(function(){ cat.classList.remove('bounce'); }, 500);
  }
  function antennaeWiggle() {
    cat.classList.add('antwig');
    setTimeout(function(){ cat.classList.remove('antwig'); }, 1000);
  }

  pdoc.addEventListener('pointerdown', function(e) {
    var el = e.target;
    if (el.matches && el.matches('input[type=range]')) { activeSlider = el; setTool('wrench'); }
  }, true);
  pdoc.addEventListener('pointerup', function() {
    if (activeSlider) { activeSlider = null; setTool(null); satisfiedBounce(); }
  }, true);
  pdoc.addEventListener('focusin', function(e) {
    var el = e.target;
    if (el.matches && el.matches('input:not([type=range]), textarea, select')) setTool('lens');
  }, true);
  pdoc.addEventListener('focusout', function(e) {
    var el = e.target;
    if (el.matches && el.matches('input:not([type=range]), textarea, select')) { setTool(null); antennaeWiggle(); }
  }, true);
  pdoc.addEventListener('change', function(e) {
    if (e.target.type === 'file') { setTool(null); antennaeWiggle(); }
  }, true);
  pdoc.addEventListener('dragenter', function() { setTool('lens'); }, true);
  pdoc.addEventListener('dragleave', function() { setTool(null); }, true);
  pdoc.addEventListener('drop',      function() { setTool(null); antennaeWiggle(); }, true);

  pwin.addEventListener('mousemove', function(e) {
    mouseX = e.clientX; mouseY = e.clientY;
    targetX = Math.max(20, Math.min(pwin.innerWidth - 140, mouseX - 70));
  });
  pwin.addEventListener('click', function() { pwin.__catMood('excited', 900); });

  setInterval(function() {
    if (!cat.classList.contains('tool-lens') && !cat.classList.contains('tool-wrench')) {
      cat.classList.add('blink');
      setTimeout(function(){ cat.classList.remove('blink'); }, 320);
    }
  }, 8000);

  function frame(now) {
    if (now > moodUntil && mood !== 'idle') { mood = 'idle'; cat.classList.remove('excited','thinking'); }
    var dx = targetX - curX;
    curX += dx * 0.06;
    var moving = Math.abs(dx) > 1.5;
    var want = (mouseX > curX + 70) ? 1 : -1;
    if (want !== facing && moving) facing = want;
    cat.style.transform = 'translateX(' + curX + 'px) scaleX(' + facing + ')';

    var hr = head.getBoundingClientRect();
    var hx = hr.left + hr.width  / 2;
    var hy = hr.top  + hr.height / 2;
    var ang = Math.atan2(mouseY - hy, (mouseX - hx) * facing);
    var px = Math.cos(ang) * 1.6;
    var py = Math.sin(ang) * 1.6;
    pupil.setAttribute('cx', 96 + px);
    pupil.setAttribute('cy', 25 + py);

    if      (cat.classList.contains('tool-wrench')) mouth.setAttribute('d','M95 32 q5 0 10 0');
    else if (cat.classList.contains('tool-lens'))   mouth.setAttribute('d','M96 32 q4 1 8 0');
    else if (mood === 'excited')                    mouth.setAttribute('d','M93 31 q7 5 14 0');
    else if (mood === 'thinking')                   mouth.setAttribute('d','M95 33 q5 -1 10 0');
    else                                            mouth.setAttribute('d','M95 32 q5 2 10 0');

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
</script>
"""
