"""
SuperPoll Admin Dashboard
Campaign management, question builder, analytics, voter logs
"""
import streamlit as st
import pandas as pd
import os
import base64
import uuid
import io
import qrcode
from pathlib import Path
from datetime import datetime

from core.database import (
    get_campaigns, get_campaign, create_campaign, update_campaign,
    toggle_campaign_status, delete_campaign,
    get_questions, get_question, create_question, update_question, delete_question,
    get_response_count, get_vote_statistics, get_demographic_breakdown,
    get_district_counts, get_voter_logs, reset_responses, export_responses_data,
    get_demographic_attributes, get_demographic_attribute, 
    create_demographic_attribute, update_demographic_attribute,
    toggle_demographic_attribute, delete_demographic_attribute,
    get_campaign_demographics, set_campaign_demographics, get_campaign_demographic_ids,
    get_images, get_image, add_image, update_image, delete_image, get_image_categories,
    get_all_settings, get_setting, set_setting
)
from views.charts_helper import (
    create_bar_chart, create_pie_chart, create_gauge_chart, create_demographic_bar_chart
)

# Upload folder
UPLOAD_FOLDER = Path(__file__).parent.parent / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Admin password (will be loaded from settings)
def get_admin_password():
    return get_setting("admin_password", "superpoll2025")

# Quota targets
QUOTA_TARGETS = {
    "ทั้งหมด": 360,
    "ตะกั่วป่า": 127,
    "ท้ายเหมือง": 124,
    "คุระบุรี": 57,
    "กะปง": 52
}

# Session timeout (1 day in seconds)
SESSION_TIMEOUT = 24 * 60 * 60

def check_login():
    """Check if admin is logged in and session is still valid (within 24 hours)"""
    if not st.session_state.get('admin_logged_in', False):
        return False
    
    # Check session timeout
    login_time = st.session_state.get('login_time')
    if login_time:
        elapsed = (datetime.now() - login_time).total_seconds()
        if elapsed > SESSION_TIMEOUT:
            # Session expired
            st.session_state.admin_logged_in = False
            st.session_state.login_time = None
            return False
    
    return True

