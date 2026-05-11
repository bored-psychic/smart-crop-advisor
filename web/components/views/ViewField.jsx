// ViewField — single view
const { useState, useEffect, useRef, useMemo, useCallback } = React;

function ViewField({ profile, setProfile, t }){
  const items=[
    {emo:'☀️',title:'Bright and dry',body:'A good day to spray and harvest. Soil moisture is fine.',tone:'leaf'},
    {emo:'🌧',title:'Light rain at dusk',body:'About 2.4 mm expected. Open drainage on plot B.',tone:'warn'},
    {emo:'🦗',title:'Locusts 180 km west',body:"Wind shift in 48 h. We'll let you know if it gets closer.",tone:'alert'},
    {emo:'🌱',title:'Canopy looks healthy',body:'NDVI 0.71 — your crop is growing on schedule.',tone:'leaf'},
  ];
  const tone={leaf:'var(--leaf)',warn:'#A06B1F',alert:'var(--berry)'};
  return (
    <div className="view-fade">
      <Topbar crumb="Field Watch"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">field</div>
          <h1 className="page-title">A <em>quiet daily check-in</em> for your land.</h1>
          <p className="page-lede">Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.</p>
        </div>
      </div>

      <LocationBar village={profile.village} setVillage={v=>setProfile({...profile,village:v})}
        state={profile.state} setState={s=>setProfile({...profile,state:s})}
        extra={<button className="btn primary" style={{padding:'8px 14px',fontSize:12}} onClick={()=>window.__catMood?.('excited',1500)}>🛰 Scan now</button>}/>

      <div className="grid-4" style={{marginBottom:18}}>
        {[['Temperature','29.4°C','feels 31'],['Humidity','64%','dewpt 22'],['Wind','12 km/h','NE'],['Rain · 24h','2.4 mm','prob 18%']].map(s=>(
          <div key={s[0]} className="card rise" style={{padding:'18px 20px'}}>
            <div className="page-eyebrow">{s[0]}</div>
            <div className="bignum" style={{fontSize:32,marginTop:6}}><em>{s[1]}</em></div>
            <div className="muted small" style={{marginTop:4}}>{s[2]}</div>
          </div>
        ))}
      </div>

      <div className="card rise rise-2">
        <div className="card-h"><h3>Today's notes</h3><span className="meta">last 24 hours · {profile.village}</span></div>
        <div style={{display:'flex',flexDirection:'column',gap:12}}>
          {items.map((i,k)=>(
            <div key={k} style={{display:'grid',gridTemplateColumns:'40px 180px 1fr',gap:14,alignItems:'center',padding:'12px 4px',borderBottom:'1px solid var(--line)'}}>
              <div style={{fontSize:24}}>{i.emo}</div>
              <div style={{fontFamily:'var(--display)',fontSize:18,color:tone[i.tone]}}>{i.title}</div>
              <div style={{color:'var(--ink-soft)',fontSize:14}}>{i.body}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.ViewField = ViewField;
