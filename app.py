
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Stock Scanner Wyckoff Pro v3",page_icon="📊",layout="wide")
UNIVERSE="""AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA BRK-B LLY WMT JPM V MA ORCL COST NFLX AMD ADBE INTC MU PLTR COIN SOFI RIVN SMCI SHOP UBER ARM CRWD PANW MRVL QCOM TXN BA CAT XOM CVX KO PEP MCD NKE DIS BABA TCEHY ASML NVO SAP TM SONY TSM"""

def rsi(s,n=14):
    d=s.diff();u=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean();dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+u/dn.replace(0,np.nan))

def engine(df):
    c,h,l,v=df.Close,df.High,df.Low,df.Volume
    ma20=c.rolling(20).mean();ma50=c.rolling(50).mean();ma200=c.rolling(200).mean();vol20=v.rolling(20).mean()
    last=float(c.iloc[-1]); events=[];pts=0.
    low60=float(l.tail(60).min());high60=float(h.tail(60).max());pos=(last-low60)/max(high60-low60,1e-9)
    effort=float(v.iloc[-1]/vol20.iloc[-1]) if vol20.iloc[-1] else 1
    ret20=last/float(c.iloc[-21])-1;ret60=last/float(c.iloc[-61])-1;ret120=last/float(c.iloc[-121])-1
    if len(c)>=25:
        support=float(l.iloc[-21:-2].min())
        if l.iloc[-2]<support and last>support:events.append("Spring");pts+=1.7 if effort>=1.2 else 1
    if len(c)>=15:
        peak=float(c.iloc[-12:-3].max());pb=(peak-last)/max(peak,1e-9)
        if .02<pb<.12 and effort<.9 and last>low60*1.03:events.append("Test");pts+=1.1
    if len(c)>=25:
        breakout=last>=float(h.iloc[-21:-1].max())*.995;up=last/float(c.iloc[-2])-1>.035
        if breakout and up and effort>=1.4:events.append("SOS");pts+=1.8
    if len(c)>=15:
        base=float(c.iloc[-15:-5].max());rl=float(c.iloc[-8:-1].min())
        if last>=base*.97 and rl>low60*1.05 and effort<1.2:events.append("LPS");pts+=1.2
    ret5=last/float(c.iloc[-6])-1
    if ret5<-.08 and effort>=1.5 and pos<.3:events.append("SC/Absorption");pts+=1
    if len(c)>=25:
        resistance=float(h.iloc[-21:-2].max())
        if h.iloc[-1]>resistance and last<resistance and effort>=1.3:events.append("UT/UTAD");pts-=1.6
    if last>ma50.iloc[-1]>ma200.iloc[-1] and ret20>.04:phase="Markup"
    elif last<ma50.iloc[-1]<ma200.iloc[-1] and ret20<-.04:phase="Markdown"
    elif ret120<-.10 and pos<.35 and abs(ret20)<.12:phase="Accumulation"
    elif ret120>.15 and pos>.65 and abs(ret20)<.12:phase="Distribution"
    else:phase="Transition"
    pts+={"Accumulation":1.2,"Markup":.7,"Distribution":-.8,"Markdown":-1.1,"Transition":0}[phase]
    rr=float(rsi(c).iloc[-1])
    if last>ma50.iloc[-1]:pts+=.4
    if ma50.iloc[-1]>ma200.iloc[-1]:pts+=.5
    if 50<=rr<=68:pts+=.4
    if effort>=1.5:pts+=.4
    if ret20>.05:pts+=.3
    if ret20<-.1:pts-=.4
    return {"phase":phase,"events":events,"score":float(np.clip(5+pts,0,10)),"rsi":rr,"vol":effort,"ret20":ret20*100,"ret60":ret60*100}

def getdf(sym,period="2y",interval="1d"):
    x=yf.download(sym,period=period,interval=interval,auto_adjust=True,progress=False,threads=False)
    if isinstance(x.columns,pd.MultiIndex):x=x.xs(sym,axis=1,level=1,drop_level=True)
    return x.dropna(subset=["Close"]) if not x.empty else x

