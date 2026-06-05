st.markdown("""
    <style>
    /* רקע אפליקציה */
    .stApp { background-color: #0A0712; color: #E6E1F3; font-family: -apple-system, sans-serif; }
    
    /* קונטיינר מניה - המסגרת הכהה */
    .stock-container { 
        background: #0B0E14; 
        border: 1px solid #1F2433; 
        border-radius: 16px; 
        padding: 20px; 
        margin-bottom: 20px; 
    }
    
    /* פאנל מידע שמאלי */
    .info-panel { 
        background: #111522; 
        border: 1px solid #1F2538; 
        border-radius: 12px; 
        padding: 15px; 
        height: 100%; 
    }
    
    /* כותרת טיקר */
    .ticker-symbol { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }
    
    /* Badge מעוגל */
    .badge { 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 0.75rem; 
        font-weight: 600; 
        display: inline-block; 
        margin-top: 8px; 
    }
    .badge-reversal { background-color: rgba(0, 184, 135, 0.15); color: #00B887; }
    
    /* תיבת אינדיקטורים */
    .indicator-box { margin-top: 15px; padding-top: 10px; border-top: 1px solid #1F2538; }
    .indicator-name { color: #938AA9; font-size: 0.8rem; }
    .indicator-desc { color: #5C5374; font-size: 0.7rem; display: block; margin-top: 2px; }
    </style>
""", unsafe_allow_html=True)
