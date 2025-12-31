"""
SuperPoll Voter UI
Mobile-first voting interface with card-based selection
"""
import streamlit as st
import base64
import requests
from pathlib import Path
from core.database import get_campaign, get_questions, submit_response, get_response_count, get_campaign_demographics, get_demographic_attributes

def get_img_base64(img_path: str) -> str:
    """Convert image to base64 for embedding"""
    try:
        path = Path(img_path)
        if path.exists():
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except:
        pass
    return None

def get_ip_address() -> str:
    """Get user's IP address"""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except:
        return None

def get_location_data(ip_address: str) -> dict:
    """Get location data from IP"""
    if not ip_address:
        return None
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'city': data.get('city', ''),
                'country': data.get('country', ''),
                'isp': data.get('isp', ''),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'region': data.get('regionName', '')
            }
    except:
        pass
    return None

def render_card_html(opt: dict, is_selected: bool, q_type: str) -> str:
    """Generate HTML for voting card - 25% image / 75% text layout"""
    has_image = opt.get('image_url') and Path(opt['image_url']).exists() if opt.get('image_url') else False
    bg_color = opt.get('bg_color', '#ffffff')
    
    # Selection styling
    border_color = '#22c55e' if is_selected else '#e2e8f0'
    border_width = '3px' if is_selected else '2px'
    check_display = 'flex' if is_selected else 'none'
    
    # Determine text color based on background brightness
    # Simple check: if bg is dark, use white text
    text_color = '#ffffff'
    try:
        # Extract RGB from hex
        hex_color = bg_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = '#1f2937' if brightness > 128 else '#ffffff'
    except:
        text_color = '#1f2937'
    
    if has_image:
        # Card with image: 25% image / 75% text
        img_b64 = get_img_base64(opt['image_url'])
        return f'''<div class="vote-card vote-card-with-image" style="border:{border_width} solid {border_color};border-radius:12px;overflow:hidden;position:relative;display:flex;align-items:stretch;background:{bg_color};cursor:pointer;transition:all 0.2s ease;margin-bottom:8px;"><div style="width:25%;min-width:80px;max-width:100px;flex-shrink:0;background:url('data:image/jpeg;base64,{img_b64}') center/cover;border-radius:10px 0 0 10px;"></div><div style="flex:1;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;min-height:70px;"><span style="font-weight:600;font-size:15px;color:{text_color};line-height:1.3;">{opt['option_text']}</span><div style="width:28px;height:28px;background:#22c55e;border-radius:50%;display:{check_display};align-items:center;justify-content:center;flex-shrink:0;margin-left:12px;"><svg width="16" height="16" fill="white" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg></div></div></div>'''
    else:
        # Small card text-only with background color
        return f'''
        <div class="vote-card vote-card-small" style="
            border: {border_width} solid {border_color};
            border-radius: 12px;
            padding: 16px 20px;
            background: {bg_color};
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            min-height: 50px;
        ">
            <span style="font-weight: 500; font-size: 16px; color: {text_color};">{opt['option_text']}</span>
            <div style="
                width: 24px;
                height: 24px;
                background: #22c55e;
                border-radius: 50%;
                display: {check_display};
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            ">
                <svg width="14" height="14" fill="white" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                </svg>
            </div>
        </div>
        '''

def render_demographic_form(campaign_id: int):
    """Render demographic collection form based on campaign settings"""
    st.markdown("### 📋 ข้อมูลผู้ตอบแบบสำรวจ")
    
    # Get demographics for this campaign
    demographics = get_campaign_demographics(campaign_id)
    
    # If no demographics set for campaign, use all active ones
    if not demographics:
        demographics = get_demographic_attributes(active_only=True)
    
    if not demographics:
        return {}
    
    demographic_data = {}
    
    # Create 2-column layout
    cols = st.columns(2)
    
    for idx, attr in enumerate(demographics):
        col = cols[idx % 2]
        
        with col:
            options = [o['option_text'] for o in attr.get('options', [])]
            
            if attr['input_type'] == 'select' and options:
                value = st.selectbox(
                    attr['label'],
                    options,
                    key=f"demo_{attr['name']}"
                )
            elif attr['input_type'] == 'radio' and options:
                value = st.radio(
                    attr['label'],
                    options,
                    key=f"demo_{attr['name']}",
                    horizontal=True
                )
            else:
                value = st.text_input(
                    attr['label'],
                    key=f"demo_{attr['name']}"
                )
            
            demographic_data[attr['label']] = value
    
    return demographic_data

