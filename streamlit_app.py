# # app.py (root of project)
# import streamlit as st
# from src.customer_mail_handling.main import run
# st.title("📧 Agentic AI Email Processor Demo")

# if st.button("Execute"):
#     run()

import sys
import warnings
from dotenv import load_dotenv
from src.customer_mail_handling.logger import logger
import time

# import litellm
# litellm._turn_on_debug()

warnings.filterwarnings("ignore", message=".*not a Python type.*")
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

import os, json
import streamlit as st
import pandas as pd

# Configure page
st.set_page_config(
    page_title="Email Processor",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark mode CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stButton > button {
        background-color: #262730;
        color: #fafafa;
        border: 1px solid #4a4a4a;
    }
    .stButton > button:hover {
        background-color: #4a4a4a;
        color: #fafafa;
    }
    .stMarkdown {
        color: #fafafa;
    }
    .stSuccess {
        background-color: #1e4d3e;
        color: #fafafa;
    }
    .stWarning {
        background-color: #4d3e1e;
        color: #fafafa;
    }
    .stInfo {
        background-color: #1e3a4d;
        color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

st.title("📧 Agentic AI Email Processor Demo")

# Init session state
if "results" not in st.session_state: st.session_state.results = []
if "status" not in st.session_state: st.session_state.status = ""
if "unread_count" not in st.session_state: st.session_state.unread_count = 0

# ---- Button ----
if st.button("Execute"):
    from customer_mail_handling.tools.gmail_tools import GetUnreadEmailsTool
    from customer_mail_handling.models import EmailDetails
    from customer_mail_handling.crew import GmailCrewAi
    import json
    from datetime import date, datetime
    st.session_state.results = []
    st.session_state.status = "Fetching unread emails..."
    email_tool = GetUnreadEmailsTool()
    email_tuples = email_tool._run(limit=500)

    st.session_state.unread_count = len(email_tuples)
    st.session_state.status = f"{st.session_state.unread_count} unread email{'s' if st.session_state.unread_count != 1 else ''} found."

    if not email_tuples:
            # logger.info("No unread emails found.")
            st.warning("No unread emails found.")
    else:
        # logger.info(f"Found {len(email_tuples)} unread emails.")
        st.success(f"Found {len(email_tuples)} unread emails.")
    
    logger.info(f"Found {len(email_tuples)} unread emails.")

    today = date.today()

    # Step 2: Loop through each email and process individually
    processed_count = 0
    failed_count = 0
    
    for idx, email_tuple in enumerate(email_tuples, start=1):
        try:
            st.session_state.status = f"Processing email {idx}/{len(email_tuples)}..."
            logger.info(f"\n📩 Processing email {idx}/{len(email_tuples)}...")
            
            # Convert to EmailDetails dict for saving
            email_detail = EmailDetails.from_email_tuple(email_tuple)
            if email_detail.date:
                try:
                    email_date_obj = datetime.strptime(email_detail.date, "%Y-%m-%d").date()
                    email_detail.age_days = (today - email_date_obj).days
                except Exception as e:
                    logger.warning(f"Error calculating age for email: {e}")
                    email_detail.age_days = None
            
            # Save only THIS email to fetched_emails.json
            os.makedirs("output", exist_ok=True)
            with open('output/fetched_emails.json', 'w') as f:
                json.dump([email_detail.dict()], f, indent=2)
            
            # Step 3: Run the crew for this single email
            crew = GmailCrewAi().crew()
            result = crew.kickoff(inputs={'email_limit': 1})
            
            processed_count += 1
            st.session_state.status = f"✅ Email {idx}/{len(email_tuples)} processed successfully"
            logger.info(f"✅ Email {idx} processed successfully")
            
        except Exception as e:
            failed_count += 1
            st.session_state.status = f"❌ Email {idx}/{len(email_tuples)} failed: {str(e)[:50]}..."
            logger.error(f"❌ Email {idx} failed: {e}")
            
        if idx < len(email_tuples):
            time.sleep(7)  # 5 second delay


    st.session_state.status = f"✅ Processing complete! {processed_count} successful, {failed_count} failed out of {len(email_tuples)} emails."

# ---- STATUS ----
st.markdown(f"**Status:** {st.session_state.status}")
