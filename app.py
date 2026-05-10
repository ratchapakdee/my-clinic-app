import streamlit as st
import pandas as pd
from datetime import datetime, time
import plotly.express as px
from streamlit_calendar import calendar
import os

# --- การตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="ระบบจองคิวรักษาออนไลน์", layout="wide")
DATA_FILE = 'bookings.csv'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # แก้ไขข้อมูลเก่า: แปลงวันที่ให้เป็นรูปแบบ YYYY-MM-DD เท่านั้น (ตัดเวลา 00:00:00 ออก)
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            # ตัดช่องว่างเผื่อมีค้างในชื่อหมอหรือเวลา
            df['start_time'] = df['start_time'].astype(str).str.strip()
            df['end_time'] = df['end_time'].astype(str).str.strip()
            return df.dropna(subset=['date'])
        except:
            return pd.DataFrame(columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])
    return pd.DataFrame(columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

if 'db' not in st.session_state:
    st.session_state.db = load_data()

TIME_OPTIONS = [f"{h:02d}:00" for h in range(8, 19)]

st.title("🏥 ระบบจองคิวรักษาออนไลน์ (หมอบะฮ์ & หมอโรส)")

# --- แบบฟอร์มการจอง ---
with st.sidebar:
    st.header("📝 แบบฟอร์มการจอง")
    with st.form("booking_form", clear_on_submit=True):
        patient = st.text_input("ชื่อผู้จอง")
        doctor = st.selectbox("เลือกหมอ", ["หมอบะฮ์", "หมอโรส"])
        booking_date = st.date_input("วันที่ต้องการจอง", min_value=datetime.today())
        
        col1, col2 = st.columns(2)
        with col1:
            start_t_str = st.selectbox("เวลาเริ่มต้น", TIME_OPTIONS[:-1], index=0)
        with col2:
            default_end_idx = TIME_OPTIONS.index(start_t_str) + 1
            end_t_str = st.selectbox("เวลาสิ้นสุด", TIME_OPTIONS[1:], index=default_end_idx-1)
            
        submit = st.form_submit_button("ยืนยันการจอง")

        if submit:
            if not patient:
                st.error("❌ กรุณากรอกชื่อผู้จอง")
            else:
                # ตรวจสอบการจองซ้ำ
                mask = (st.session_state.db['date'] == str(booking_date)) & \
                       (pd.to_datetime(st.session_state.db['start_time']).dt.time < datetime.strptime(end_t_str, "%H:%M").time()) & \
                       (pd.to_datetime(st.session_state.db['end_time']).dt.time > datetime.strptime(start_t_str, "%H:%M").time())
                
                if len(st.session_state.db[mask]) < 2:
                    new_entry = pd.DataFrame([[patient, doctor, str(booking_date), start_t_str, end_t_str]], 
                                            columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])
                    st.session_state.db = pd.concat([st.session_state.db, new_entry], ignore_index=True)
                    save_data(st.session_state.db)
                    st.success(f"✅ จองคิวคุณ {patient} สำเร็จ!")
                    st.rerun()
                else:
                    st.error("❌ ขออภัย คิวเต็มแล้วในช่วงเวลานี้")

# --- ปฏิทินและสถิติ ---
tab1, tab2 = st.tabs(["📅 ปฏิทินรายสัปดาห์", "📊 แดชบอร์ดสถิติ"])

with tab1:
    calendar_events = []
    for _, row in st.session_state.db.iterrows():
        color = "#3498db" if row['doctor'] == "หมอบะฮ์" else "#e91e63"
        # ตรวจสอบความถูกต้องของเวลาเบื้องต้น
        s_time = row['start_time'] if ":" in str(row['start_time']) else f"{row['start_time']}:00"
        e_time = row['end_time'] if ":" in str(row['end_time']) else f"{row['end_time']}:00"
        
        calendar_events.append({
            "title": str(row['patient']),
            "start": f"{row['date']}T{s_time}",
            "end": f"{row['date']}T{e_time}",
            "color": color
        })

    calendar_options = {
        "initialView": "timeGridWeek",
        "slotMinTime": "08:00:00",
        "slotMaxTime": "19:00:00",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "timeGridWeek,timeGridDay"},
        "allDaySlot": False,
        "displayEventTime": False,
        "firstDay": 0
    }
    calendar(events=calendar_events, options=calendar_options, key='clinic_calendar')

with tab2:
    if not st.session_state.db.empty:
        df_stats = st.session_state.db.copy()
        df_stats['date_dt'] = pd.to_datetime(df_stats['date'])
        df_stats['month'] = df_stats['date_dt'].dt.strftime('%Y-%m')
        c1, c2 = st.columns(2)
        with c1:
            m_days = df_stats.groupby('month')['date'].nunique().reset_index()
            st.plotly_chart(px.bar(m_days, x='month', y='date', title="จำนวนวันที่มีการจองต่อเดือน"), use_container_width=True)
        with c2:
            top_p = df_stats['patient'].value_counts().reset_index().head(5)
            top_p.columns = ['ชื่อ', 'จำนวนครั้ง']
            st.plotly_chart(px.pie(top_p, values='จำนวนครั้ง', names='ชื่อ', title="ผู้จองบ่อยที่สุด"), use_container_width=True)