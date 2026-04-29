import streamlit as st
import pandas as pd
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
from datetime import date, datetime
import plotly.graph_objects as go
import plotly.express as px
import os
import random
import time

# ---------------- GOOGLE SHEETS SETUP ----------------
def connect_to_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gspread" in st.secrets:
            creds_dict = st.secrets["gspread"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key("1d8DAXQ38iRKMTVcGwwue1zg-CGIerP-DPdtINj8YNrU").sheet1
            return sheet
        return None
    except: return None

def sync_to_sheets(date_str, task, status, mood_score):
    sheet = connect_to_gsheet()
    if sheet:
        try: sheet.append_row([str(date_str), task, int(status), float(mood_score)])
        except: pass

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect('zenhabits_pro_final_v29.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, pin TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS habits (user TEXT, date TEXT, task TEXT, status INT, reminder_time TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS tasks (user TEXT, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS notes (user TEXT, date TEXT, txt TEXT, sentiment FLOAT)')
conn.commit()

# ---------------- STYLING (PINK GRADIENT) ----------------
st.set_page_config(page_title="ZenHabits Pro", layout="wide")

def get_base64(file):
    try:
        if os.path.exists(file):
            with open(file, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None
    return None

logo_file = "zenhabitlogo.jpg"
bin_str = get_base64(logo_file)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&family=Dancing+Script:wght@700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background-color: #002d2d; color: white; }
    .track-text { font-family: 'Dancing Script', cursive; color: #AD1457 !important; font-size: 55px; text-align: center; }
    .habit-card { background: #004d40; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-left: 6px solid #AD1457; }
    .mastery-header { background: linear-gradient(135deg, #004d40 0%, #AD1457 100%); padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 30px; }
    .speed-text { font-weight: bold; font-size: 24px; text-align: center; }
    .stButton>button { 
        background: linear-gradient(45deg, #AD1457, #F06292) !important; 
        color: white !important; border-radius: 25px !important; border: none !important; font-weight: 600 !important; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- INITIALIZATION ----------------
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = ""
if 'name' not in st.session_state: st.session_state.name = ""

def get_sentiment(text):
    pos = ['good', 'happy', 'great', 'productive', 'achieved', 'calm', 'best', 'awesome', 'nice']
    neg = ['bad', 'sad', 'tired', 'failed', 'stress', 'lazy', 'worst', 'angry', 'slow']
    words = text.lower().split()
    return float(sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg))

# ---------------- AUTH PAGE ----------------
def auth_page():
    if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="150"></p>', unsafe_allow_html=True)
    st.markdown('<div class="track-text">ZenHabits Pro</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        mode = st.radio("Choose", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
        email = st.text_input("Email")
        if mode == "Sign Up":
            name = st.text_input("Full Name")
            pin = st.text_input("4-Digit PIN", type="password", max_chars=4)
            if st.button("Register"):
                c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (email, name, pin))
                conn.commit(); st.success("Registered! Now Login.")
        else:
            pin = st.text_input("PIN", type="password", max_chars=4)
            if st.button("Login"):
                c.execute("SELECT name FROM users WHERE email=? AND pin=?", (email, pin))
                res = c.fetchone()
                if res:
                    st.session_state.logged_in, st.session_state.user, st.session_state.name = True, email, res[0]
                    st.rerun()
                else: st.error("Wrong PIN!")

# ---------------- DASHBOARD ----------------
def dashboard():
    u = st.session_state.user
    with st.sidebar:
        if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="100"></p>', unsafe_allow_html=True)
        st.title(f"Hi, {st.session_state.name}")
        st.markdown("---")
        st.subheader("⏲️ Reminder Settings")
        show_reminders = st.toggle("Enable Reminder", value=True)
        tm = st.time_input("Set Time", datetime.now().time())
        st.markdown("---")
        c.execute("SELECT DISTINCT name FROM tasks WHERE user=?", (u,))
        history = [t[0] for t in c.fetchall()]
        suggested = st.selectbox("Suggestions", [""] + history)
        nh = st.text_input("New Task")
        if st.button("Add Task"):
            t_name = nh if nh else suggested
            if t_name:
                rem_time = str(tm) if show_reminders else "Off"
                c.execute("INSERT INTO habits VALUES (?,?,?,?,?)", (u, str(date.today()), t_name, 0, rem_time))
                conn.commit(); st.rerun()
        if st.button("Logout"):
            st.session_state.logged_in = False; st.rerun()

    df_all = pd.read_sql_query("SELECT * FROM habits WHERE user=?", conn, params=(u,))
    mastery = round((df_all['status'].sum() / len(df_all) * 100), 1) if not df_all.empty else 0.0
    st.markdown(f'<div class="mastery-header"><h1>{mastery}% Mastery Score</h1></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        target_date = st.date_input("Select Date", date.today())
        c.execute("SELECT rowid, task, status, reminder_time FROM habits WHERE user=? AND date=?", (u, str(target_date)))
        day_tasks = c.fetchall()

        if day_tasks:
            reward_area = st.empty()
            for i, (rid, t_name, t_stat, t_time) in enumerate(day_tasks, 1):
                ca, cb, cc = st.columns([0.1, 0.7, 0.2])
                with ca:
                    check = st.checkbox("", value=bool(t_stat), key=f"tk_{rid}")
                with cb:
                    time_disp = f"(⏰ {t_time})" if t_time != "Off" else ""
                    st.markdown(f'<div class="habit-card">{t_name} {time_disp}</div>', unsafe_allow_html=True)
                with cc:
                    if st.button("Del", key=f"del_{rid}"):
                        c.execute("DELETE FROM habits WHERE rowid=?", (rid,))
                        conn.commit(); st.rerun()

                if check and not t_stat:
                    st.balloons()
                    reward_area.success("Congratulations 🎉 Take your reward with timer, you deserve this 🤗 enjoy")
                    c.execute("UPDATE habits SET status=1 WHERE rowid=?", (rid,))
                    conn.commit(); sync_to_sheets(target_date, t_name, 1, 0)
                    time.sleep(8)
                    reward_area.empty(); st.rerun()
                elif not check and t_stat:
                    c.execute("UPDATE habits SET status=0 WHERE rowid=?", (rid,))
                    conn.commit(); st.rerun()
            
            # --- MOOD JOURNAL (FIXED & VISIBLE) ---
            st.markdown("---")
            st.subheader("📝 Daily Mood Journal")
            c.execute("SELECT txt FROM notes WHERE user=? AND date=?", (u, str(target_date)))
            note_res = c.fetchone()
            u_note = st.text_area("How was your day?", value=note_res[0] if note_res else "", height=150)
            if st.button("💾 Save Progress & Mood"):
                score = get_sentiment(u_note)
                c.execute("DELETE FROM notes WHERE user=? AND date=?", (u, str(target_date)))
                c.execute("INSERT INTO notes VALUES (?,?,?,?)", (u, str(target_date), u_note, score))
                conn.commit(); sync_to_sheets(target_date, "Journal Entry", 1, score)
                st.success("Mood Saved Successfully! ✅"); time.sleep(1); st.rerun()
        else: st.info("No tasks for today.")

    with col_r:
        if day_tasks:
            done = sum(1 for x in day_tasks if x[2] == 1)
            total = len(day_tasks)
            perc = int(done/total*100) if total > 0 else 0
            sc = "#b71c1c" if perc < 50 else ("#ffeb3b" if perc < 80 else "#00c853")
            st.markdown(f'<div class="speed-text" style="color:{sc};">Speed: {perc}% Done</div>', unsafe_allow_html=True)
            fig = go.Figure(go.Pie(values=[done, total-done], hole=0.7, marker=dict(colors=[sc, "#001a1a"])))
            fig.update_layout(showlegend=False, height=250, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        # --- MOOD TREND GRAPH ---
        st.subheader("Weekly Mood Trend")
        df_mood = pd.read_sql_query("SELECT date, sentiment FROM notes WHERE user=? ORDER BY date ASC", conn, params=(u,))
        if not df_mood.empty:
            df_mood['date'] = pd.to_datetime(df_mood['date'])
            fig_mood = px.line(df_mood, x='date', y='sentiment', markers=True, template="plotly_dark")
            fig_mood.update_traces(line_color='#AD1457', marker=dict(size=10))
            fig_mood.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mood, use_container_width=True)

# ---------------- RUN ----------------
if st.session_state.logged_in: dashboard()
else: auth_page()