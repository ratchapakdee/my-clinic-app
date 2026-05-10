import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import plotly.express as px

st.set_page_config(page_title="ระบบจองคิวออนไลน์", layout="wide")

# --- เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ดึงข้อมูลล่าสุดเสมอ (ttl=0)
        df = conn.read(ttl=0)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        return df.dropna(subset=['date'])
    except:
        return pd.DataFrame(columns=['patient', 'doctor', 'date', 'start_time', 'end_time'])

# เก็บข้อมูลใน session
if 'db' not in st.session_state:
    st.session_state.db = load_data()

TIME_OPTIONS = [f"{h:02d}:00" for h in range(8, 19)]

st.title("🏥 ระบบจองคิวรักษาออนไลน์ (หมอฮาบีบะฮ์ คลินิกการแพทย์แผนไทย)")

# --- แถบด้านข้าง: จองคิวใหม่ ---
with st.sidebar:
    st.header("📝 จองคิวใหม่")
    if st.button("🔄 รีเฟรชดึงข้อมูลจาก Sheets"):
        st.session_state.db = load_data()
        st.rerun()
        
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
                conn.update(data=st.session_state.db)
                st.success(f"บันทึกคิวคุณ {patient} แล้ว")
                st.rerun()

# --- ส่วนหลัก: ปฏิทิน / แก้ไขข้อมูล / สถิติ ---
tab1, tab2, tab3 = st.tabs(["📅 ตารางคิว", "⚙️ แก้ไข/ลบข้อมูล", "📊 สรุปสถิติ"])

with tab1:
    events = []
    for _, row in st.session_state.db.iterrows():
        events.append({
            "title": row['patient'],
            "start": f"{row['date']}T{row['start_time']}:00",
            "end": f"{row['date']}T{row['end_time']}:00",
            "color": "#3498db" if row['doctor'] == "หมอบะฮ์" else "#e91e63"
        })
    calendar(events=events, options={"initialView": "timeGridWeek", "slotMinTime": "08:00:00", "slotMaxTime": "19:00:00", "displayEventTime": False})

with tab2:
    st.subheader("🛠️ จัดการข้อมูลคิวที่จองไว้")
    if not st.session_state.db.empty:
        # สร้างรายการให้เลือกเพื่อแก้ไขหรือลบ
        st.session_state.db['display_text'] = st.session_state.db['date'] + " | " + st.session_state.db['patient']
        choice = st.selectbox("เลือกคิวที่ต้องการจัดการ", st.session_state.db['display_text'].tolist())
        target_idx = st.session_state.db[st.session_state.db['display_text'] == choice].index[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### **แก้ไขข้อมูล**")
            edit_name = st.text_input("ชื่อ", value=st.session_state.db.loc[target_idx, 'patient'])
            if st.button("💾 บันทึกการแก้ไข"):
                st.session_state.db.loc[target_idx, 'patient'] = edit_name
                conn.update(data=st.session_state.db.drop(columns=['display_text'], errors='ignore'))
                st.success("แก้ไขเรียบร้อย!")
                st.rerun()
        with c2:
            st.markdown("### **ยกเลิกคิว**")
            st.write(f"ลบคิวของ: {st.session_state.db.loc[target_idx, 'patient']}")
            if st.button("🗑️ ยืนยันการลบคิวนี้"):
                st.session_state.db = st.session_state.db.drop(target_idx).reset_index(drop=True)
                conn.update(data=st.session_state.db.drop(columns=['display_text'], errors='ignore'))
                st.warning("ลบข้อมูลสำเร็จ")
                st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลคิวในระบบ")

with tab3:
    if not st.session_state.db.empty:
        # แก้ไขจุดที่เคย Error value_usage เป็น value_counts
        stats = st.session_state.db['patient'].value_counts().reset_index().head(5)
        stats.columns = ['ชื่อ', 'จำนวนครั้ง']
        st.plotly_chart(px.bar(stats, x='ชื่อ', y='จำนวนครั้ง', title="Top 5 คนไข้ที่มาบ่อย"), use_container_width=True)
