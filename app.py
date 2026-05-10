import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import plotly.express as px

st.set_page_config(page_title="ระบบจองคิวออนไลน์", layout="wide")

# เชื่อมต่อกับ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # อ่านข้อมูลและล้างค่าวันที่ให้สะอาด
        df = conn.read(ttl=0) # ttl=0 เพื่อให้ดึงข้อมูลใหม่ล่าสุดเสมอ
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        return df.dropna(subset=['date'])
    except:
        return pd.DataFrame(columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])

# โหลดข้อมูลเข้า Session State
if 'db' not in st.session_state or st.sidebar.button("🔄 อัปเดตข้อมูลจาก Sheets"):
    st.session_state.db = load_data()

TIME_OPTIONS = [f"{h:02d}:00" for h in range(8, 19)]

st.title("🏥 ระบบจองคิวรักษาออนไลน์ (หมอบะฮ์ & หมอโรส)")

# --- ส่วนที่ 1: แบบฟอร์มการจอง (Sidebar) ---
with st.sidebar:
    st.header("📝 แบบฟอร์มการจองใหม่")
    with st.form("booking_form", clear_on_submit=True):
        patient = st.text_input("ชื่อผู้จอง")
        doctor = st.selectbox("เลือกหมอ", ["หมอบะฮ์", "หมอโรส"])
        booking_date = st.date_input("วันที่ต้องการจอง", min_value=datetime.today())
        
        col1, col2 = st.columns(2)
        with col1:
            start_t_str = st.selectbox("เวลาเริ่มต้น", TIME_OPTIONS[:-1])
        with col2:
            end_t_str = st.selectbox("เวลาสิ้นสุด", TIME_OPTIONS[1:], index=1)
            
        submit = st.form_submit_button("ยืนยันการจอง")

        if submit and patient:
            new_entry = pd.DataFrame([[patient, doctor, str(booking_date), start_t_str, end_t_str]], 
                                    columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])
            st.session_state.db = pd.concat([st.session_state.db, new_entry], ignore_index=True)
            conn.update(data=st.session_state.db)
            st.success(f"✅ เพิ่มคิวคุณ {patient} เรียบร้อย!")
            st.rerun()

# --- ส่วนที่ 2: หน้าหลัก (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📅 ปฏิทิน", "⚙️ จัดการข้อมูล (แก้ไข/ลบ)", "📊 แดชบอร์ด"])

with tab1:
    calendar_events = []
    for _, row in st.session_state.db.iterrows():
        color = "#3498db" if row['doctor'] == "หมอบะฮ์" else "#e91e63"
        calendar_events.append({
            "title": str(row['patient']),
            "start": f"{row['date']}T{row['start_time']}:00",
            "end": f"{row['date']}T{row['end_time']}:00",
            "color": color
        })
    calendar(events=calendar_events, options={"initialView": "timeGridWeek", "slotMinTime": "08:00:00", "slotMaxTime": "19:00:00", "displayEventTime": False}, key='clinic_calendar')

with tab2:
    st.subheader("🛠️ แก้ไขหรือลบข้อมูลการจอง")
    if not st.session_state.db.empty:
        # เลือกรายชื่อที่ต้องการจัดการ
        df_display = st.session_state.db.copy()
        df_display['select_name'] = df_display['date'] + " | " + df_display['patient'] + " (" + df_display['doctor'] + ")"
        
        selected_booking = st.selectbox("เลือกคิวที่ต้องการจัดการ", df_display['select_name'].tolist())
        idx = df_display[df_display['select_name'] == selected_booking].index[0]
        
        col_edit, col_del = st.columns(2)
        
        with col_edit:
            st.info("แก้ไขข้อมูล")
            new_name = st.text_input("แก้ไขชื่อ", value=st.session_state.db.loc[idx, 'patient'])
            new_doc = st.selectbox("เปลี่ยนหมอ", ["หมอบะฮ์", "หมอโรส"], index=0 if st.session_state.db.loc[idx, 'doctor'] == "หมอบะฮ์" else 1)
            if st.button("💾 บันทึกการแก้ไข"):
                st.session_state.db.loc[idx, 'patient'] = new_name
                st.session_state.db.loc[idx, 'doctor'] = new_doc
                conn.update(data=st.session_state.db)
                st.success("แก้ไขข้อมูลสำเร็จ!")
                st.rerun()
                
        with col_del:
            st.warning("ลบข้อมูล")
            st.write(f"คุณแน่ใจหรือไม่ที่จะลบคิวของ: **{st.session_state.db.loc[idx, 'patient']}**")
            if st.button("🗑️ ยืนยันการลบตัวเลือกนี้"):
                st.session_state.db = st.session_state.db.drop(idx).reset_index(drop=True)
                conn.update(data=st.session_state.db)
                st.success("ลบข้อมูลเรียบร้อย!")
                st.rerun()
    else:
        st.write("ยังไม่มีข้อมูลการจอง")

with tab3:
    if not st.session_state.db.empty:
        # แก้ไขจุดที่เคย Error value_usage เป็น value_counts
        top_patients = st.session_state.db['patient'].value_counts().reset_index().head(5)
        top_patients.columns = ['ชื่อคนไข้', 'จำนวนครั้ง']
        st.plotly_chart(px.bar(top_patients, x='ชื่อคนไข้', y='จำนวนครั้ง', title="คนไข้ที่มาบ่อยที่สุด"), use_container_width=True)
