import streamlit as st
import pandas as pd
import sqlite3
import base64
from datetime import date, datetime
import plotly.graph_objects as go
import plotly.express as px
import os
import time

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect('zenhabits_pro_final_v29.db', check_same_thread=False, timeout=20)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, pin TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS habits (user TEXT, date TEXT, task TEXT, status INT, reminder_time TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS notes (user TEXT, date TEXT, txt TEXT, sentiment FLOAT)')
conn.commit()

# ---------------- STYLING ----------------
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
    .stButton>button { 
        background: linear-gradient(45deg, #AD1457, #F06292) !important; 
        color: white !important; border-radius: 25px !important; border: none !important; font-weight: 600 !important; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = ""

def get_sentiment(text):
    pos = ['good', 'happy', 'great', 'productive', 'achieved', 'calm', 'best', 'awesome', 'nice']
    neg = ['bad', 'sad', 'tired', 'failed', 'stress', 'lazy', 'worst', 'angry', 'slow']
    words = text.lower().split()
    return float(sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg))

# ---------------- DASHBOARD ----------------
def dashboard():
    u = st.session_state.user
    with st.sidebar:
        if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="100"></p>', unsafe_allow_html=True)
        st.title(f"Hi, {st.session_state.name}")
        st.markdown("---")
        show_reminders = st.toggle("Enable Reminder", value=True)
        tm = st.time_input("Set Time", datetime.now().time())
        nh = st.text_input("New Task")
        if st.button("Add Task"):
            if nh:
                rem_time = str(tm) if show_reminders else "Off"
                c.execute("INSERT INTO habits (user, date, task, status, reminder_time) VALUES (?,?,?,?,?)", (u, str(date.today()), nh, 0, rem_time))
                conn.commit(); st.rerun()
        if st.button("Logout"):
            st.session_state.logged_in = False; st.rerun()

    # Mastery Header
    df_all = pd.read_sql_query("SELECT * FROM habits WHERE user=?", conn, params=(u,))
    mastery = round((df_all['status'].sum() / len(df_all) * 100), 1) if not df_all.empty else 0.0
    st.markdown(f'<div class="mastery-header"><h1>{mastery}% Mastery Score</h1></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        target_date = st.date_input("Select Date", date.today())
        c.execute("SELECT rowid, task, status, reminder_time FROM habits WHERE user=? AND date=?", (u, str(target_date)))
        day_tasks = c.fetchall()

        reward_area = st.empty()
        if day_tasks:
            for rid, t_name, t_stat, t_time in day_tasks:
                ca, cb, cc = st.columns([0.1, 0.7, 0.2])
                with ca:
                    check = st.checkbox("", value=bool(t_stat), key=f"tk_{rid}")
                with cb:
                    st.markdown(f'<div class="habit-card">{t_name} (⏰ {t_time})</div>', unsafe_allow_html=True)
                with cc:
                    if st.button("Del", key=f"del_{rid}"):
                        c.execute("DELETE FROM habits WHERE rowid=?", (rid,))
                        conn.commit(); st.rerun()

                if check and not t_stat:
                    st.balloons(); reward_area.success("Congratulations 🎉 Take your reward with timer, you deserve this 🤗 enjoy")
                    c.execute("UPDATE habits SET status=1 WHERE rowid=?", (rid,))
                    conn.commit(); time.sleep(8); reward_area.empty(); st.rerun()
                elif not check and t_stat:
                    c.execute("UPDATE habits SET status=0 WHERE rowid=?", (rid,))
                    conn.commit(); st.rerun()
        
        st.markdown("---")
        st.subheader("📝 Mood Journal")
        c.execute("SELECT txt FROM notes WHERE user=? AND date=?", (u, str(target_date)))
        note_res = c.fetchone()
        u_note = st.text_area("How's the day?", value=note_res[0] if note_res else "", height=100)
        if st.button("💾 Save Progress"):
            score = get_sentiment(u_note)
            c.execute("INSERT OR REPLACE INTO notes (user, date, txt, sentiment) VALUES (?,?,?,?)", (u, str(target_date), u_note, score))
            conn.commit(); st.rerun()

    with col_r:
        # 1. PIE CHART (SPEEDOMETER)
        st.subheader("🎯 Today's Speed")
        if day_tasks:
            done = sum(1 for x in day_tasks if x[2] == 1)
            total = len(day_tasks)
            perc = int(done/total*100) if total > 0 else 0
            sc = "#b71c1c" if perc < 50 else ("#ffeb3b" if perc < 80 else "#00c853")
            st.markdown(f'<h3 style="text-align:center; color:{sc};">Speed: {perc}% Done</h3>', unsafe_allow_html=True)
            fig_pie = go.Figure(go.Pie(values=[done, total-done], hole=0.7, marker=dict(colors=[sc, "#001a1a"])))
            fig_pie.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Add tasks to track speed.")

        # 2. LINE GRAPH (PROGRESS)
        st.markdown("---")
        st.subheader("📈 Progress Trend")
        df_prog = pd.read_sql_query("SELECT date, SUM(status) as done FROM habits WHERE user=? GROUP BY date ORDER BY date ASC", conn, params=(u,))
        if not df_prog.empty:
            fig_line = px.line(df_prog, x='date', y='done', markers=True)
            fig_line.update_traces(line_color='#AD1457')
            fig_line.update_layout(height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_line, use_container_width=True)

        # 3. BAR GRAPH (MOOD)
        st.markdown("---")
        st.subheader("📊 Mood Analysis")
        df_mood = pd.read_sql_query("SELECT date, sentiment FROM notes WHERE user=? ORDER BY date ASC", conn, params=(u,))
        if not df_mood.empty:
            df_mood['date_label'] = pd.to_datetime(df_mood['date']).dt.strftime('%d %b')
            fig_bar = px.bar(df_mood, x='date_label', y='sentiment', color='sentiment', color_continuous_scale=['#F06292', '#AD1457'])
            fig_bar.update_layout(height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

# ---------------- AUTH ----------------
def auth():
    st.markdown('<div class="track-text">ZenHabits Pro</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        m = st.radio("Mode", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
        e = st.text_input("Email")
        p = st.text_input("PIN", type="password")
        if m == "Sign Up":
            n = st.text_input("Name")
            if st.button("Create"):
                c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (e, n, p))
                conn.commit(); st.success("Created!")
        elif st.button("Login"):
            c.execute("SELECT name FROM users WHERE email=? AND pin=?", (e, p))
            res = c.fetchone()
            if res:
                st.session_state.logged_in, st.session_state.user, st.session_state.name = True, e, res[0]
                st.rerun()

if st.session_state.logged_in: dashboard()
else: auth()