def render_voter_app(campaign_id: int):
    """Main voter interface"""
    campaign = get_campaign(campaign_id)
    
    if not campaign:
        st.error("❌ ไม่พบแคมเปญ")
        return
    
    # Header
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #1e40af; margin-bottom: 8px;">🗳️ {campaign['title']}</h1>
        <p style="color: #6b7280; font-size: 14px;">{campaign.get('description', '')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if already voted (using session state)
    if st.session_state.get(f'voted_{campaign_id}'):
        st.success("✅ ขอบคุณที่ร่วมตอบแบบสำรวจ!")
        st.balloons()
        
        # Show response count
        count = get_response_count(campaign_id)
        st.info(f"📊 ขณะนี้มีผู้ตอบแบบสำรวจแล้ว {count} คน")
        return
    
    # Initialize session state for answers
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    
    # Demographic form
    with st.expander("📋 ข้อมูลผู้ตอบแบบสำรวจ", expanded=True):
        demographic_data = render_demographic_form(campaign_id)
    
    st.markdown("---")
    
    # Get questions
    questions = get_questions(campaign_id)
    
    if not questions:
        st.warning("⚠️ ยังไม่มีคำถามในแคมเปญนี้")
        return
    
    # Render each question
    for q_idx, question in enumerate(questions):
        st.markdown(f"### ❓ คำถามที่ {q_idx + 1}")
        st.markdown(f"**{question['question_text']}**")
        
        q_type = question['question_type']
        max_sel = question.get('max_selections', 1)
        
        if q_type == 'multi':
            st.caption(f"เลือกได้สูงสุด {max_sel} ข้อ")
        
        # Initialize answer for this question
        q_key = f"q_{question['id']}"
        if q_key not in st.session_state.answers:
            st.session_state.answers[q_key] = [] if q_type == 'multi' else None
        
        # Render options
        options = question.get('options', [])
        
        # Always use single column layout - 25/75 layout is inside the card
        for opt_idx, opt in enumerate(options):
            # Check if selected
            current_answers = st.session_state.answers.get(q_key, [])
            if q_type == 'multi':
                is_selected = opt['id'] in current_answers
            else:
                is_selected = current_answers == opt['id']
            
            # Render card HTML
            card_html = render_card_html(opt, is_selected, q_type)
            st.markdown(card_html, unsafe_allow_html=True)
            
            # Add marker for CSS
            st.markdown('<div class="btn-marker-small"></div>', unsafe_allow_html=True)
            
            # Invisible button
            if st.button("เลือก", key=f"btn_{question['id']}_{opt['id']}", use_container_width=True):
                if q_type == 'multi':
                    current = st.session_state.answers.get(q_key, [])
                    if opt['id'] in current:
                        current.remove(opt['id'])
                    elif len(current) < max_sel:
                        current.append(opt['id'])
                    st.session_state.answers[q_key] = current
                else:
                    st.session_state.answers[q_key] = opt['id']
                st.rerun()
        
        st.markdown("---")
    
    # Submit button
    st.markdown("### 📤 ส่งคำตอบ")
    
    # Validate answers
    all_answered = True
    for question in questions:
        q_key = f"q_{question['id']}"
        answer = st.session_state.answers.get(q_key)
        if answer is None or (isinstance(answer, list) and len(answer) == 0):
            all_answered = False
            break
    
    if not all_answered:
        st.warning("⚠️ กรุณาตอบคำถามให้ครบทุกข้อ")
    
    if st.button("✅ ยืนยันส่งคำตอบ", type="primary", use_container_width=True, disabled=not all_answered):
        # Collect data
        ip_address = get_ip_address()
        location_data = get_location_data(ip_address)
        
        # Get user agent
        try:
            user_agent = st.context.headers.get("User-Agent", "")
        except:
            user_agent = ""
        
        # Format answers
        answers = {}
        for question in questions:
            q_key = f"q_{question['id']}"
            answer = st.session_state.answers.get(q_key)
            if isinstance(answer, list):
                answers[question['id']] = answer
            else:
                answers[question['id']] = [answer] if answer else []
        
        # Submit
        try:
            submit_response(
                campaign_id=campaign_id,
                demographic_data=demographic_data,
                answers=answers,
                ip_address=ip_address,
                user_agent=user_agent,
                location_data=location_data
            )
            
            # Mark as voted
            st.session_state[f'voted_{campaign_id}'] = True
            st.session_state.answers = {}
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
