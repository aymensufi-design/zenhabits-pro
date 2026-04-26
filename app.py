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
    .mastery-header { background: linear-gradient(90deg, #004d40, #AD1457); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; }
    .quote-box { background: rgba(173, 20, 87, 0.2); border: 1px dashed #AD1457; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px; color: #ffeb3b; font-weight: bold; }
    .speed-text { font-size: 26px; font-weight: bold; text-align: center; margin-top: 10px; padding: 10px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def get_sentiment(text):
    pos = ['good', 'happy', 'great', 'productive', 'achieved', 'calm', 'best', 'awesome', 'nice', 'cool', 'excellent', 'relaxed']
    neg = ['bad', 'sad', 'tired', 'failed', 'stress', 'lazy', 'worst', 'angry', 'slow', 'boring', 'depressed', 'anxious']
    words = text.lower().split()
    score = sum(1 for w in words if w in pos) - sum(1 for w in words if w in neg)
    return float(score)

MOTIVATIONAL_QUOTES = ["Keep going! ✨", "Don't stop now! 💪", "Small steps everyday! 🚀", "Stay focused! 🎯"]

# ---------------- DASHBOARD ----------------
def dashboard():
    u = st.session_state.user
    
    with st.sidebar:
        if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="100"></p>', unsafe_allow_html=True)
        st.title(f"Hi, {st.session_state.name}")
        target_date = st.date_input("Select Working Date", date.today())
        st.markdown(f'<div class="quote-box">{random.choice(MOTIVATIONAL_QUOTES)}</div>', unsafe_allow_html=True)
        st.markdown("---")
        
        c.execute("SELECT DISTINCT name FROM tasks WHERE user=?", (u,))
        history = [t[0] for t in c.fetchall()]
        suggested = st.selectbox("Suggestions", [""] + history)
        nh = st.text_input("Add Task Name")
        
        use_reminder = st.checkbox("Set Reminder?", value=False)
        tm = "None"
        if use_reminder:
            tm = str(st.time_input("Time", datetime.now().time()))
            
        if st.button("Add Task"):
            t_name = nh if nh else suggested
            if t_name:
                c.execute("INSERT OR IGNORE INTO tasks VALUES (?,?)", (u, t_name))
                c.execute("INSERT INTO habits VALUES (?,?,?,?,?)", (u, str(target_date), t_name, 0, tm))
                conn.commit()
                st.rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    df_all = pd.read_sql_query("SELECT * FROM habits WHERE user=?", conn, params=(u,))
    mastery = round((df_all['status'].sum() / len(df_all) * 100), 1) if not df_all.empty else 0.0
    st.markdown(f'<div class="mastery-header"><h1>{mastery}% Total Mastery Score</h1></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1.3, 1])
    
    with col_l:
        st.subheader(f"Tasks for {target_date}")
        search_query = st.text_input("🔍 Search tasks...", placeholder="Search here...").lower()
        
        c.execute("SELECT rowid, task, status, reminder_time FROM habits WHERE user=? AND date=?", (u, str(target_date)))
        day_tasks = c.fetchall()
        filtered_tasks = [t for t in day_tasks if search_query in t[1].lower()]
        
        updates = {}
        if filtered_tasks:
            reward_area = st.empty()
            for i, (rid, t_name, t_stat, t_time) in enumerate(filtered_tasks, 1):
                ca, cb, cc = st.columns([0.1, 0.7, 0.2])
                with ca: 
                    check = st.checkbox("", value=bool(t_stat), key=f"tk_{rid}_{target_date}")
                    updates[rid] = check
                    if check and not t_stat:
                        reward_area.success("Congratulations 🎉 Take your reward with timer, you deserve this 🤗 enjoy")
                        st.balloons()
                        c.execute("UPDATE habits SET status=1 WHERE rowid=?", (rid,))
                        conn.commit()
                        time.sleep(3)
                        reward_area.empty()
                        st.rerun()
                with cb: 
                    display_time = f" (⏰ {t_time})" if t_time != "None" else ""
                    st.markdown(f'<div class="habit-card">{i}. {t_name}{display_time}</div>', unsafe_allow_html=True)
                with cc:
                    if st.button("Del", key=f"del_{rid}_{target_date}"):
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
                msg = st.success("Data Saved Successfully! ✅")
                time.sleep(3)
                msg.empty()
                st.rerun()
        else:
            st.info(f"No tasks found for {target_date}.")

    with col_r:
        if day_tasks:
            done = sum(1 for x in day_tasks if x[2] == 1)
            total = len(day_tasks)
            perc = int(done/total*100) if total > 0 else 0
            
            speed_status = "Improve Speed 🐢"
            speed_color = "#b71c1c"
            if perc >= 80: speed_status, speed_color = "Excellent ⚡", "#00c853"
            elif perc >= 50: speed_status, speed_color = "Good 👍", "#ffeb3b"
            
            st.markdown(f'<div class="speed-text" style="background-color:{speed_color}33; color:{speed_color}; border: 2px solid {speed_color};">{speed_status} ({perc}%)</div>', unsafe_allow_html=True)
            fig_pie = go.Figure(go.Pie(values=[done, total-done], hole=0.7, marker=dict(colors=[speed_color, "#001a1a"])))
            fig_pie.update_layout(showlegend=False, height=220, margin=dict(t=10,b=10), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- LINE GRAPH (WEEKLY TREND) RE-ADDED ---
        if not df_all.empty:
            st.subheader("Weekly Trend")
            df_line = df_all.copy()
            df_line['date'] = pd.to_datetime(df_line['date'])
            trend = df_line.groupby('date')['status'].sum().reset_index().sort_values('date')
            fig_line = px.line(trend, x='date', y='status', markers=True)
            fig_line.update_traces(line_color='#AD1457')
            fig_line.update_layout(height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", margin=dict(t=10,b=10))
            st.plotly_chart(fig_line, use_container_width=True)

        # MOOD BAR CHART
        st.subheader("Mood History")
        df_mood = pd.read_sql_query("SELECT date, sentiment FROM notes WHERE user=?", conn, params=(u,))
        if not df_mood.empty:
            df_mood['date'] = pd.to_datetime(df_mood['date'])
            df_mood = df_mood.sort_values('date')
            fig_mood = px.bar(df_mood, x='date', y='sentiment', color='sentiment', color_continuous_scale=['red', 'yellow', 'green'])
            fig_mood.update_layout(height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", margin=dict(t=10,b=10))
            st.plotly_chart(fig_mood, use_container_width=True)

# ---------------- AUTH ----------------
def auth_page():
    if bin_str: st.markdown(f'<p align="center"><img src="data:image/jpeg;base64,{bin_str}" width="180"></p>', unsafe_allow_html=True)
    st.markdown('<div class="track-text">ZenHabits Pro</div>', unsafe_allow_html=True)
    mode = st.tabs(["Login", "Sign Up"])
    with mode[0]:
        e = st.text_input("Email", key="l_e")
        p = st.text_input("PIN", type="password", key="l_p")
        if st.button("Login"):
            c.execute("SELECT name FROM users WHERE email=? AND pin=?", (e, p))
            res = c.fetchone()
            if res:
                st.session_state.logged_in, st.session_state.user, st.session_state.name = True, e, res[0]
                st.rerun()
            else: st.error("Wrong details")
    with mode[1]:
        ne, nn, np = st.text_input("Email", key="s_e"), st.text_input("Name"), st.text_input("PIN", type="password")
        if st.button("Register"):
            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (ne, nn, np))
            conn.commit()
            st.success("Success! Login now.")

if st.session_state.logged_in: dashboard()
else: auth_page()