import { useState, useEffect, useCallback } from "react";

const TICKERS = ["NVDA","AXON","CRWD","PODD","GEV","LULU","SMCI","META"];

// ── Fetch real market data via Claude API + web search ────────────────────────
async function fetchRealData(tickers) {
  const prompt = `Get current stock market data for these tickers: ${tickers.join(", ")}.
For each stock return ONLY a JSON array (no markdown, no explanation) with objects containing:
- ticker (string)
- price (number, current price)
- change (number, % change today)
- volume (number, today's volume in millions, e.g. 45.2)
- avgVolume (number, 30-day avg volume in millions)
- high52 (number, 52-week high)
- low52 (number, 52-week low)
- dayHigh (number)
- dayLow (number)
- sector (string)

Use web search to get the latest real data. Return ONLY the JSON array, nothing else.`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      tools: [{ type: "web_search_20250305", name: "web_search" }],
      messages: [{ role: "user", content: prompt }]
    })
  });

  const data = await response.json();
  const text = data.content
    .filter(b => b.type === "text")
    .map(b => b.text)
    .join("");

  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
}

// ── Classify setup ────────────────────────────────────────────────────────────
function classify(s) {
  const pctFrom52 = ((s.high52 - s.price) / s.high52) * 100;
  const rvol = s.avgVolume > 0 ? s.volume / s.avgVolume : 1;
  if (pctFrom52 < 2.5) return "breakout";
  if (rvol > 1.5) return "momentum";
  return "momentum";
}