def scan(sym):
    try:
        d=getdf(sym,"2y","1d")
        if len(d)<210:return None
        w=getdf(sym,"5y","1wk")
        if len(w)<100:return None
        day=engine(d);week=engine(w)
        alignment=0
        if week["phase"] in ("Accumulation","Markup"):alignment+=2
        if day["phase"] in ("Accumulation","Markup"):alignment+=2
        if week["score"]>=7:alignment+=1
        if day["score"]>=7:alignment+=1
        if week["phase"] in ("Distribution","Markdown"):alignment-=2
        if day["phase"] in ("Distribution","Markdown"):alignment-=2
        setup="Neutral"
        ev=day["events"]
        if "Spring" in ev and day["phase"]=="Accumulation":setup="Spring Reversal"
        elif "SOS" in ev and ("Accumulation" in (day["phase"],week["phase"])):setup="SOS Breakout"
        elif "LPS" in ev and day["phase"] in ("Accumulation","Markup"):setup="LPS Continuation"
        elif day["phase"]=="Markup" and week["phase"]=="Markup":setup="Trend Continuation"
        elif "Test" in ev:setup="Test / Re-accumulation"
        elif "UT/UTAD" in ev:setup="Distribution Warning"
        quality=float(np.clip(5+(day["score"]-5)*.45+(week["score"]-5)*.45+alignment*.35,0,10))
        return {"Symbol":sym,"Date":str(d.index[-1].date()),"Price":float(d.Close.iloc[-1]),
                "Daily":day["phase"],"Weekly":week["phase"],"Setup":setup,
                "Setup Score":round(quality,2),"Daily Score":round(day["score"],2),"Weekly Score":round(week["score"],2),
                "Events":", ".join(ev) if ev else "—","RSI":round(day["rsi"],1),"Vol x":round(day["vol"],2),
                "20D %":round(day["ret20"],1),"60D %":round(day["ret60"],1)}
    except Exception:return None

st.title("📊 Stock Scanner — Wyckoff Pro v3")
st.caption("Multi-Timeframe: Weekly + Daily • Setup Engine • Spring / SOS / LPS / Test • EOD")

with st.sidebar:
    raw=st.text_area("Universe",UNIVERSE,height=220)
    workers=st.slider("Parallel scans",2,12,8)
    minimum=st.slider("Minimum Setup Score",0.,10.,6.,.5)
    setups=st.multiselect("Setup",["Spring Reversal","SOS Breakout","LPS Continuation","Trend Continuation","Test / Re-accumulation","Distribution Warning","Neutral"],
                          ["Spring Reversal","SOS Breakout","LPS Continuation","Trend Continuation","Test / Re-accumulation","Distribution Warning","Neutral"])
    aligned=st.checkbox("רק Daily + Weekly תומכים",False)
    run=st.button("🚀 MULTI-TIMEFRAME SCAN",type="primary",use_container_width=True)

symbols=list(dict.fromkeys(x.strip().upper() for x in raw.replace(","," ").split() if x.strip()))
if run or "res" not in st.session_state:
    bar=st.progress(0);rows=[]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fs={ex.submit(scan,s):s for s in symbols}
        for i,f in enumerate(as_completed(fs),1):
            x=f.result()
            if x:rows.append(x)
            bar.progress(i/max(1,len(fs)))
    bar.empty();st.session_state.res=pd.DataFrame(rows)

df=st.session_state.res
if df.empty:st.warning("אין תוצאות.");st.stop()
view=df[(df["Setup Score"]>=minimum)&df.Setup.isin(setups)].copy()
if aligned:
    view=view[((view.Weekly.isin(["Accumulation","Markup"]))&(view.Daily.isin(["Accumulation","Markup"])))]
view=view.sort_values(["Setup Score","Weekly Score","Daily Score"],ascending=False)

a,b,c,d=st.columns(4)
a.metric("נסרקו",len(df));b.metric("Setups",len(view));c.metric("ממוצע Setup",f"{df['Setup Score'].mean():.1f}");d.metric("Spring/SOS/LPS",int(df.Events.str.contains("Spring|SOS|LPS",regex=True).sum()))
st.subheader("🎯 Multi-Timeframe Results")
st.dataframe(view,use_container_width=True,hide_index=True)
st.download_button("⬇️ CSV",view.to_csv(index=False).encode(),"wyckoff_mtf.csv","text/csv")

st.subheader("🔬 Deep Dive")
if len(view):
    sym=st.selectbox("בחר מניה",view.Symbol.tolist())
    row=view[view.Symbol==sym].iloc[0]
    d=getdf(sym,"2y","1d")
    w=getdf(sym,"5y","1wk")
    de=engine(d);we=engine(w)
    x1,x2,x3,x4=st.columns(4)
    x1.metric("Setup",row.Setup);x2.metric("Setup Score",f"{row['Setup Score']:.1f}/10")
    x3.metric("Daily / Weekly",f"{de['phase']} / {we['phase']}");x4.metric("Events",", ".join(de["events"]) or "None")
    st.line_chart(d.Close)
    st.caption("ה-Setup הוא מודל היוריסטי המבוסס על OHLCV; הוא אינו קביעה ודאית של תבנית Wyckoff ואינו המלצת השקעה.")
