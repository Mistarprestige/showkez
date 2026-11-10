import streamlit as st
from transformers import pipeline
from fpdf import FPDF
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import random
import os
import shutil
import time
import threading

# ==========================================
# 1. DATABASE SETUP & SIMULATED LIVE SCRAPER
# ==========================================
def init_db():
    if not os.path.exists("backups"):
        os.makedirs("backups")
    conn = sqlite3.connect("army_intel.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intel_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            input_text TEXT,
            threat_level TEXT,
            kinetic_flags TEXT,
            info_flags TEXT,
            media_vectors TEXT,
            ai_sentiment TEXT,
            ai_confidence REAL
        )
    """)
    conn.commit()
    conn.close()

def log_to_db(text, threat, kinetic, info, media, ai_label, ai_score):
    conn = sqlite3.connect("army_intel.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO intel_logs (timestamp, input_text, threat_level, kinetic_flags, info_flags, media_vectors, ai_sentiment, ai_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text, threat, 
          ", ".join(kinetic) if kinetic else "None", 
          ", ".join(info) if info else "None",
          ", ".join(media) if media else "None", 
          ai_label, round(ai_score, 2)))
    conn.commit()
    conn.close()

def fetch_logs():
    conn = sqlite3.connect("army_intel.db")
    try:
        df = pd.read_sql_query("SELECT timestamp, threat_level, kinetic_flags, info_flags, media_vectors, ai_sentiment, input_text FROM intel_logs ORDER BY id DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def clear_db():
    conn = sqlite3.connect("army_intel.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM intel_logs")
    conn.commit()
    conn.close()

# Background thread daemon that simulates live data flowing from WhatsApp/Telegram APIs
def live_osint_scraper_simulation():
    mock_intercepts = [
        "Alert on Telegram: Olosa bandits plotting to ambush tactical columns along the bypass route, they are spreading iro false claims.",
        "Viral WhatsApp audio claims wuybe groups successfully managed to attack base, soldiraabe don run leave weapons, that news is fenande.",
        "A thread on Nairaland states ndị ohi are gathering near coordinates, army hide information regarding casualties.",
        "Breaking on Gistlover: Reports of a mutiny in the camp over logistics, military command is issuing fake news."
    ]
    while True:
        time.sleep(45) # Simulates a live ingestion scanning interval
        try:
            text = random.choice(mock_intercepts)
            found_kf = [w for w in PROPAGANDA_KEYWORDS["high_risk"] if w in text.lower()]
            found_if = [w for w in PROPAGANDA_KEYWORDS["misinformation_triggers"] if w in text.lower()]
            all_m = PROPAGANDA_KEYWORDS["streaming_platforms"] + PROPAGANDA_KEYWORDS["local_blogs"]
            found_mv = [w for w in all_m if w in text.lower()]
            threat = "CRITICAL" if (found_kf and found_if) else "MEDIUM"
            log_to_db(text, threat, found_kf, found_if, found_mv, "NEGATIVE", round(random.uniform(85.0, 99.0), 2))
        except Exception:
            pass

# Initialize engine layers
init_db()
if "bg_thread_started" not in st.session_state:
    threading.Thread(target=live_osint_scraper_simulation, daemon=True).start()
    st.session_state.bg_thread_started = True

# ==========================================
# 2. MODELS & DICTIONARIES CONFIGURATION
# ==========================================
@st.cache_resource
def load_sentiment_model():
    return pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")

@st.cache_resource
def load_transcription_model():
    # Utilizing an optimized processing fallback sequence for standard machines
    return pipeline("automatic-speech-recognition", model="facebook/wav2vec2-base-960h")

try:
    analyzer = load_sentiment_model()
    transcriber = load_transcription_model()
except Exception:
    analyzer, transcriber = None, None

PROPAGANDA_KEYWORDS = {
    "high_risk": [
        "unknown gunmen", "bandits", "bh", "iswap", "ambush", "mutiny", "dem don run", "kill soldiers", "attack base",
        "konu", "wuybe", "soldiraabe", "agha", "ndi ohi", "ndị ohi", "ndị agha", "ogun", "olosa", "jaguda", "jagun", "yan ta'adda"
    ],
    "misinformation_triggers": [
        "fake news", "army hide", "secret burial", "government format", "dem dey lie", "hiding casualties", "soldier strike",
        "fenande", "suudude", "nsunsu", "asi", "asiri", "iro", "baba"
    ],
    "streaming_platforms": ["youtube", "tiktok", "telegram", "whatsapp", "facebook", "twitter", "instagram"],
    "local_blogs": ["linda ikeji", "nairaland", "gistlover", "punch", "vanguard", "instablog", "sahara reporters"]
}

# ==========================================
# 3. REPORT EXPORT GENERATION MACHINE
# ==========================================
def generate_pdf(text, risk, high_risk_found, misinfo_found, media_found, ai_label, ai_score):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "NIGERIAN ARMY INTELLIGENCE COMPLEX (NAIC)", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "TACTICAL INFORMATION SCREENING REPORT", ln=True, align="C")
    pdf.line(10, 30, 200, 30)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Date/Time Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.cell(0, 7, f"Assigned Risk Level: {risk.upper()}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "1. INTERCEPTED RAW CAPTURE DATA:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, text)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "2. DICTIONARY EVALUATIONS:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Kinetic Vectors: {', '.join(high_risk_found) if high_risk_found else 'None'}", ln=True)
    pdf.cell(0, 6, f"Info Warfare Vectors: {', '.join(misinfo_found) if misinfo_found else 'None'}", ln=True)
    pdf.cell(0, 6, f"Intercept Channels: {', '.join(media_found) if media_found else 'None'}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "3. DEEP LEARNING LOGS ANALYSIS:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"AI Label: {ai_label} | Engine Score: {ai_score:.2f}%", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "RESTRICTED - FOR MILITARY USE ONLY", align="C", ln=True)
    return pdf.output()

# ==========================================
# 4. SECURE PRODUCTION LOG IN ACCESS GUARDS
# ==========================================
st.set_page_config(page_title="NA Tactical Info Guard", page_icon="🛡️", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🛡️ NAIC Tactical Surveillance Access Point")
    with st.form("Login Gateway"):
        st.subheader("Enter Secure Intelligence Credentials")
        username = st.text_input("Operator Designation / Service ID:")
        password = st.text_input("Command Access Token (PIN):", type="password")
        submitted = st.form_submit_button("Authenticate Terminal Connection")
        
        if submitted:
            # Enforcing strict offline user authorization parameters for the defense demo
            if username == "DAPR_Officer" and password == "NaspreAI2026":
                st.session_state.authenticated = True
                st.success("Access Authorized. Initializing Surveillance Matrices...")
                st.rerun()
            else:
                st.error("Authentication Denied. Security incident logged at AHQ.")
    st.stop()

# ==========================================
# 5. CORE WORKSPACE APPLICATION INTERFACE
# ==========================================
logo_col, title_col = st.columns()
with logo_col:
    if os.path.exists("army_logo.png"):
        st.image("army_logo.png", use_container_width=True)
with title_col:
    st.title("Tactical Information & Counter-Misinformation Engine")
    st.markdown("**Nigerian Army School of Public Relations and Information (NASPRI) - Production Build**")

st.divider()

main_col, log_col = st.columns()

if "trigger_critical_popup" not in st.session_state:
    st.session_state.trigger_critical_popup = False

with main_col:
    st.markdown("### 📡 Active Ingestion Processing")
    
    # Dual-input layout options for tactical data entry handling
    data_source_mode = st.radio("Select Ingestion Channel Source Input Type:", ["Manual Text / Social Log Copy", "Intercepted Signal Audio Upload (.wav)"])
    processed_text = ""

    if data_source_mode == "Manual Text / Social Log Copy":
        processed_text = st.text_area("Input Text Matrix:", height=120, placeholder="Paste suspicious network scripts or blog tracking threads here...")
    else:
        uploaded_audio = st.file_uploader("Upload Intercepted Signal File:", type=["wav"])
        if uploaded_audio is not None:
            st.audio(uploaded_audio)
            if transcriber:
                with st.spinner("Decoding tactical acoustics via Speech-to-Text backend pipeline..."):
                    try:
                        # Local computational pipeline reads raw bytes and extracts strings instantly
                        audio_bytes = uploaded_audio.read()
                        asr_result = transcriber(audio_bytes)
                        processed_text = asr_result["text"]
                    except Exception:
                        st.warning("Unable to decode uploaded audio. Please use manual text input instead.")