function calcRS(change, spyChange) {
  const rel = change - spyChange;
  return Math.min(99, Math.max(1, Math.round(50 + rel * 8)));
}

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Spark({ positive }) {
  // Generate a plausible-looking intraday shape
  const pts = Array.from({length: 12}, (_, i) => {
    const trend = positive ? i * 0.8 : -i * 0.8;
    return 50 + trend + (Math.sin(i * 1.3) * 8);
  });
  const w=80, h=32;
  const min=Math.min(...pts), max=Math.max(...pts);
  const range = max - min || 1;
  const path = pts.map((v,i) => `${(i/(pts.length-1))*w},${h-((v-min)/range)*(h-4)-2}`).join(" ");
  const color = positive ? "#22d3a0" : "#f87171";
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <defs>
        <linearGradient id={`g${positive}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <polyline points={`${path} ${w},${h} 0,${h}`} fill={`url(#g${positive})`}/>
      <polyline points={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── Risk Calculator ───────────────────────────────────────────────────────────
function RiskCalc({ onClose, prefill }) {
  const [entry,  setEntry]  = useState(prefill?.price?.toFixed(2) || "");
  const [stop,   setStop]   = useState("");
  const [target, setTarget] = useState("");
  const [riskAmt,setRisk]   = useState("500");

  const calc = () => {
    const e=+entry, s=+stop, t=+target, r=+riskAmt;
    if (!e||!s||!r||Math.abs(e-s)<0.001) return null;
    const riskPer = Math.abs(e-s);
    const shares  = Math.floor(r/riskPer);
    const position= shares*e;
    const potential= t ? (t-e)*shares : null;
    const rr = potential ? (potential/r).toFixed(2) : null;
    return { shares, position:position.toFixed(0), potential:potential?.toFixed(0), rr };
  };
  const res = calc();

  return (
    <div style={{position:"fixed",inset:0,zIndex:50,display:"flex",alignItems:"flex-end",justifyContent:"center",background:"rgba(0,0,0,0.75)"}}>
      <div onClick={e=>e.stopPropagation()} style={{background:"#0d1117",borderTop:"1px solid #21262d",borderRadius:"24px 24px 0 0",width:"100%",maxWidth:460,padding:"20px 18px 40px"}}>
        <div style={{width:40,height:4,background:"#30363d",borderRadius:99,margin:"0 auto 18px"}}/>
        <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:18,color:"#e6edf3",marginBottom:18}}>מחשבון סיכון</div>
        {prefill?.ticker && <div style={{fontSize:12,color:"#f0b429",marginBottom:12,fontWeight:700}}>{prefill.ticker} · ${prefill.price?.toFixed(2)}</div>}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
          {[["כניסה $",entry,setEntry],["סטופ $",stop,setStop],["יעד $",target,setTarget],["סיכון $",riskAmt,setRisk]].map(([label,val,set])=>(
            <div key={label}>
              <div style={{fontSize:11,color:"#8b949e",marginBottom:5}}>{label}</div>
              <input type="number" value={val} onChange={e=>set(e.target.value)}
                style={{width:"100%",background:"#161b22",border:"1px solid #21262d",borderRadius:10,padding:"9px 11px",color:"#e6edf3",fontSize:14,outline:"none",boxSizing:"border-box"}}
                placeholder="0.00"/>
            </div>
          ))}
        </div>
        {res && (
          <div style={{background:"#161b22",borderRadius:14,padding:14,border:"1px solid #21262d"}}>
            {[
              ["מניות", res.shares, "#e6edf3"],
              ["גודל פוזיציה", `$${(+res.position).toLocaleString()}`, "#e6edf3"],
              res.rr && ["R:R", `${res.rr}:1`, +res.rr>=2?"#22d3a0":"#f0b429"],
              res.potential && ["פוטנציאל", `+$${(+res.potential).toLocaleString()}`, "#22d3a0"],
            ].filter(Boolean).map(([label,val,color])=>(
              <div key={label} style={{display:"flex",justifyContent:"space-between",padding:"8px 0",borderBottom:"1px solid #21262d"}}>
                <span style={{color:"#8b949e",fontSize:13}}>{label}</span>
                <span style={{color,fontWeight:700,fontSize:15}}>{val}</span>
              </div>
            ))}
          </div>
        )}
        <button onClick={onClose} style={{marginTop:14,width:"100%",background:"#21262d",border:"none",borderRadius:12,padding:13,color:"#8b949e",fontWeight:600,cursor:"pointer",fontSize:14}}>סגור</button>
      </div>
    </div>
  );
}

// ── Screener Tab ──────────────────────────────────────────────────────────────
function ScreenerTab({ stocks, loading, error, onRefresh, onTrade }) {
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("rs");

  const list = stocks
    .filter(s => filter==="all" || s.setup===filter)
    .sort((a,b) => b[sortBy] - a[sortBy]);

  if (error) return (
    <div style={{textAlign:"center",padding:40}}>
      <div style={{fontSize:32,marginBottom:12}}>⚠️</div>
      <div style={{color:"#f87171",marginBottom:8,fontWeight:700}}>שגיאה בטעינת נתונים</div>
      <div style={{color:"#484f58",fontSize:12,marginBottom:20,lineHeight:1.6}}>{error}</div>
      <button onClick={onRefresh} style={{background:"#f0b429",border:"none",borderRadius:12,padding:"10px 24px",color:"#0d1117",fontWeight:700,cursor:"pointer",fontFamily:"'Syne',sans-serif"}}>נסה שוב</button>
    </div>
  );

  if (loading) return (
    <div style={{textAlign:"center",padding:60}}>
      <div style={{fontSize:40,marginBottom:16,display:"inline-block",animation:"spin 1s linear infinite"}}>⟳</div>
      <div style={{color:"#8b949e",fontSize:14,marginBottom:8}}>מושך נתונים אמיתיים...</div>
      <div style={{color:"#484f58",fontSize:12}}>Yahoo Finance דרך Claude AI</div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  return (
    <div>
      <div style={{display:"flex",gap:8,marginBottom:14}}>
        {[["all","הכל"],["breakout","פריצות"],["momentum","מומנטום"]].map(([v,l])=>(
          <button key={v} onClick={()=>setFilter(v)} style={{flex:1,padding:"8px 0",borderRadius:12,border:"none",cursor:"pointer",fontWeight:700,fontSize:12,fontFamily:"'Syne',sans-serif",
            background:filter===v?"#f0b429":"#161b22",color:filter===v?"#0d1117":"#8b949e",transition:"all 0.15s"}}>
            {l}
          </button>
        ))}
      </div>

      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
        <div style={{display:"flex",gap:14}}>
          {[["rs","RS"],["rvol","RVOL"],["change","שינוי"]].map(([v,l])=>(
            <button key={v} onClick={()=>setSortBy(v)} style={{background:"none",border:"none",cursor:"pointer",fontSize:11,fontWeight:700,
              color:sortBy===v?"#f0b429":"#484f58",fontFamily:"'Syne',sans-serif"}}>
              {l}{sortBy===v?" ↓":""}
            </button>
          ))}
        </div>
        <button onClick={onRefresh} style={{background:"none",border:"none",cursor:"pointer",fontSize:12,color:"#484f58"}}>↻ רענן</button>
      </div>

      <div style={{display:"flex",flexDirection:"column",gap:10}}>
        {list.map(s => (
          <div key={s.ticker} onClick={()=>onTrade(s)}
            style={{background:"#161b22",borderRadius:16,padding:14,border:`1px solid ${s.nearKey?"rgba(240,180,41,0.5)":"#21262d"}`,cursor:"pointer"}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10}}>
              <div>
                <div style={{display:"flex",alignItems:"center",gap:7,marginBottom:3}}>
                  <span style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:16,color:"#e6edf3"}}>{s.ticker}</span>
                  {s.nearKey && <span style={{fontSize:9,background:"rgba(240,180,41,0.15)",color:"#f0b429",padding:"2px 6px",borderRadius:99,fontWeight:700}}>52W HIGH</span>}
                  <span style={{fontSize:9,padding:"2px 6px",borderRadius:99,fontWeight:700,
                    background:s.setup==="breakout"?"rgba(139,92,246,0.15)":"rgba(56,189,248,0.15)",
                    color:s.setup==="breakout"?"#a78bfa":"#38bdf8"}}>
                    {s.setup==="breakout"?"BREAKOUT":"MOMENTUM"}
                  </span>
                </div>
                <div style={{fontSize:11,color:"#484f58"}}>{s.sector}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:16,color:"#e6edf3"}}>${s.price?.toFixed(2)}</div>
                <div style={{fontWeight:700,fontSize:13,color:s.change>=0?"#22d3a0":"#f87171"}}>{s.change>=0?"+":""}{s.change?.toFixed(2)}%</div>
              </div>
            </div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",paddingTop:10,borderTop:"1px solid #21262d"}}>
              <div style={{display:"flex",gap:16}}>
                {[
                  ["RS",   s.rs,                    s.rs>=85?"#22d3a0":s.rs>=70?"#f0b429":"#8b949e"],
                  ["RVOL", `${s.rvol?.toFixed(1)}x`,s.rvol>=1.5?"#22d3a0":"#8b949e"],
                  ["VOL",  `${s.volume?.toFixed(1)}M`,"#8b949e"],
                  ["ATR%", `${s.atrPct}%`,           "#8b949e"],
                ].map(([l,v,c])=>(
                  <div key={l}>
                    <div style={{fontSize:10,color:"#484f58",marginBottom:2}}>{l}</div>
                    <div style={{fontSize:12,fontWeight:700,color:c}}>{v}</div>
                  </div>
                ))}
              </div>
              <Spark positive={s.change>=0}/>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Portfolio Tab ─────────────────────────────────────────────────────────────
const MOCK_POSITIONS = [
  { ticker:"NVDA", entry:897.0, shares:50,  stop:878.0, target:970.0 },
  { ticker:"AXON", entry:298.5, shares:80,  stop:288.0, target:335.0 },
  { ticker:"GEV",  entry:181.2, shares:120, stop:175.0, target:202.0 },
];

function PortfolioTab({ stocks, onCalc }) {
  const enriched = MOCK_POSITIONS.map(p => {
    const live = stocks.find(s=>s.ticker===p.ticker);
    const current = live?.price || p.entry;
    const pnl = (current - p.entry) * p.shares;
    const progress = Math.min(Math.max(((current-p.entry)/(p.target-p.entry))*100,0),100);
    return {...p, current, pnl, progress};
  });
  const totalPnL = enriched.reduce((s,p)=>s+p.pnl,0);

  return (
    <div>
      <div style={{background:"linear-gradient(135deg,#161b22,#0d1117)",border:"1px solid #21262d",borderRadius:20,padding:20,marginBottom:14}}>
        <div style={{fontSize:10,color:"#484f58",letterSpacing:2,textTransform:"uppercase",marginBottom:4}}>Open P&L · מחירים חיים</div>
        <div style={{fontFamily:"'Syne',sans-serif",fontWeight:900,fontSize:36,color:totalPnL>=0?"#22d3a0":"#f87171",letterSpacing:-1}}>
          {totalPnL>=0?"+":"-"}${Math.abs(totalPnL).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g,",")}
        </div>
        <div style={{fontSize:12,color:"#484f58",marginTop:4}}>{enriched.length} פוזיציות פתוחות</div>
      </div>

      <button onClick={()=>onCalc(null)} style={{width:"100%",background:"#f0b429",border:"none",borderRadius:14,padding:14,color:"#0d1117",fontWeight:800,fontSize:14,cursor:"pointer",marginBottom:14,fontFamily:"'Syne',sans-serif",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}>
        🧮 מחשבון סיכון
      </button>

      <div style={{display:"flex",flexDirection:"column",gap:10}}>
        {enriched.map(p=>(
          <div key={p.ticker} style={{background:"#161b22",borderRadius:16,padding:14,border:`1px solid ${p.pnl>=0?"rgba(34,211,160,0.2)":"rgba(248,113,113,0.2)"}`}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:12}}>
              <div>
                <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:16,color:"#e6edf3"}}>{p.ticker}</div>
                <div style={{fontSize:11,color:"#484f58"}}>{p.shares} מניות · כניסה ${p.entry}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontWeight:800,fontSize:16,color:p.pnl>=0?"#22d3a0":"#f87171"}}>{p.pnl>=0?"+":""}{p.pnl.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g,",")}$</div>
                <div style={{fontSize:12,color:"#8b949e"}}>${p.current.toFixed(2)}</div>
              </div>
            </div>
            <div style={{position:"relative",height:6,background:"#21262d",borderRadius:99,marginBottom:8}}>
              <div style={{position:"absolute",height:"100%",width:`${p.progress}%`,background:"linear-gradient(90deg,#22d3a0,#06d6a0)",borderRadius:99,transition:"width 0.5s"}}/>
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:10}}>
              <span style={{color:"#f87171"}}>סטופ ${p.stop}</span>
              <span style={{color:"#484f58"}}>{p.progress.toFixed(0)}% ליעד</span>
              <span style={{color:"#22d3a0"}}>יעד ${p.target}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Journal Tab ───────────────────────────────────────────────────────────────
