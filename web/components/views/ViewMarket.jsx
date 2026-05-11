// ViewMarket — single view
const { useState, useEffect, useRef, useMemo, useCallback } = React;

function genSeries(b,n=60){let arr=[],p=b;for(let i=0;i<n;i++){p=p*(1+(Math.random()-0.48)*0.025+0.0008);arr.push(p)}return arr}
function ViewMarket({ profile, setProfile, t }){
  const [crop,setCrop]=useState('Cotton');
  const series=useMemo(()=>genSeries({Cotton:6800,Wheat:2400,Rice:2100,Maize:1850,Onion:2000,Tomato:1300}[crop]||3000,60),[crop]);
  const fc=useMemo(()=>genSeries(series[series.length-1],14),[series]);
  const today=series[series.length-1], yest=series[series.length-2];
  const change=((today-yest)/yest)*100, target=fc[fc.length-1], upside=((target-today)/today)*100;

  const W=720,H=220,pad=30;
  const all=[...series,...fc]; const min=Math.min(...all), max=Math.max(...all);
  const x=i=>pad+i*(W-pad*2)/(all.length-1);
  const y=v=>H-pad-((v-min)/(max-min))*(H-pad*2);
  const path=(arr,off=0)=>arr.map((v,i)=>`${i===0?'M':'L'}${x(i+off)},${y(v)}`).join(' ');

  return (
    <div className="view-fade">
      <Topbar crumb="Market"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">market</div>
          <h1 className="page-title">A <em>fair price,</em> a calm decision.</h1>
          <p className="page-lede">We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.</p>
        </div>
      </div>

      <LocationBar village={profile.village} setVillage={v=>setProfile({...profile,village:v})}
        state={profile.state} setState={s=>setProfile({...profile,state:s})}
        extra={
          <select className="input" value={crop} onChange={e=>setCrop(e.target.value)}>
            {['Cotton','Wheat','Rice','Maize','Onion','Tomato'].map(c=><option key={c}>{c}</option>)}
          </select>
        }/>

      <div className="card rise rise-2">
        <div className="card-h">
          <h3 style={{margin:0}}>Today's mandi · {crop}</h3>
          <span className="tag">📍 {profile.state}</span>
        </div>
        <div className="grid-3" style={{marginBottom:14}}>
          <div>
            <div className="page-eyebrow">spot price</div>
            <div className="bignum">₹<em>{today.toFixed(0)}</em><span className="unit">/q</span></div>
            <div className="small" style={{color:change>=0?'var(--leaf)':'var(--berry)',marginTop:4}}>{change>=0?'▲':'▼'} {Math.abs(change).toFixed(2)}% from yesterday</div>
          </div>
          <div>
            <div className="page-eyebrow">in 14 days</div>
            <div className="bignum">₹<em>{target.toFixed(0)}</em><span className="unit">/q</span></div>
            <div className="small" style={{color:upside>=0?'var(--leaf)':'var(--berry)',marginTop:4}}>{upside>=0?'▲':'▼'} {Math.abs(upside).toFixed(2)}% expected</div>
          </div>
          <div>
            <div className="page-eyebrow">our advice</div>
            <div className="bignum"><em style={{color:upside>2?'var(--leaf)':upside<-2?'var(--berry)':'#A06B1F'}}>{upside>2?'wait':upside<-2?'sell':'either way'}</em></div>
            <div className="small muted" style={{marginTop:4}}>{upside>2?`hold for ~₹${(target-today).toFixed(0)} more`:upside<-2?'price likely to slip':'pretty steady'}</div>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} style={{width:'100%',height:220,display:'block'}}>
          <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="rgba(62,107,62,0.18)"/><stop offset="100%" stopColor="rgba(62,107,62,0)"/></linearGradient></defs>
          {[0,1,2,3].map(i=><line key={i} x1={pad} y1={pad+i*(H-pad*2)/3} x2={W-pad} y2={pad+i*(H-pad*2)/3} stroke="rgba(42,51,40,0.06)"/>)}
          <path d={series.map((v,i)=>`${i===0?'M':'L'}${x(i)},${y(v)}`).join(' ')+` L${x(series.length-1)},${H-pad} L${x(0)},${H-pad} Z`} fill="url(#ag)"/>
          <path d={path(series,0)} fill="none" stroke="var(--leaf)" strokeWidth="2" strokeLinecap="round"/>
          <path d={path(fc,series.length-1)} fill="none" stroke="var(--leaf)" strokeWidth="2" strokeDasharray="3 5" strokeLinecap="round" opacity="0.7"/>
          <line x1={x(series.length-1)} y1={pad} x2={x(series.length-1)} y2={H-pad} stroke="var(--ink-faint)" strokeDasharray="2 4" opacity="0.3"/>
          <text x={x(series.length-1)+4} y={pad+10} className="spark-axis">today</text>
        </svg>
      </div>
    </div>
  );
}

window.ViewMarket = ViewMarket;
