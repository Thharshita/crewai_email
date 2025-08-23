import streamlit as st
import pandas as pd
import re

status_placeholder = st.empty()
table_placeholder = st.empty()

# Initialize results in session state
if 'email_results' not in st.session_state:
    st.session_state.email_results = []
    
# Show initial empty table
if not st.session_state.email_results:
    df = pd.DataFrame(columns=['Email ID', 'Sender Id','Body', 'Category','Label' ,'Starred','Draft'])
    table_placeholder.table(df)
import streamlit as st
import pandas as pd
import re
from customer_mail_handling.logger import logger
status_placeholder = st.empty()
table_placeholder = st.empty()

# Initialize results in session state
if 'email_results' not in st.session_state:
    st.session_state.email_results = []
    
# Show initial empty table
if not st.session_state.email_results:
    df = pd.DataFrame(columns=['Email ID', 'Sender Id','Body', 'Category','Label' ,'Starred','Draft'])
    table_placeholder.table(df)

def step_callback(step):
    try:
        from crewai.agents.parser import AgentAction, AgentFinish
        from crewai.agents.crew_agent_executor import ToolResult
        # Debug: Show what step we're processing
        step_str = str(step)
        
        if isinstance(step, ToolResult):
            result = getattr(step, "result", None)
            logger.info(f"ToolResult: {result}")
            logger.info(f"ToolResult type: {type(result)}")

            # Capture email data from GetUnreadEmailsTool result
            if isinstance(step.result, list) and len(step.result) > 0:
                logger.info(f"result:{result}")
                result = step.result[0] if isinstance(step.result, list) else step.result
                if isinstance(result, dict) and 'email_id' in result and 'body' in result:
                    email_id = result['email_id']
                    body = result['body']
                    sender=result['sender']
                    subject=result['subject']
                
                
                    # Add email row if not exists
                    existing = next((r for r in st.session_state.email_results if r['Email ID'] == email_id), None)
                    if not existing:
                        st.session_state.email_results.append({
                            'Email ID': email_id,
                            'Body': body,
                            'Subject':subject,
                            'Sender':sender,
                            'Category': '',
                            'Draft': '',
                            'Label':'',
                            'Starred':'',
                        })
                        df = pd.DataFrame(st.session_state.email_results)
                        table_placeholder.table(df)

            tool_inp=getattr(step,'tool_input','')
            logger.info(f"tool_inp:{tool_inp}")
            logger.info(type(tool_inp))
                # Handle tool results for draft saving
            if  'body' and 'draft_saved' in str(step.tool_input):
                    tool_inp=dict(tool_inp)
                    email_id = tool_inp['email_id']
               
                    existing = next((r for r in st.session_state.email_results if r['Email ID'] == email_id), None)
                    if existing:
                        existing['Draft'] = tool_inp['body'][:50] + '...'
                        df = pd.DataFrame(st.session_state.email_results)
                        table_placeholder.table(df)
                        status_placeholder.text(f"Draft saved for {email_id}")


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
            elif 'get_cutomer_data' in tool.lower:
                status_placeholder.text("Retrieveing cutomer data....")
        

        
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
                    import json
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
                            if label:
                                existing['Label'] = label
                            if 'starred' in email:
                                existing['Starred'] = starred
                        else:
                            
                            st.session_state.email_results.append({
                                'Email ID': email_id,
                                'Body': '',
                                'Category': category,
                                'Label':label,
                                'Starred': starred,
                                'Draft': ''
                            })
                        
                        # Update table
                        df = pd.DataFrame(st.session_state.email_results)
                        table_placeholder.table(df)
                        
                    
        
        
                            
    except Exception as e:
        status_placeholder.text(f"Processing...")
def step_callback(step):
    try:
        from crewai.agents.parser import AgentAction, AgentFinish
        
        # Debug: Show what step we're processing
        step_str = str(step)
        
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
            elif 'get_cutomer_data' in tool.lower:
                status_placeholder.text("Retrieveing cutomer data....")
        

        # Capture email data from GetUnreadEmailsTool result
        if hasattr(step, 'result') and isinstance(step.result, list) and len(step.result) > 0:
            result = step.result[0] if isinstance(step.result, list) else step.result
            if isinstance(result, dict) and 'email_id' in result and 'body' in result:
                email_id = result['email_id']
                body = result['body']
                sender=result['sender']
                subject=result['subject']
            
            
                # Add email row if not exists
                existing = next((r for r in st.session_state.email_results if r['Email ID'] == email_id), None)
                if not existing:
                    st.session_state.email_results.append({
                        'Email ID': email_id,
                        'Body': body,
                        'Subject':subject,
                        'Sender':sender,
                        'Category': '',
                        'Draft': '',
                        'Label':'',
                        'Starred':'',
                    })
                    df = pd.DataFrame(st.session_state.email_results)
                    table_placeholder.table(df)

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
                    import json
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
                            if label:
                                existing['Label'] = label
                            if 'starred' in email:
                                existing['Starred'] = starred
                        else:
                            
                            st.session_state.email_results.append({
                                'Email ID': email_id,
                                'Body': '',
                                'Category': category,
                                'Label':label,
                                'Starred': starred,
                                'Draft': ''
                            })
                        
                        # Update table
                        df = pd.DataFrame(st.session_state.email_results)
                        table_placeholder.table(df)
                        
                    
        
        # Handle tool results for draft saving
        if hasattr(step, 'result') and 'draft_saved=True' in str(step.result):
            result_str = str(step.result)
            email_id_match = re.search(r'email_id=([^,\s]+)', result_str)
            subject_match = re.search(r'subject=([^,\\\\]+)', result_str)
            
            if email_id_match:
                email_id = email_id_match.group(1)
                draft_text = subject_match.group(1) if subject_match else 'Draft saved'
                
                existing = next((r for r in st.session_state.email_results if r['Email ID'] == email_id), None)
                if existing:
                    existing['Draft'] = draft_text[:50] + '...'
                    df = pd.DataFrame(st.session_state.email_results)
                    table_placeholder.table(df)
                    status_placeholder.text(f"Draft saved for {email_id}")
                            
    except Exception as e:
        status_placeholder.text(f"Processing...")