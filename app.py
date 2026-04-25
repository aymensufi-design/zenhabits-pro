import streamlit as st
import pandas as pd
import sqlite3
import base64
from datetime import date, datetime
import plotly.graph_objects as go
import plotly.express as px
import os
import random
import time

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect('zenhabits_pro_final_v29.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, pin TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS habits (user TEXT, date TEXT, task TEXT, status INT, reminder_time TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS tasks (user TEXT, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS notes (user TEXT, date TEXT, txt TEXT, sentiment FLOAT)')
conn.commit()

# ---------------- STYLING ----------------
st.set_page_config(page_title="ZenHabits Pro", layout="wide")

def get_base64(file):
    try:
        if os.path.exists(file):
            with open(file, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except: return None
    return None

logo_file = "zenhabitlogo.jpg"
bin_str = get_base64(logo_file)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap');
    .stApp { background-color: #002d2d; color: white; }
    section[data-testid="stSidebar"] { background-color: #001a1a !important; }
    .track-text { font-family: 'Dancing Script', cursive; color: #AD1457; font-size: 35px; text-align: center; margin-bottom: 20px; }
    .habit-card { background: #004d40; padding: 12px; border-radius: 8px; margin-bottom: 5px; border-left: 5px solid #AD1457; font-weight: bold; }
    .stButton>button { background-color: #AD1457 !important; color: white !important; border-radius: 20px; font-weight: bold; width: 100%; }
    .del-btn>button { background-color: #b71c1c !important; font-size: 10px !important; height: 25px !important; width: 60px !important; border-radius: 5px; }
    .mastery-header { background: linear-gradient(90deg, #004d40, #AD1457); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; }
    .quote-box { background: rgba(173, 20, 87, 0.2); border: 1px dashed #AD1457; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px; color: #ffeb3b; font-weight: bold; }
    .speed-text { font-size: 24px; font-weight: bold; text-align: center; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def get_sentiment(text):
    # Expanded list for better detection
    pos = ['good', 'happy', 'great', 'productive', 'achieved', 'calm', 'best', 'awesome', 'nice', 'cool', 'excellent', 'relaxed']
    neg = ['bad', 'sad', 'tired', 'failed', 'stress', 'lazy', 'worst', 'angry', 'slow', 'boring', 'depressed', 'anxious']
    words = text.lower().split()
    score = sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg)
    return float(score)

MOTIVATIONAL_QUOTES = ["Keep going! ✨", "Don't stop now! 💪", "Small steps everyday! 🚀", "Stay focused! 🎯"]

# ---------------- AUTH ----------------
def auth_page():
    if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="180"></p>', unsafe_allow_html=True)
    st.markdown('<div class="track-text">ZenHabits Pro</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        mode = st.radio("Mode", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
        email = st.text_input("Email")
        if mode == "Sign Up":
            name = st.text_input("Name")
            pin = st.text_input("PIN", type="password", max_chars=4)
            if st.button("Register"):
                c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (email, name, pin))
                conn.commit()
                st.success("Account Created!")
        else:
            pin = st.text_input("PIN", type="password", max_chars=4)
            if st.button("Login"):
                c.execute("SELECT name FROM users WHERE email=? AND pin=?", (email, pin))
                res = c.fetchone()
                if res:
                    st.session_state.logged_in, st.session_state.user, st.session_state.name = True, email, res[0]
                    st.rerun()
                else: st.error("Wrong details!")

# ---------------- DASHBOARD ----------------
def dashboard():
    u = st.session_state.user
    
    with st.sidebar:
        if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="100"></p>', unsafe_allow_html=True)
        st.title(f"Hi, {st.session_state.name}")
        st.markdown(f'<div class="quote-box">{random.choice(MOTIVATIONAL_QUOTES)}</div>', unsafe_allow_html=True)
        st.markdown("---")
        c.execute("SELECT DISTINCT name FROM tasks WHERE user=?", (u,))
        history = [t[0] for t in c.fetchall()]
        suggested = st.selectbox("Suggestions", [""] + history)
        nh = st.text_input("Add Task")
        tm = st.time_input("Time", datetime.now().time())
        if st.button("Add Task"):
            t_name = nh if nh else suggested
            if t_name:
                c.execute("INSERT OR IGNORE INTO tasks VALUES (?,?)", (u, t_name))
                c.execute("INSERT INTO habits VALUES (?,?,?,?,?)", (u, str(date.today()), t_name, 0, str(tm)))
                conn.commit()
                st.rerun()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    df_all = pd.read_sql_query("SELECT * FROM habits WHERE user=?", conn, params=(u,))
    mastery = round((df_all['status'].sum() / len(df_all) * 100), 1) if not df_all.empty else 0.0
    st.markdown(f'<div class="mastery-header"><h1>{mastery}% Mastery Score</h1></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1.3, 1])
    
    with col_l:
        target_date = st.date_input("Select Date", date.today())
        search = st.text_input("🔍 Search...").lower()
        c.execute("SELECT rowid, task, status, reminder_time FROM habits WHERE user=? AND date=?", (u, str(target_date)))
        day_tasks = c.fetchall()
        
        updates = {}
        if day_tasks:
            reward_area = st.empty()
            for i, (rid, t_name, t_stat, t_time) in enumerate(day_tasks, 1):
                if search in t_name.lower():
                    ca, cb, cc = st.columns([0.1, 0.7, 0.2])
                    with ca: 
                        check = st.checkbox("", value=bool(t_stat), key=f"tk_{rid}_{target_date}")
                        updates[rid] = check
                        if check and not t_stat:
                            st.balloons()
                            reward_area.success("Congratulations 🎉 Take your reward with timer, you deserve this 🤗 enjoy")
                            c.execute("UPDATE habits SET status=1 WHERE rowid=?", (rid,))
                            conn.commit()
                            time.sleep(5)
                            reward_area.empty()
                            st.rerun()
                    with cb: st.markdown(f'<div class="habit-card">{i}. {t_name} (⏰ {t_time})</div>', unsafe_allow_html=True)
                    with cc:
                        if st.button("Del", key=f"del_{rid}"):
                            c.execute("DELETE FROM habits WHERE rowid=?", (rid,))
                            conn.commit()
                            st.rerun()
            
            c.execute("SELECT txt FROM notes WHERE user=? AND date=?", (u, str(target_date)))
            note_res = c.fetchone()
            u_note = st.text_area("📝 Mood Journal", value=note_res[0] if note_res else "", height=100)
            if st.button("💾 Save Progress & Mood"):
                for rid, s in updates.items():
                    c.execute("UPDATE habits SET status=? WHERE rowid=?", (int(s), rid))
                score = get_sentiment(u_note)
                c.execute("DELETE FROM notes WHERE user=? AND date=?", (u, str(target_date)))
                c.execute("INSERT INTO notes VALUES (?,?,?,?)", (u, str(target_date), u_note, score))
                conn.commit()
                st.rerun()
        else: st.info("No tasks for this date.")

    with col_r:
        if day_tasks:
            done = sum(1 for x in day_tasks if x[2] == 1)
            total = len(day_tasks)
            perc = int(done/total*100)
            
            speed_status = "Improve Speed 🐢"
            speed_color = "#b71c1c"
            if perc >= 80: 
                speed_status = "Excellent ⚡"
                speed_color = "#00c853"
            elif perc >= 50: 
                speed_status = "Good 👍"
                speed_color = "#ffeb3b"
            
            st.markdown(f'<div class="speed-text" style="color:{speed_color};">{speed_status} ({perc}%)</div>', unsafe_allow_html=True)
            
            fig_pie = go.Figure(go.Pie(values=[done, total-done], hole=0.7, marker=dict(colors=[speed_color, "#001a1a"])))
            fig_pie.update_layout(showlegend=False, height=220, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

        if not df_all.empty:
            st.subheader("Weekly Trend")
            df_line = df_all.copy()
            df_line['date'] = pd.to_datetime(df_line['date'])
            trend = df_line.groupby('date')['status'].sum().reset_index().sort_values('date')
            fig_line = px.line(trend, x='date', y='status', markers=True)
            fig_line.update_traces(line_color='#AD1457')
            fig_line.update_layout(height=180, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_line, use_container_width=True)

        # MOOD ANALYTICS RE-FIXED
        st.subheader("Mood Analytics")
        df_mood = pd.read_sql_query("SELECT date, sentiment FROM notes WHERE user=?", conn, params=(u,))
        if not df_mood.empty:
            df_mood['date'] = pd.to_datetime(df_mood['date'])
            df_mood = df_mood.sort_values('date')
            # Using Plotly Bar for clear sentiment representation
            fig_mood = px.bar(df_mood, x='date', y='sentiment', color='sentiment', 
                              color_continuous_scale=['red', 'yellow', 'green'],
                              labels={'sentiment': 'Mood Score'})
            fig_mood.update_layout(height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                   showlegend=False, font_color="white", margin=dict(t=10,b=10))
            st.plotly_chart(fig_mood, use_container_width=True)
        else:
            st.info("Write something in your journal and Save to see Mood Analytics!")

if st.session_state.logged_in: dashboard()
else: auth_page()