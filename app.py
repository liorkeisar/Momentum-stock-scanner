import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🏹 Test Scanner - Static Data")

# יצירת נתונים ידניים ללא קריאה חיצונית
data = [
    {"Ticker": "NVDA", "Price": 214.25, "Change %": 1.5},
    {"Ticker": "AMD", "Price": 150.10, "Change %": -0.5},
    {"Ticker": "PLTR", "Price": 25.40, "Change %": 2.2}
]

st.write("מציג נתונים מהזיכרון הפנימי:")

# הצגת טבלה
df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)

st.success("אם אתה רואה את הטבלה הזו, האפליקציה תקינה והבעיה היא בחיבור לבורסה.")
