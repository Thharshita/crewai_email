import streamlit as st
import pandas as pd
import re
import json
from customer_mail_handling.logger import logger

# Configure page for dark mode and wide layout
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
    .stDataFrame {
        background-color: #262730;
    }
    .stTable {
        background-color: #262730;
    }
    div[data-testid="stTable"] table {
        background-color: #262730;
        color: #fafafa;
    }
    div[data-testid="stTable"] th {
        background-color: #1e1e1e;
        color: #fafafa;
        font-weight: bold;
    }
    div[data-testid="stTable"] td {
        background-color: #262730;
        color: #fafafa;
        max-width: 300px;
        word-wrap: break-word;
    }
    .element-container .stText {
        color: #ffff00 !important;
        padding: 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

status_placeholder = st.empty()
table_placeholder = st.empty()

# Initialize results in session state
if 'email_results' not in st.session_state:
    st.session_state.email_results = []
    
# Show initial empty table
if not st.session_state.email_results:
    df = pd.DataFrame(columns=['Email ID','Sender','Subject','Body', 'Category','Label' ,'Starred','Draft'])
    table_placeholder.dataframe(df, use_container_width=True, height=400)

def step_callback(step):
    try:
        from crewai.agents.parser import AgentAction, AgentFinish
        from crewai.agents.crew_agent_executor import ToolResult
        # Debug: Show what step we're processing
        step_str = str(step)
        
        if isinstance(step, ToolResult):
            raw = getattr(step, "result", None)
            
            # Only process if it's email data (list with email_id)
            if isinstance(raw, str) and '"email_id"' in raw and '[' in raw and len(raw) < 10000:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and len(parsed) > 0 and 'email_id' in parsed[0]:
                        for email in parsed:
                            email_id = email.get("email_id")
                            if not email_id:
                                continue
                                
                            existing = next((r for r in st.session_state.email_results if r['Email ID'] == email_id), None)
                            if not existing:
                                st.session_state.email_results.append({
                                    'Email ID': email_id,
                                    'Sender': email.get("sender", ""),
                                    'Subject': email.get("subject", ""),
                                    'Body': email.get("body", ""),
                                    'Category': '',
                                    'Label': '',
                                    'Starred': '',
                                    'Draft': ''
                                })
                            else:
                                if not existing['Body'] and email.get("body"):
                                    existing['Body'] = email.get("body", "")
                                if not existing['Sender']:
                                    existing['Sender'] = email.get("sender", "")
                                if not existing['Subject']:
                                    existing['Subject'] = email.get("subject", "")
                except:
                    pass

            


        if isinstance(step, AgentAction):
            tool = getattr(step, 'tool', '')
            if 'get_unread_emails' in tool:
                status_placeholder.text("Fetching Email...")
            elif 'categoriz' in tool.lower():
                status_placeholder.text("Categorizer Agent Running...")
            elif 'organiz' in tool.lower():
                status_placeholder.text("Organizer Agent Running...")
            elif 'save_email_draft' in tool:
                status_placeholder.text("Response Generator Running...")
            elif 'get_customer_data' in tool.lower():
                status_placeholder.text("Retrieving customer data...")



        
        elif isinstance(step, AgentFinish):
            output = getattr(step, 'output', None)
            status_placeholder.text(f"Agent Finished - Processing output...")
            
            if output:
                # Try to parse as dict first
                if hasattr(output, 'dict'):
                    data = output.dict()
                elif hasattr(output, 'model_dump'):
                    data = output.model_dump()
                else:
                    # Try to parse string output
                    try:
                        data = json.loads(str(output))
                    except:
                        data = {}
                
                # Process email data
                if 'emails' in data:
                    for email in data['emails']:
                        email_id = email.get('email_id')
                        subject = email.get('subject', '')
                        sender=email.get('sender','')
                        category = email.get('category', '')
                        label= email.get('applied_labels','')
                        starred=email.get('starred','')
                        
                        # Find existing row or create new
                        existing = next((r for r in st.session_state.email_results if r['Email ID'] == email_id), None)
                        
                        if existing:
                            if category:
                                existing['Category'] = category
                            if label:
                                existing['Label'] = str(label)
                            if 'starred' in email:
                                existing['Starred'] = str(starred)
                        else:
                            st.session_state.email_results.append({
                                'Email ID': email_id,
                                'Sender': sender,
                                'Subject': subject,
                                'Body': '',
                                'Category': category,
                                'Label': str(label),
                                'Starred': str(starred),
                                'Draft': ''
                            })
                        
        # Handle draft body from AgentAction tool_input  
        if isinstance(step, AgentAction) and 'save_email_draft' in getattr(step, "tool", ""):
            tool_inp = getattr(step, "tool_input", "")
            logger.info(f"Draft tool_input: {tool_inp}")
            
            try:
                if isinstance(tool_inp, str):
                    tool_data = json.loads(tool_inp)
                else:
                    tool_data = tool_inp
                    
                email_id = tool_data.get("email_id")
                body = tool_data.get("body", "")
                
                if email_id:
                    existing = next((r for r in st.session_state.email_results if r["Email ID"] == email_id), None)
                    if existing:
                        existing["Draft"] = body
                        logger.info(f"Draft set: {existing['Draft']}")
            except Exception as e:
                logger.info(f"Draft error: {e}")

        # Refresh table with better formatting
        if st.session_state.email_results:
            df = pd.DataFrame(st.session_state.email_results)
            # Configure column widths
            column_config = {
                "Email ID": st.column_config.TextColumn("Email ID", width="small"),
                "Sender": st.column_config.TextColumn("Sender", width="medium"),
                "Subject": st.column_config.TextColumn("Subject", width="medium"),
                "Body": st.column_config.TextColumn("Body", width="large"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Label": st.column_config.TextColumn("Label", width="small"),
                "Starred": st.column_config.TextColumn("Starred", width="small"),
                "Draft": st.column_config.TextColumn("Draft", width="large")
            }
            table_placeholder.dataframe(df, use_container_width=True, height=400, column_config=column_config)
        else:
            table_placeholder.info("No emails to display")
                    
        
        
                            
    except Exception as e:
        status_placeholder.text(f"Processing...")