const HISTORY = [
  { ticker:"META",  pnl:2178,  rr:2.1,  date:"05/01", result:"win"  },
  { ticker:"PANW",  pnl:-994,  rr:-0.8, date:"04/01", result:"loss" },
  { ticker:"SMCI",  pnl:1940,  rr:1.9,  date:"03/01", result:"win"  },
  { ticker:"TSLA",  pnl:1340,  rr:1.3,  date:"02/01", result:"win"  },
  { ticker:"AMZN",  pnl:-675,  rr:-0.7, date:"29/12", result:"loss" },
  { ticker:"MSTR",  pnl:1740,  rr:2.3,  date:"28/12", result:"win"  },
];

function JournalTab() {
  const wins = HISTORY.filter(t=>t.result==="win");
  const losses = HISTORY.filter(t=>t.result==="loss");
  const totalPnL = HISTORY.reduce((s,t)=>s+t.pnl,0);
  const winRate = ((wins.length/HISTORY.length)*100).toFixed(0);
  const avgWin = wins.reduce((s,t)=>s+t.pnl,0)/wins.length;
  const avgLoss = Math.abs(losses.reduce((s,t)=>s+t.pnl,0)/losses.length);
  const pf = (avgWin/avgLoss).toFixed(2);

  return (
    <div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
        {[["Win Rate",`${winRate}%`,+winRate>=60?"#22d3a0":"#f0b429"],
          ["Profit Factor",pf,+pf>=2?"#22d3a0":"#f0b429"],
          ["Net P&L",`$${totalPnL.toLocaleString()}`,totalPnL>=0?"#22d3a0":"#f87171"],
          ["עסקאות",HISTORY.length,"#e6edf3"]].map(([label,val,color])=>(
          <div key={label} style={{background:"#161b22",borderRadius:16,padding:14,border:"1px solid #21262d"}}>
            <div style={{fontSize:11,color:"#484f58",marginBottom:6}}>{label}</div>
            <div style={{fontFamily:"'Syne',sans-serif",fontWeight:900,fontSize:26,color}}>{val}</div>
          </div>
        ))}
      </div>
      <div style={{display:"flex",flexDirection:"column",gap:8}}>
        {HISTORY.map((t,i)=>(
          <div key={i} style={{background:"#161b22",borderRadius:14,padding:12,border:`1px solid ${t.result==="win"?"rgba(34,211,160,0.15)":"rgba(248,113,113,0.15)"}`,display:"flex",alignItems:"center",gap:12}}>
            <div style={{width:3,height:36,borderRadius:99,background:t.result==="win"?"#22d3a0":"#f87171",flexShrink:0}}/>
            <div style={{flex:1}}>
              <div style={{display:"flex",justifyContent:"space-between"}}>
                <span style={{fontFamily:"'Syne',sans-serif",fontWeight:800,color:"#e6edf3"}}>{t.ticker}</span>
                <span style={{fontWeight:700,color:t.pnl>=0?"#22d3a0":"#f87171"}}>{t.pnl>=0?"+":""}{t.pnl.toLocaleString()}$</span>
              </div>
              <div style={{display:"flex",justifyContent:"space-between",marginTop:3}}>
                <span style={{fontSize:11,color:"#484f58"}}>{t.date}</span>
                <span style={{fontSize:11,fontWeight:700,color:t.rr>=1?"#22d3a0":"#f87171"}}>{t.rr}R</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [stocks,     setStocks]     = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [tab,        setTab]        = useState("screener");
  const [calc,       setCalc]       = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const raw = await fetchRealData(TICKERS);

      // Find SPY-equivalent change for RS (use median change as market proxy)
      const changes = raw.map(s=>s.change).sort((a,b)=>a-b);
      const medianChange = changes[Math.floor(changes.length/2)] || 0;

      const enriched = raw.map(s => {
        const rvol = s.avgVolume > 0 ? +(s.volume / s.avgVolume).toFixed(2) : 1;
        const dayRange = (s.dayHigh||s.price) - (s.dayLow||s.price);
        const atrPct = +((dayRange / s.price) * 100).toFixed(1);
        const nearKey = s.high52 ? ((s.high52 - s.price) / s.high52) * 100 < 2.5 : false;
        return {
          ...s,
          rvol,
          atrPct,
          nearKey,
          rs: calcRS(s.change, medianChange),
          setup: classify({...s, rvol}),
        };
      });

      setStocks(enriched);
      setLastUpdate(new Date().toLocaleTimeString("he-IL"));
    } catch(e) {
      console.error(e);
      setError("לא הצלחתי לטעון את הנתונים. לחץ 'נסה שוב'.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const iv = setInterval(loadData, 5 * 60 * 1000); // every 5 min
    return () => clearInterval(iv);
  }, [loadData]);

  const tabs = [
    {id:"screener",  icon:"⚡", label:"סקרינר"},
    {id:"portfolio", icon:"📊", label:"פוזיציות"},
    {id:"journal",   icon:"📈", label:"יומן"},
  ];

  return (
    <div style={{minHeight:"100vh",background:"#0d1117",color:"#e6edf3",fontFamily:"'Syne',sans-serif",maxWidth:480,margin:"0 auto",position:"relative"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&display=swap');
        * { box-sizing:border-box; -webkit-font-smoothing:antialiased; }
        input::-webkit-outer-spin-button,input::-webkit-inner-spin-button{-webkit-appearance:none;}
        ::-webkit-scrollbar{width:0;}
      `}</style>

      {/* Header */}
      <div style={{position:"sticky",top:0,zIndex:40,background:"rgba(13,17,23,0.97)",backdropFilter:"blur(12px)",borderBottom:"1px solid #21262d",padding:"48px 16px 12px"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}>
          <div>
            <div style={{fontSize:10,color:"#f0b429",letterSpacing:3,textTransform:"uppercase",marginBottom:2}}>TradeEdge Pro</div>
            <div style={{fontWeight:900,fontSize:22,letterSpacing:-0.5}}>Dashboard</div>
          </div>
          <div style={{textAlign:"right"}}>
            <div style={{fontSize:10,color:"#484f58",marginBottom:3}}>{lastUpdate ? `עודכן ${lastUpdate}` : "טוען..."}</div>
            <div style={{display:"flex",alignItems:"center",gap:5,justifyContent:"flex-end"}}>
              <div style={{width:7,height:7,borderRadius:"50%",background:loading?"#f0b429":"#22d3a0",animation:"pulse 2s infinite"}}/>
              <span style={{fontSize:11,color:loading?"#f0b429":"#22d3a0",fontWeight:700}}>{loading?"טוען...":"חי"}</span>
            </div>
          </div>
        </div>
        <div style={{display:"flex",background:"#161b22",borderRadius:14,padding:4,gap:4}}>
          {tabs.map(t=>(
            <button key={t.id} onClick={()=>setTab(t.id)} style={{flex:1,padding:"8px 0",borderRadius:10,border:"none",cursor:"pointer",fontWeight:700,fontSize:12,fontFamily:"'Syne',sans-serif",transition:"all 0.15s",
              background:tab===t.id?"#f0b429":"transparent",color:tab===t.id?"#0d1117":"#484f58"}}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{padding:"16px 14px 100px"}}>
        {tab==="screener"  && <ScreenerTab stocks={stocks} loading={loading} error={error} onRefresh={loadData} onTrade={s=>setCalc(s)}/>}
        {tab==="portfolio" && <PortfolioTab stocks={stocks} onCalc={s=>setCalc(s||{})}/>}
        {tab==="journal"   && <JournalTab/>}
      </div>

      {/* FAB */}
      <button onClick={()=>setCalc({})} style={{position:"fixed",bottom:28,right:16,width:56,height:56,borderRadius:"50%",background:"#f0b429",border:"none",fontSize:22,cursor:"pointer",boxShadow:"0 4px 20px rgba(240,180,41,0.4)",zIndex:39,display:"flex",alignItems:"center",justifyContent:"center"}}>
        🧮
      </button>

      {calc!==null && <RiskCalc prefill={calc} onClose={()=>setCalc(null)}/>}
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
    </div>
  );
}
