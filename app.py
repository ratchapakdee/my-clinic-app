import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import plotly.express as px
import os

st.set_page_config(page_title="ระบบจองคิวออนไลน์ (CSV Mode)", layout="wide")

DATA_FILE = 'bookings.csv'

# --- ฟังก์ชันจัดการข้อมูล ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            return df.dropna(subset=['date'])
        except:
            return pd.DataFrame(columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])
    return pd.DataFrame(columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])

def save_data(df):
    # บันทึกแบบ utf-8-sig เพื่อให้ Excel เปิดแล้วภาษาไทยไม่เพี้ยน
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

# โหลดข้อมูล
if 'db' not in st.session_state:
    st.session_state.db = load_data()

TIME_OPTIONS = [f"{h:02d}:00" for h in range(8, 19)]

st.title("🏥 ระบบจองคิวรักษาออนไลน์ (หมอบะฮ์ & หมอโรส)")

# --- แถบด้านข้าง: จองคิวใหม่ ---
with st.sidebar:
    st.header("📝 จองคิวใหม่")
    with st.form("booking_form", clear_on_submit=True):
        patient = st.text_input("ชื่อผู้จอง")
        doctor = st.selectbox("เลือกหมอ", ["หมอบะฮ์", "หมอโรส"])
        booking_date = st.date_input("วันที่จอง", min_value=datetime.today())
        col1, col2 = st.columns(2)
        with col1:
            start_t = st.selectbox("เริ่ม", TIME_OPTIONS[:-1])
        with col2:
            end_t = st.selectbox("เลิก", TIME_OPTIONS[1:], index=1)
            
        if st.form_submit_button("ยืนยันการจอง"):
            if patient:
                new_data = pd.DataFrame([[patient, doctor, str(booking_date), start_t, end_t]], 
                                        columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])
                st.session_state.db = pd.concat([st.session_state.db, new_data], ignore_index=True)
                save_data(st.session_state.db)
                st.success(f"บันทึกคิวคุณ {patient} แล้ว")
                st.rerun()

# --- ส่วนหลัก: ปฏิทิน / จัดการข้อมูล / สถิติ ---
tab1, tab2, tab3 = st.tabs(["📅 ตารางคิว", "⚙️ แก้ไข/ลบข้อมูล", "📊 สรุปสถิติ"])

with tab1:
    events = []
    for _, row in st.session_state.db.iterrows():
        events.append({
            "title": str(row['patient']),
            "start": f"{row['date']}T{row['start_time']}:00",
            "end": f"{row['date']}T{row['end_time']}:00",
            "color": "#3498db" if row['doctor'] == "หมอบะฮ์" else "#e91e63"
        })
    calendar(events=events, options={"initialView": "timeGridWeek", "slotMinTime": "08:00:00", "slotMaxTime": "19:00:00", "displayEventTime": False})

with tab2:
    st.subheader("🛠️ จัดการข้อมูลคิวที่จองไว้")
    if not st.session_state.db.empty:
        # สร้างตัวเลือกสำหรับแก้ไข/ลบ
        df_manage = st.session_state.db.copy()
        df_manage['id'] = df_manage['date'] + " | " + df_manage['patient']
        
        choice = st.selectbox("เลือกคิวที่ต้องการจัดการ", df_manage['id'].tolist())
        target_idx = df_manage[df_manage['id'] == choice].index[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("แก้ไขชื่อ")
            new_name = st.text_input("ชื่อคนไข้", value=st.session_state.db.loc[target_idx, 'patient'])
            if st.button("💾 บันทึกการแก้ไข"):
                st.session_state.db.loc[target_idx, 'patient'] = new_name
                save_data(st.session_state.db)
                st.success("แก้ไขเรียบร้อย!")
                st.rerun()
        with c2:
            st.warning("ยกเลิกคิว")
            if st.button("🗑️ ยืนยันการลบคิวนี้"):
                st.session_state.db = st.session_state.db.drop(target_idx).reset_index(drop=True)
                save_data(st.session_state.db)
                st.success("ลบข้อมูลสำเร็จ")
                st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลคิวในระบบ")

with tab3:
    if not st.session_state.db.empty:
        stats = st.session_state.db['patient'].value_counts().reset_index().head(5)
        stats.columns = ['ชื่อ', 'จำนวนครั้ง']
        st.plotly_chart(px.bar(stats, x='ชื่อ', y='จำนวนครั้ง', title="Top 5 คนไข้ที่มาบ่อย"), use_container_width=True)
