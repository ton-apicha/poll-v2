"""
SuperPoll - Professional Field Operations Polling System
Main application entry point
"""
import streamlit as st
import os
from pathlib import Path

# Import modules
from core.database import init_db, get_campaign
from views.voter_ui import render_voter_app
from views.admin_ui import render_admin_app

# Page configuration
st.set_page_config(
    page_title="SuperPoll",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
def load_css():
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def main():
    # Initialize database
    init_db()
    
    # Load CSS
    load_css()
    
    # Get URL parameters
    query_params = st.query_params
    
    # Route based on parameters
    if "poll" in query_params:
        # Voter mode - ?poll=<campaign_id>
        try:
            campaign_id = int(query_params["poll"])
            campaign = get_campaign(campaign_id)
            if campaign and campaign['is_active']:
                render_voter_app(campaign_id)
            else:
                st.error("❌ ไม่พบโพลที่เปิดใช้งาน")
        except (ValueError, TypeError):
            st.error("❌ รหัสโพลไม่ถูกต้อง")
    else:
        # Admin mode - no parameters
        render_admin_app()

if __name__ == "__main__":
    main()