def render_login():
    """Render login page"""
    st.markdown("""
    <div style="text-align: center; padding: 60px 0;">
        <h1 style="color: #1e40af;">🔐 SuperPoll Admin</h1>
        <p style="color: #6b7280;">กรุณาใส่รหัสผ่านเพื่อเข้าสู่ระบบ</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("รหัสผ่าน", type="password", key="admin_password")
        
        if st.button("เข้าสู่ระบบ", type="primary", use_container_width=True):
            if password == get_admin_password():
                st.session_state.admin_logged_in = True
                st.session_state.login_time = datetime.now()  # บันทึกเวลา login
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง")

def render_header():
    """Render admin header"""
    st.markdown("""
    <div class="admin-header">
        <h1>🗳️ SuperPoll Admin</h1>
        <p>ระบบจัดการแคมเปญสำรวจความคิดเห็น</p>
    </div>
    """, unsafe_allow_html=True)

def render_campaign_list():
    """Render campaign list with management options"""
    st.markdown("## 📋 รายการแคมเปญ")
    
    campaigns = get_campaigns()
    
    if not campaigns:
        st.info("ยังไม่มีแคมเปญ กรุณาสร้างแคมเปญใหม่")
    
    for camp in campaigns:
        with st.container():
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            
            with col1:
                status_badge = "🟢 เปิดใช้งาน" if camp['is_active'] else "🔴 ปิดใช้งาน"
                response_count = get_response_count(camp['id'])
                st.markdown(f"""
                **{camp['title']}** {status_badge}
                
                {camp.get('description', '')} | 📊 ตอบแล้ว: {response_count} คน
                """)
            
            with col2:
                if st.button("📊", key=f"view_{camp['id']}", help="ดูผลลัพธ์"):
                    st.session_state.selected_campaign = camp['id']
                    st.session_state.admin_view = 'results'
                    st.rerun()
            
            with col3:
                toggle_label = "⏸️" if camp['is_active'] else "▶️"
                if st.button(toggle_label, key=f"toggle_{camp['id']}", 
                           help="เปิด/ปิดแคมเปญ"):
                    toggle_campaign_status(camp['id'])
                    st.rerun()
            
            with col4:
                if st.button("🗑️", key=f"delete_{camp['id']}", help="ลบแคมเปญ"):
                    st.session_state.confirm_delete = camp['id']
                    st.rerun()
        
        st.divider()
    
    # Confirm delete dialog
    if st.session_state.get('confirm_delete'):
        camp_id = st.session_state.confirm_delete
        st.warning(f"⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบแคมเปญนี้? ข้อมูลทั้งหมดจะถูกลบ")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ ยืนยันลบ", type="primary"):
                delete_campaign(camp_id)
                st.session_state.confirm_delete = None
                st.rerun()
        with col2:
            if st.button("❌ ยกเลิก"):
                st.session_state.confirm_delete = None
                st.rerun()
    
    # Create new campaign
    st.markdown("### ➕ สร้างแคมเปญใหม่")
    with st.form("new_campaign"):
        title = st.text_input("ชื่อแคมเปญ")
        description = st.text_area("คำอธิบาย")
        
        if st.form_submit_button("สร้างแคมเปญ", type="primary"):
            if title:
                campaign_id = create_campaign(title, description)
                st.success(f"✅ สร้างแคมเปญสำเร็จ! (ID: {campaign_id})")
                st.rerun()
            else:
                st.error("กรุณาใส่ชื่อแคมเปญ")

def get_img_base64(img_path: str) -> str:
    """Convert image to base64 for preview"""
    try:
        path = Path(img_path)
        if path.exists():
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except:
        pass
    return None

def render_question_builder(campaign_id: int):
    """Render question builder interface"""
    campaign = get_campaign(campaign_id)
    if not campaign:
        st.error("ไม่พบแคมเปญ")
        return
    
    st.markdown(f"## 📝 Question Builder - {campaign['title']}")
    
    # Get existing questions
    questions = get_questions(campaign_id)
    
    # Display existing questions
    if questions:
        st.markdown("### 📋 คำถามที่มีอยู่")
        
        for q in questions:
            with st.expander(f"❓ {q['question_text']}", expanded=False):
                type_badge = "🔵 Single" if q['question_type'] == 'single' else f"🟢 Multi (max {q['max_selections']})"
                st.markdown(f"**ประเภท:** {type_badge}")
                
                st.markdown("**ตัวเลือก:**")
                for opt in q.get('options', []):
                    # Show preview with image if exists
                    img_preview = ""
                    if opt.get('image_url') and Path(opt['image_url']).exists():
                        img_b64 = get_img_base64(opt['image_url'])
                        if img_b64:
                            img_preview = f'<img src="data:image/jpeg;base64,{img_b64}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;vertical-align:middle;margin-right:8px;">'
                    
                    color_dot = f'<span style="display:inline-block;width:12px;height:12px;background:{opt.get("bg_color", "#ccc")};border-radius:2px;margin-right:4px;"></span>'
                    st.markdown(f"{img_preview}{color_dot} {opt['option_text']}", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ แก้ไข", key=f"edit_q_{q['id']}"):
                        st.session_state.editing_question = q['id']
                        st.rerun()
                with col2:
                    if st.button("🗑️ ลบ", key=f"del_q_{q['id']}"):
                        delete_question(q['id'])
                        st.rerun()
    
    # Add/Edit question form
    editing_id = st.session_state.get('editing_question')
    editing_q = get_question(editing_id) if editing_id else None
    
    # Use editing_id in keys to reset form when switching questions
    form_key = f"edit_{editing_id}" if editing_id else "new"
    
    # Cancel editing button
    if editing_q:
        st.markdown("---")
        if st.button("❌ ยกเลิกแก้ไข"):
            st.session_state.editing_question = None
            st.rerun()
    
    form_title = "✏️ แก้ไขคำถาม" if editing_q else "➕ เพิ่มคำถามใหม่"
    st.markdown(f"### {form_title}")
    
    # Get all images for selection
    all_images = get_images()
    image_options = {0: "ไม่เลือกรูป"}
    for img in all_images:
        image_options[img['id']] = f"{img['original_name']} ({img['category']})"
    
    # Question text - key includes editing_id to reset when switching
    q_text = st.text_input("คำถาม", 
        value=editing_q['question_text'] if editing_q else "",
        key=f"q_text_{form_key}")
    
    col1, col2 = st.columns(2)
    with col1:
        q_type_options = ['single', 'multi']
        q_type_idx = q_type_options.index(editing_q['question_type']) if editing_q else 0
        q_type = st.selectbox("ประเภท", q_type_options, index=q_type_idx,
                              format_func=lambda x: "Single Select" if x == 'single' else "Multi Select",
                              key=f"q_type_{form_key}")
    
    with col2:
        max_sel = st.number_input("จำนวนที่เลือกได้สูงสุด", min_value=1, max_value=10,
                                 value=editing_q['max_selections'] if editing_q else 1,
                                 key=f"q_max_sel_{form_key}")
    
    st.markdown("**ตัวเลือก** (กรอกอย่างน้อย 2 ตัวเลือก)")
    st.caption("💡 เลือกรูปภาพจาก Image Gallery - ไปที่เมนู 🖼️ คลังรูปภาพ เพื่ออัพโหลดรูป")
    
    # Get existing options if editing
    existing_options = editing_q.get('options', []) if editing_q else []
    
    options_data = []
    for i in range(6):  # Max 6 options
        st.markdown(f"**ตัวเลือกที่ {i+1}**")
        
        # Get defaults
        default_text = existing_options[i]['option_text'] if i < len(existing_options) else ""
        default_color = existing_options[i].get('bg_color', '#ffffff') if i < len(existing_options) else "#ffffff"
        default_img_url = existing_options[i].get('image_url') if i < len(existing_options) else None
        
        # Find image id from url
        default_img_id = 0
        if default_img_url:
            for img in all_images:
                if img['file_path'] == default_img_url:
                    default_img_id = img['id']
                    break
        
        cols = st.columns([3, 1, 2])
        
        with cols[0]:
            opt_text = st.text_input("ชื่อ", value=default_text, key=f"opt_text_{form_key}_{i}", label_visibility="collapsed", placeholder=f"ชื่อตัวเลือก {i+1}")
        
        with cols[1]:
            opt_color = st.color_picker("สี", value=default_color, key=f"opt_color_{form_key}_{i}")
        
        with cols[2]:
            # Image selector
            img_id = st.selectbox("รูปภาพ", 
                options=list(image_options.keys()),
                format_func=lambda x: image_options.get(x, "ไม่เลือก"),
                index=list(image_options.keys()).index(default_img_id) if default_img_id in image_options else 0,
                key=f"opt_img_{form_key}_{i}",
                label_visibility="collapsed")
        
        # Preview image if selected
        if img_id and img_id != 0:
            selected_img = get_image(img_id)
            if selected_img and Path(selected_img['file_path']).exists():
                img_b64 = get_img_base64(selected_img['file_path'])
                if img_b64:
                    st.markdown(f'''
                    <div style="display:inline-block;margin-bottom:10px;">
                        <img src="data:image/jpeg;base64,{img_b64}" 
                             style="width:60px;height:60px;object-fit:cover;border-radius:8px;border:2px solid #e2e8f0;">
                    </div>
                    ''', unsafe_allow_html=True)
        
        if opt_text:
            img_url = None
            if img_id and img_id != 0:
                selected_img = get_image(img_id)
                if selected_img:
                    img_url = selected_img['file_path']
            
            options_data.append({
                'text': opt_text,
                'bg_color': opt_color,
                'image_url': img_url
            })
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 บันทึก", type="primary", use_container_width=True):
            if not q_text:
                st.error("กรุณาใส่คำถาม")
            elif len(options_data) < 2:
                st.error("กรุณาใส่ตัวเลือกอย่างน้อย 2 ตัว")
            else:
                if editing_q:
                    update_question(editing_q['id'], q_text, q_type, max_sel, options_data)
                    st.session_state.editing_question = None
                    st.success("✅ อัพเดทคำถามเรียบร้อย")
                else:
                    create_question(campaign_id, q_text, q_type, max_sel, options_data)
                    st.success("✅ เพิ่มคำถามเรียบร้อย")
                st.rerun()
    
    with col2:
        if st.button("🔄 รีเซ็ตฟอร์ม", use_container_width=True):
            st.session_state.editing_question = None
            st.rerun()

def render_results(campaign_id: int):
    """Render results dashboard with quota tracking"""
    campaign = get_campaign(campaign_id)
    if not campaign:
        st.error("ไม่พบแคมเปญ")
        return
    
    st.markdown(f"## 📊 Executive Dashboard - {campaign['title']}")
    
    # Quick stats
    total_responses = get_response_count(campaign_id)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        target = QUOTA_TARGETS.get("ทั้งหมด", 360)
        progress = (total_responses / target * 100) if target > 0 else 0
        st.metric("📊 ตอบแล้ว", f"{total_responses} / {target}", f"{progress:.1f}%")
    with col2:
        remaining = max(0, target - total_responses)
        st.metric("⏳ เหลืออีก", remaining, "คน")
    with col3:
        status = "✅ ครบแล้ว!" if total_responses >= target else "🔄 กำลังดำเนินการ"
        st.metric("สถานะ", status)
    
    st.divider()
    
    # Quota gauges by district
    st.markdown("### 📍 Quota Tracking ตามอำเภอ")
    
    district_data = get_district_counts(campaign_id)
    district_counts = {d['value']: d['count'] for d in district_data.get('data', [])}
    
    cols = st.columns(4)
    for i, (district, target) in enumerate(QUOTA_TARGETS.items()):
        if district == "ทั้งหมด":
            continue
        with cols[i % 4]:
            current = district_counts.get(district, 0)
            fig = create_gauge_chart(district, current, target)
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Vote statistics
    st.markdown("### 🗳️ ผลการโหวต")
    
    stats = get_vote_statistics(campaign_id)
    
    if not stats['questions']:
        st.info("ยังไม่มีข้อมูลการโหวต")
    else:
        chart_type = st.radio("รูปแบบกราฟ", ["แท่ง", "วงกลม"], horizontal=True)
        
        for q in stats['questions']:
            if chart_type == "แท่ง":
                fig = create_bar_chart(q['text'], q['options'])
            else:
                fig = create_pie_chart(q['text'], q['options'])
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Demographic breakdown
    st.markdown("### 👥 Demographic Breakdown")
    
    demo_tabs = st.tabs(["ช่วงอายุ (Gen)", "เพศ", "อำเภอ", "พื้นที่"])
    
    demo_fields = [('Gen', 'ช่วงอายุ'), ('เพศ', 'เพศ'), ('อำเภอ', 'อำเภอ'), ('พื้นที่', 'พื้นที่')]
    
    for tab, (field, label) in zip(demo_tabs, demo_fields):
        with tab:
            data = get_demographic_breakdown(campaign_id, field)
            if data['data']:
                fig = create_demographic_bar_chart(label, data['data'])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูล")

def render_voter_logs(campaign_id: int):
    """Render detailed voter logs"""
    st.markdown("## 📋 Voter Logs")
    
    logs = get_voter_logs(campaign_id)
    
    if not logs:
        st.info("ยังไม่มีข้อมูลผู้ตอบ")
        return
    
    st.markdown(f"**รวมทั้งหมด:** {len(logs)} รายการ")
    
    # Create dataframe for display
    log_data = []
    for log in logs:
        demo = log.get('demographic_data', {})
        loc = log.get('location_data', {})
        
        # Create Google Maps link
        lat = loc.get('lat')
        lon = loc.get('lon')
        map_link = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else ""
        
        log_data.append({
            'เวลา': log['created_at'],
            'อำเภอ': demo.get('อำเภอ', '-'),
            'พื้นที่': demo.get('พื้นที่', '-'),
            'Gen': demo.get('Gen', '-'),
            'เพศ': demo.get('เพศ', '-'),
            'IP': log.get('ip_address', '-'),
            'เมือง': loc.get('city', '-'),
            'ประเทศ': loc.get('country', '-'),
            'ISP': loc.get('isp', '-'),
            'พิกัด': map_link
        })
    
    df = pd.DataFrame(log_data)
    
    # Display as table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Download option
    st.download_button(
        label="📥 ดาวน์โหลด CSV",
        data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"voter_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def render_export(campaign_id: int):
    """Render data export interface"""
    st.markdown("## 📤 Export Data")
    
    data = export_responses_data(campaign_id)
    
    if not data:
        st.info("ยังไม่มีข้อมูลให้ export")
        return
    
    st.markdown(f"**จำนวนข้อมูล:** {len(data)} รายการ")
    
    df = pd.DataFrame(data)
    
    # Preview
    st.markdown("### Preview")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)
    
    # Download
    st.download_button(
        label="📥 ดาวน์โหลด Full CSV",
        data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"superpoll_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def render_danger_zone(campaign_id: int):
    """Render danger zone with reset option"""
    st.markdown("## ⚠️ Danger Zone")
    
    st.warning("คำเตือน: การดำเนินการในส่วนนี้ไม่สามารถย้อนกลับได้")
    
    response_count = get_response_count(campaign_id)
    st.markdown(f"**จำนวนข้อมูลปัจจุบัน:** {response_count} รายการ")
    
    if st.button("🗑️ ล้างข้อมูลผู้ตอบทั้งหมด", type="secondary"):
        st.session_state.confirm_reset = True
    
    if st.session_state.get('confirm_reset'):
        st.error("⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูลผู้ตอบทั้งหมด?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ ยืนยันลบ", type="primary"):
                reset_responses(campaign_id)
                st.session_state.confirm_reset = False
                st.success("✅ ลบข้อมูลเรียบร้อย")
                st.rerun()
        with col2:
            if st.button("❌ ยกเลิก"):
                st.session_state.confirm_reset = False
                st.rerun()

def render_image_manager():
    """Render image upload and management interface"""
    st.markdown("## 🖼️ คลังรูปภาพ")
    st.caption("อัพโหลดและจัดการรูปภาพสำหรับใช้ใน Question Builder")
    
    # Upload section
    st.markdown("### 📤 อัพโหลดรูปใหม่")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "เลือกไฟล์รูปภาพ", 
            type=['png', 'jpg', 'jpeg', 'webp'],
            accept_multiple_files=True,
            key="image_uploader"
        )
    
    with col2:
        category = st.text_input("หมวดหมู่", value="ผู้สมัคร", key="upload_category")
        description = st.text_input("คำอธิบาย (optional)", key="upload_desc")
    
    if uploaded_files:
        if st.button("📤 อัพโหลดทั้งหมด", type="primary"):
            for uploaded_file in uploaded_files:
                # Generate unique filename
                ext = uploaded_file.name.split('.')[-1]
                filename = f"{uuid.uuid4().hex}.{ext}"
                file_path = UPLOAD_FOLDER / filename
                
                # Save file
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Add to database
                add_image(
                    filename=filename,
                    original_name=uploaded_file.name,
                    file_path=str(file_path),
                    category=category,
                    description=description
                )
            
            st.success(f"✅ อัพโหลดสำเร็จ {len(uploaded_files)} รูป")
            st.rerun()
    
    st.divider()
    
    # Gallery section
    st.markdown("### 🖼️ รูปภาพทั้งหมด")
    
    # Category filter
    categories = get_image_categories()
    if categories:
        filter_options = ["ทั้งหมด"] + categories
        selected_filter = st.selectbox("กรองตามหมวดหมู่", filter_options)
        
        if selected_filter == "ทั้งหมด":
            images = get_images()
        else:
            images = get_images(category=selected_filter)
    else:
        images = get_images()
    
    if not images:
        st.info("ยังไม่มีรูปภาพในคลัง กรุณาอัพโหลดรูปใหม่")
        return
    
    st.markdown(f"**จำนวนรูปภาพ:** {len(images)} รูป")
    
    # Display in grid
    cols_per_row = 4
    for i in range(0, len(images), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(images):
                img = images[idx]
                with col:
                    # Show image preview
                    if Path(img['file_path']).exists():
                        img_b64 = get_img_base64(img['file_path'])
                        if img_b64:
                            st.markdown(f'''
                            <div style="text-align:center;margin-bottom:8px;">
                                <img src="data:image/jpeg;base64,{img_b64}" 
                                     style="width:100%;max-height:120px;object-fit:cover;border-radius:8px;border:2px solid #e2e8f0;">
                            </div>
                            ''', unsafe_allow_html=True)
                    
                    st.caption(f"📁 {img['original_name'][:15]}...")
                    st.caption(f"🏷️ {img['category']}")
                    
                    if st.button("🗑️", key=f"del_img_{img['id']}", help="ลบรูป"):
                        delete_image(img['id'])
                        st.rerun()

def generate_qr_code(url: str, size: int = 10):
    """Generate QR code image for URL"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return img_b64

def render_server_settings():
    """Render server settings page"""
    st.markdown("## 🌐 ตั้งค่า Server")
    st.caption("ตั้งค่า URL ของ server สำหรับสร้าง QR Code และลิงก์โพล")
    
    # Server URL
    st.markdown("### 🔗 Server URL")
    
    current_url = get_setting("server_url", "http://localhost:8501")
    
    new_url = st.text_input(
        "URL ของ Server",
        value=current_url,
        help="ใส่ IP address หรือ domain name ของ server เช่น http://192.168.1.100:8501 หรือ https://poll.example.com",
        key="server_url_input"
    )
    
    st.caption("💡 **ตัวอย่าง URL:**")
    st.caption("- Local: `http://localhost:8501`")
    st.caption("- IP Address: `http://192.168.1.100:8501`")
    st.caption("- Domain: `https://poll.mycompany.com`")
    
    if new_url != current_url:
        if st.button("💾 บันทึก URL", type="primary"):
            set_setting("server_url", new_url, "URL ของ server สำหรับสร้าง QR Code")
            st.success("✅ บันทึก URL เรียบร้อย")
            st.rerun()
    
    st.divider()
    
    # QR Code Generator
    st.markdown("### 📱 สร้าง QR Code สำหรับแคมเปญ")
    
    campaigns = get_campaigns()
    
    if not campaigns:
        st.info("ยังไม่มีแคมเปญ กรุณาสร้างแคมเปญก่อน")
        return
    
    # Campaign selector
    campaign_options = {c['id']: c['title'] for c in campaigns}
    selected_campaign_id = st.selectbox(
        "เลือกแคมเปญ",
        options=list(campaign_options.keys()),
        format_func=lambda x: campaign_options.get(x, ""),
        key="qr_campaign_select"
    )
    
    if selected_campaign_id:
        campaign = get_campaign(selected_campaign_id)
        server_url = get_setting("server_url", "http://localhost:8501")
        
        # Remove trailing slash
        server_url = server_url.rstrip('/')
        poll_url = f"{server_url}/?poll={selected_campaign_id}"
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**🔗 ลิงก์โพล:**")
            st.code(poll_url)
            
            # Copy hint
            st.caption("📋 คลิกที่ลิงก์เพื่อคัดลอก")
            
            # QR size
            qr_size = st.slider("ขนาด QR Code", min_value=5, max_value=20, value=10, key="qr_size")
        
        with col2:
            st.markdown("**📱 QR Code:**")
            
            # Generate QR
            qr_b64 = generate_qr_code(poll_url, qr_size)
            
            st.markdown(f'''
            <div style="text-align:center;padding:20px;background:#f8fafc;border-radius:12px;">
                <img src="data:image/png;base64,{qr_b64}" style="max-width:100%;border-radius:8px;">
            </div>
            ''', unsafe_allow_html=True)
            
            # Download button
            qr_bytes = base64.b64decode(qr_b64)
            st.download_button(
                label="⬇️ ดาวน์โหลด QR Code",
                data=qr_bytes,
                file_name=f"qr_poll_{selected_campaign_id}.png",
                mime="image/png",
                use_container_width=True
            )
        
        # Campaign info
        st.divider()
        st.markdown("### 📋 ข้อมูลแคมเปญ")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("ชื่อแคมเปญ", campaign['title'][:20] + "..." if len(campaign['title']) > 20 else campaign['title'])
        with col2:
            status = "🟢 เปิด" if campaign.get('is_active') else "🔴 ปิด"
            st.metric("สถานะ", status)
        with col3:
            count = get_response_count(selected_campaign_id)
            st.metric("จำนวนผู้ตอบ", f"{count} คน")
    
    st.divider()
    
    # Admin password setting
    st.markdown("### 🔑 รหัสผ่าน Admin")
    
    current_password = get_setting("admin_password", "superpoll2025")
    
    new_password = st.text_input(
        "รหัสผ่านใหม่",
        value=current_password,
        type="password",
        key="new_admin_password"
    )
    
    confirm_password = st.text_input(
        "ยืนยันรหัสผ่าน",
        type="password",
        key="confirm_admin_password"
    )
    
    if new_password and new_password != current_password:
        if new_password == confirm_password:
            if st.button("🔐 เปลี่ยนรหัสผ่าน"):
                set_setting("admin_password", new_password, "รหัสผ่านเข้าระบบ Admin")
                st.success("✅ เปลี่ยนรหัสผ่านเรียบร้อย")
                st.rerun()
        else:
            st.warning("⚠️ รหัสผ่านไม่ตรงกัน")

def render_demographic_settings():
    """Render demographic attributes management"""
    st.markdown("## ⚙️ ตั้งค่าคุณสมบัติผู้ตอบ")
    st.caption("จัดการ attributes ที่ใช้เก็บข้อมูลผู้ตอบแบบสำรวจ")
    
    # Get all attributes
    attributes = get_demographic_attributes()
    
    if attributes:
        st.markdown("### 📋 รายการคุณสมบัติ")
        
        for attr in attributes:
            status_icon = "🟢" if attr['is_active'] else "🔴"
            options_count = len(attr.get('options', []))
            
            with st.expander(f"{status_icon} **{attr['label']}** ({attr['name']}) - {options_count} ตัวเลือก", expanded=False):
                st.markdown(f"**ชื่อ (key):** `{attr['name']}`")
                st.markdown(f"**ป้ายกำกับ:** {attr['label']}")
                st.markdown(f"**ประเภท:** {attr['input_type']}")
                
                st.markdown("**ตัวเลือก:**")
                for opt in attr.get('options', []):
                    st.markdown(f"- {opt['option_text']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✏️ แก้ไข", key=f"edit_attr_{attr['id']}"):
                        st.session_state.editing_attr = attr['id']
                        st.rerun()
                with col2:
                    toggle_text = "⏸️ ปิด" if attr['is_active'] else "▶️ เปิด"
                    if st.button(toggle_text, key=f"toggle_attr_{attr['id']}"):
                        toggle_demographic_attribute(attr['id'])
                        st.rerun()
                with col3:
                    if st.button("🗑️ ลบ", key=f"del_attr_{attr['id']}"):
                        st.session_state.confirm_del_attr = attr['id']
                        st.rerun()
        
        # Confirm delete
        if st.session_state.get('confirm_del_attr'):
            attr_id = st.session_state.confirm_del_attr
            st.warning("⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบคุณสมบัตินี้?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ ยืนยันลบ", type="primary", key="confirm_del_attr_btn"):
                    delete_demographic_attribute(attr_id)
                    st.session_state.confirm_del_attr = None
                    st.rerun()
            with col2:
                if st.button("❌ ยกเลิก", key="cancel_del_attr_btn"):
                    st.session_state.confirm_del_attr = None
                    st.rerun()
    
    st.divider()
    
    # Add/Edit form
    editing_id = st.session_state.get('editing_attr')
    editing_attr = get_demographic_attribute(editing_id) if editing_id else None
    
    form_title = "✏️ แก้ไขคุณสมบัติ" if editing_attr else "➕ เพิ่มคุณสมบัติใหม่"
    st.markdown(f"### {form_title}")
    
    with st.form("attr_form"):
        col1, col2 = st.columns(2)
        with col1:
            attr_name = st.text_input("ชื่อ (key)", 
                value=editing_attr['name'] if editing_attr else "",
                help="ใช้เป็น key ในระบบ เช่น district, gender")
        with col2:
            attr_label = st.text_input("ป้ายกำกับ", 
                value=editing_attr['label'] if editing_attr else "",
                help="แสดงในหน้าโหวต เช่น อำเภอ, เพศ")
        
        input_type = st.selectbox("ประเภท Input",
            ["select", "radio", "text"],
            index=["select", "radio", "text"].index(editing_attr['input_type']) if editing_attr else 0,
            format_func=lambda x: {"select": "Dropdown", "radio": "Radio Button", "text": "ข้อความ"}[x])
        
        st.markdown("**ตัวเลือก** (ใส่ทีละบรรทัด, ใช้กับ select/radio)")
        existing_options = "\n".join([o['option_text'] for o in editing_attr.get('options', [])]) if editing_attr else ""
        options_text = st.text_area("ตัวเลือก", value=existing_options, height=150)
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 บันทึก", type="primary")
        with col2:
            if editing_attr:
                if st.form_submit_button("❌ ยกเลิก"):
                    st.session_state.editing_attr = None
                    st.rerun()
        
        if submitted:
            if not attr_name or not attr_label:
                st.error("กรุณากรอกชื่อและป้ายกำกับ")
            else:
                options_list = [o.strip() for o in options_text.split('\n') if o.strip()]
                
                if editing_attr:
                    update_demographic_attribute(editing_id, attr_name, attr_label, input_type, options_list)
                    st.session_state.editing_attr = None
                    st.success("✅ อัพเดทคุณสมบัติเรียบร้อย")
                else:
                    create_demographic_attribute(attr_name, attr_label, input_type, options_list)
                    st.success("✅ เพิ่มคุณสมบัติเรียบร้อย")
                st.rerun()

def render_campaign_demographics(campaign_id: int):
    """Render campaign demographics selection"""
    campaign = get_campaign(campaign_id)
    if not campaign:
        st.error("ไม่พบแคมเปญ")
        return
    
    st.markdown(f"## 👥 ตั้งค่าคุณสมบัติผู้ตอบ - {campaign['title']}")
    st.caption("เลือกคุณสมบัติที่ต้องการเก็บข้อมูลสำหรับแคมเปญนี้")
    
    # Get all active attributes
    all_attrs = get_demographic_attributes(active_only=True)
    
    if not all_attrs:
        st.warning("⚠️ ยังไม่มีคุณสมบัติในระบบ กรุณาเพิ่มคุณสมบัติก่อน")
        if st.button("➕ ไปเพิ่มคุณสมบัติ"):
            st.session_state.admin_view = 'demographics'
            st.rerun()
        return
    
    # Get current campaign demographics
    current_ids = get_campaign_demographic_ids(campaign_id)
    
    st.markdown("### ✅ เลือกคุณสมบัติที่ใช้")
    
    selected_ids = []
    
    for attr in all_attrs:
        is_selected = attr['id'] in current_ids
        options_preview = ", ".join([o['option_text'] for o in attr.get('options', [])[:3]])
        if len(attr.get('options', [])) > 3:
            options_preview += "..."
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.checkbox("", value=is_selected, key=f"demo_check_{attr['id']}"):
                selected_ids.append(attr['id'])
        with col2:
            st.markdown(f"**{attr['label']}** (`{attr['name']}`)")
            st.caption(f"ตัวเลือก: {options_preview}")
    
    st.divider()
    
    if st.button("💾 บันทึกการตั้งค่า", type="primary"):
        set_campaign_demographics(campaign_id, selected_ids)
        st.success("✅ บันทึกการตั้งค่าเรียบร้อย")
        st.rerun()

def render_admin_app():
    """Main admin interface router"""
    # Check login
    if not check_login():
        render_login()
        return
    
    # Header
    render_header()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🏠 เมนูหลัก")
        
        if st.button("📋 แคมเปญ", use_container_width=True):
            st.session_state.admin_view = 'campaigns'
            st.session_state.selected_campaign = None
            st.rerun()
        
        if st.button("⚙️ ตั้งค่าคุณสมบัติ", use_container_width=True):
            st.session_state.admin_view = 'demographics'
            st.session_state.selected_campaign = None
            st.rerun()
        
        # Campaign-specific menu
        if st.session_state.get('selected_campaign'):
            campaign = get_campaign(st.session_state.selected_campaign)
            if campaign:
                st.divider()
                st.markdown(f"**📁 {campaign['title']}**")
                
                if st.button("📊 ผลลัพธ์", use_container_width=True):
                    st.session_state.admin_view = 'results'
                    st.rerun()
                
                if st.button("📝 Question Builder", use_container_width=True):
                    st.session_state.admin_view = 'questions'
                    st.rerun()
                
                if st.button("👥 คุณสมบัติผู้ตอบ", use_container_width=True):
                    st.session_state.admin_view = 'campaign_demo'
                    st.rerun()
                
                if st.button("📋 Voter Logs", use_container_width=True):
                    st.session_state.admin_view = 'logs'
                    st.rerun()
                
                if st.button("📤 Export", use_container_width=True):
                    st.session_state.admin_view = 'export'
                    st.rerun()
                
                if st.button("⚠️ Danger Zone", use_container_width=True):
                    st.session_state.admin_view = 'danger'
                    st.rerun()
        
        st.divider()
        
        # System settings
        st.markdown("### 🛠️ ตั้งค่าระบบ")
        
        if st.button("🖼️ คลังรูปภาพ", use_container_width=True):
            st.session_state.admin_view = 'images'
            st.session_state.selected_campaign = None
            st.rerun()
        
        if st.button("🌐 ตั้งค่า Server", use_container_width=True):
            st.session_state.admin_view = 'server_settings'
            st.session_state.selected_campaign = None
            st.rerun()
        
        # Poll link
        if st.session_state.get('selected_campaign'):
            st.divider()
            camp_id = st.session_state.selected_campaign
            server_url = get_setting("server_url", "http://localhost:8501").rstrip('/')
            st.markdown("### 🔗 ลิงก์โพล")
            poll_url = f"{server_url}/?poll={camp_id}"
            st.code(poll_url)
            st.caption("📋 คลิกเพื่อคัดลอก")
        
        st.divider()
        
        # Logout
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.session_state.login_time = None
            st.rerun()
    
    # Main content
    view = st.session_state.get('admin_view', 'campaigns')
    campaign_id = st.session_state.get('selected_campaign')
    
    if view == 'demographics':
        render_demographic_settings()
    elif view == 'images':
        render_image_manager()
    elif view == 'server_settings':
        render_server_settings()
    elif view == 'campaigns' or not campaign_id:
        render_campaign_list()
    elif view == 'results':
        render_results(campaign_id)
    elif view == 'questions':
        render_question_builder(campaign_id)
    elif view == 'campaign_demo':
        render_campaign_demographics(campaign_id)
    elif view == 'logs':
        render_voter_logs(campaign_id)
    elif view == 'export':
        render_export(campaign_id)
    elif view == 'danger':
        render_danger_zone(campaign_id)
    else:
        render_campaign_list()
