import imaplib
import email
from email.header import decode_header
from typing import List, Tuple, Literal, Optional, Type, Dict, Any
import re
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
import os,json
from pydantic import BaseModel, Field
from crewai.tools import tool
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import pandas as pd
from customer_mail_handling.logger import logger
# (like a subject or sender name).

def decode_header_safe(header):
    """
    Safely decode email headers that might contain encoded words or non-ASCII characters.
    """
    if not header:
        return ""
    
    try:
        decoded_parts = []
        for decoded_str, charset in decode_header(header):
            if isinstance(decoded_str, bytes):
                if charset:
                    decoded_parts.append(decoded_str.decode(charset or 'utf-8', errors='replace'))
                else:
                    decoded_parts.append(decoded_str.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(str(decoded_str))
        return ' '.join(decoded_parts)
    except Exception as e:
        # Fallback to raw header if decoding fails
        return str(header)

def clean_email_body(email_body: str) -> str:
    """
    Clean the email body by removing HTML tags and excessive whitespace.
    """
    try:
        logger.info(f"clean_email_body:{email_body}")
        soup = BeautifulSoup(email_body, "html.parser")
        text = soup.get_text(separator=" ")  # Get text with spaces instead of <br/>
    except Exception as e:
        logger.info(f"Error parsing HTML: {e}")
        text = email_body  # Fallback to raw body if parsing fails

    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()

    logger.info(f"text:{text}")
    return text

# Handling login with Gmail credentials

# Connecting/disconnecting from Gmail

# Reading messages from an email thread

# Extracting clean text from emails
class GmailToolBase(BaseTool):
    """Base class for Gmail tools, handling connection and credentials."""
    
    class Config:
        arbitrary_types_allowed = True #This allows the class to accept types that Pydantic normally doesn’t accept (like IMAP objects).

    email_address: Optional[str] = Field(None, description="Gmail email address")
    app_password: Optional[str] = Field(None, description="Gmail app password")

    def __init__(self, description: str = ""):
        super().__init__(description=description)
        self.email_address = os.environ.get("EMAIL_ADDRESS")
        self.app_password = os.environ.get("APP_PASSWORD")

        if not self.email_address or not self.app_password:
            raise ValueError("EMAIL_ADDRESS and APP_PASSWORD must be set in the environment.")

    def _connect(self):
        """Connect to Gmail."""
        try:
            logger.info(f"Connecting to Gmail with email: {self.email_address[:3]}...{self.email_address[-8:]}")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.email_address, self.app_password)
            logger.info("Successfully logged in to Gmail")
            return mail
        except Exception as e:
            logger.info(f"Error connecting to Gmail: {e}")
            raise e

    def _disconnect(self, mail):
        """Disconnect from Gmail."""
        try:
            mail.close()
            mail.logout()
            logger.info("Successfully disconnected from Gmail")
        except:
            pass

    def _get_thread_messages(self, mail: imaplib.IMAP4_SSL, msg) -> List[str]:
        """Get all messages in the thread by following References and In-Reply-To headers."""
        logger.info("get_thread_messages")
        thread_messages = []
    
        try:
            # Collect message IDs
            references = msg.get("References", "").split()
            in_reply_to = msg.get("In-Reply-To", "").split()
            message_ids = list(set(references + in_reply_to))
            logger.info(f"message_ids: {message_ids}")
    
            if not message_ids:
                return []
    
            thread_ids = []
            # Safer: loop through each message_id instead of building one long OR query
            for mid in message_ids:
                result, data = mail.search(None, f'HEADER MESSAGE-ID "{mid}"')
                if result == "OK" and data[0]:
                    thread_ids.extend(data[0].split())
    
            logger.info(f"Found {len(thread_ids)} related messages in thread.")
    
            # Fetch each related message
            for thread_id in set(thread_ids):  # Remove duplicates
                result, msg_data = mail.fetch(thread_id, "(RFC822)")
                if result == "OK":
                    thread_msg = email.message_from_bytes(msg_data[0][1])
                    thread_body = self._extract_body(thread_msg)
                    thread_messages.append(thread_body)
    
        except Exception as e:
            logger.error(f"get thread message error:{str}")
    
        return thread_messages

    # def _get_thread_messages(self, mail: imaplib.IMAP4_SSL, msg) -> List[str]:
    #     """Get all messages in the thread by following References and In-Reply-To headers."""
    #     logger.info("get_thread_messages")
    #     thread_messages = []
        
    #     # Get message IDs from References and In-Reply-To headers
    #     references = msg.get("References", "").split()
    #     in_reply_to = msg.get("In-Reply-To", "").split()
    #     message_ids = list(set(references + in_reply_to))  # Remove duplicates
        
    #     if message_ids:
    #         # Search for messages with these Message-IDs
    #         search_criteria = ' OR '.join(f'HEADER MESSAGE-ID "{mid}"' for mid in message_ids)
    #         result, data = mail.search(None, search_criteria)
            
    #         if result == "OK":
    #             thread_ids = data[0].split()
    #             for thread_id in thread_ids:
    #                 result, msg_data = mail.fetch(thread_id, "(RFC822)")
    #                 if result == "OK":
    #                     thread_msg = email.message_from_bytes(msg_data[0][1])
    #                     # Extract body from thread message
    #                     thread_body = self._extract_body(thread_msg)
    #                     thread_messages.append(thread_body)
        
    #     return thread_messages

    def _extract_body(self, msg) -> str:
        """Extract body from an email message."""
        logger.info("extract_body_function")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                # logger.info(f"content_type:{content_type}")
                content_disposition = str(part.get("Content-Disposition"))
                # logger.info(f"content_disposition:{content_disposition}")
                try:
                    email_body = part.get_payload(decode=True).decode()
                    # logger.info(f"email_body:{email_body}")
                except:
                    email_body = ""

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body = email_body
                    break
                elif content_type == "text/html" and "attachment" not in content_disposition:
                    body = clean_email_body(email_body)
        else:
            try:
                logger.info("inside else")
                body = clean_email_body(msg.get_payload(decode=True).decode())
            except Exception as e:
                body = f"Error decoding body: {e}"
        # logger.info(f"returning body:{body}")
        return body

class GetUnreadEmailsSchema(BaseModel):
    """Schema for GetUnreadEmailsTool input."""
    limit: Optional[int] = Field(
        default=5,
        description="Maximum number of unread emails to retrieve. Defaults to 5.",
        ge=1  # Ensures the limit is greater than or equal to 1
    )

class CsvRetrieverTool(BaseTool):
    """Tool to get customer data from csv file."""
    # metadata fields that are commonly used in tool-based frameworks
    name: str = "get_customer_data" # Used to reference or call the tool in a pipeline or agent.
    description: str = "Gets customer data from csv" #Helping agents decide when to use this tool.
    
    def _run(self,sender_email_list:list) :
        logger.info(f"sender_email_list:{sender_email_list}")
        df = pd.read_csv("D:\email_handling_crewai\October_Allocation_23.csv",low_memory=False)
        responses = []
        for email in sender_email_list:
            record = df[df['EMAILADDRESS'].str.lower() == email.lower()]
            if not record.empty:
                r = record.iloc[0]
                response = {
                    "Customer Name": r["CUSTOMER_NAME"],
                    "Account Number": r["ACCOUNT_NO"],
                    "Product": r["PRODUCT"],
                    "Outstanding Principal": r["Principal"],
                    "Outstanding Amount": r["OUTSTANDING"],
                    "EMI Amount": r["EMI"],
                    "Overdue Amount": r["OVERDUE_AMOUNT"],
                    "DPD": r["DPD"],
                    "Bucket": r["BUCKET"],
                    "Loan Start Date": r["CONTRACT_START_DATE"],
                    "Last Payment Received": r.get("Amount Collected"),
                    "Branch Name": r["BRANCH_NAME"],
                    "Branch City": r["BRANCH_CITY"],
                    "CHARGES":r["CHARGES"],
                    "Contact Info": {
                        "Phone": r["MOBILE_NO"],
                        "Email": r["EMAILADDRESS"],
                        "Address": r["ADDRESS"]
                    }
                }
                responses.append(response)
            else:
                responses.append(f"No records found for {email}")
        return responses


class GetUnreadEmailsTool(GmailToolBase):
    """Tool to get unread emails from Gmail."""
    # metadata fields that are commonly used in tool-based frameworks
    name: str = "get_unread_emails" # Used to reference or call the tool in a pipeline or agent.
    description: str = "Gets unread emails from Gmail" #Helping agents decide when to use this tool.
    args_schema: Type[BaseModel] = GetUnreadEmailsSchema #A pydantic model that defines the innput argument the tool accepts
    
    def _run(self, limit: Optional[int] = None) -> List[Tuple[str, str, str, str, Dict]]:
        mail = self._connect()
        try:
            logger.info("DEBUG: Connecting to Gmail...")
            mail.select("INBOX")
            result, data = mail.search(None, 'UNSEEN')
            
            logger.info(f"DEBUG: Search result: {result}")
            
            if result != "OK":
                logger.info("DEBUG: Error searching for unseen emails")
                return []
            
            email_ids = data[0].split()
        
            logger.info(f"DEBUG: Found {len(email_ids)} unread emails")
            
            if not email_ids:
                logger.info("DEBUG: No unread emails found.")
                return []
            
            email_ids = list(reversed(email_ids))
            email_ids = email_ids[:limit]
            logger.info(f"DEBUG: Processing {len(email_ids)} emails")
            
            emails = []
            for i, email_id in enumerate(email_ids):
                logger.info(f"DEBUG: Processing email {i+1}/{len(email_ids)}")
                result, msg_data = mail.fetch(email_id, "(RFC822)")
                if result != "OK":
                    logger.info(f"Error fetching email {email_id}:{ result}")
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                # logger.info(f"msg:{msg}")

                # Decode headers properly (handles encoded characters)
                subject = decode_header_safe(msg["Subject"])
                logger.info(f"subject:{subject}")
                # if not subject:
                #     subject="Pending EMI status"
                #     logger.info(f"subject:{subject}")
                
                sender = decode_header_safe(msg["From"])
                logger.info(f"sender:{sender}")
                
                # Extract and standardize the date
                date_str = msg.get("Date", "")
                logger.info(f"date_str:{date_str}")
                received_date = self._parse_email_date(date_str)
                logger.info(f"recieved_Date:{received_date}")
                # Get the current message body
                current_body = self._extract_body(msg)
                # logger.info(f"current_body:{current_body}")
                # Get thread messages
                thread_messages = self._get_thread_messages(mail, msg)
                logger.info(f"thread_message:{thread_messages}")
                # Combine current message with thread history
                full_body = "\n\n--- Previous Messages ---\n".join([current_body] + thread_messages)
                # logger.info(f"full_body:{full_body}")
                # Get thread metadata
                thread_info = {
                    'original_subject':subject,
                    'message_id': msg.get('Message-ID', ''),
                    'in_reply_to': msg.get('In-Reply-To', ''),
                    'references': msg.get('References', ''),
                    'date': received_date,  # Use standardized date
                    'raw_date': date_str,   # Keep original date string
                    'email_id': email_id.decode('utf-8')
                }

                # Add a clear date indicator in the body for easier extraction
                full_body = f"EMAIL DATE: {received_date}\n\n{full_body}"
                
                # logger.info the structure of what we're appending
                logger.info(f"DEBUG: Email tuple structure: subject={subject}, sender={sender}, body_length={len(full_body)}, email_id={email_id.decode('utf-8')}, thread_info_keys={thread_info.keys()}")
                
                emails.append((subject, sender, full_body, email_id.decode('utf-8'), thread_info))
            
            logger.info(f"DEBUG: Returning {len(emails)} email tuples")
            return emails
        except Exception as e:
            logger.info(f"DEBUG: Exception in GetUnreadEmailsTool: {str(e)}")
            import traceback
            traceback.logger.info_exc()
            return []
        finally:
            self._disconnect(mail)

    def _parse_email_date(self, date_str: str) -> str:
        """
        Parse email date string into a standardized format.
        Returns ISO format date string (YYYY-MM-DD) or empty string if parsing fails.
        """
        if not date_str:
            return ""
        
        try:
            # Try various date formats commonly found in emails
            # Remove timezone name if present (like 'EDT', 'PST')
            date_str = re.sub(r'\s+\([A-Z]{3,4}\)', '', date_str)
            
            # Parse with email.utils
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            if parsed_date:
                return parsed_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.info(f"Error parsing date '{date_str}': {e}")
        
        return ""

class SaveDraftSchema(BaseModel):
    """Schema for SaveDraftTool input."""
    subject: str = Field(..., description="Email subject assigned by agent")
    body: str = Field(..., description="Email body content assigned by agent")
    recipient: str = Field(..., description="Recipient email address assigned by agent")
    thread_info: Optional[Dict[str, Any]] = Field(None, description="Thread information for replies")
    email_id:str=Field(description="Unique identifier for the email")
    draft_saved:str= Field(default=False,description="Whether the draft is created")
    


class SaveDraftTool(BaseTool):
    """Tool to save an email as a draft using IMAP."""
    name: str = "save_email_draft"
    description: str = "Saves an email as a draft in Gmail"
    args_schema: Type[BaseModel] = SaveDraftSchema

    def _format_body(self, body: str) -> str:
        """Format the email body with signature."""
        # Replace [Your name] or [Your Name] with Harshita Mehta
        body = re.sub(r'\[Your [Nn]ame\]', 'Harshita Mehta', body)
        
        # If no placeholder was found, append the signature
        if '[Your' not in body and '[your' not in body:
            body = f"{body}\n\nBest regards,\nHarshita Mehta"
        
        return body
    
    
    def _connect(self):
        """Connect to Gmail using IMAP."""
        # Get email credentials from environment
        email_address = os.environ.get('EMAIL_ADDRESS')
        app_password = os.environ.get('APP_PASSWORD')
        
        if not email_address or not app_password:
            raise ValueError("EMAIL_ADDRESS or APP_PASSWORD environment variables not set")
        
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        logger.info(f"Connecting to Gmail with email: {email_address[:3]}...{email_address[-10:]}")
        mail.login(email_address, app_password)
        return mail, email_address

    def _disconnect(self, mail):
        """Disconnect from Gmail."""
        try:
            mail.logout()
        except:
            pass

    def _check_drafts_folder(self, mail):
        """Check available mailboxes to find the drafts folder."""
        logger.info("Checking available mailboxes...")
        result, mailboxes = mail.list()
        if result == 'OK':
            drafts_folders = []
            for mailbox in mailboxes:
                if b'Drafts' in mailbox or b'Draft' in mailbox:
                    drafts_folders.append(mailbox.decode())
                    logger.info(f"Found drafts folder: {mailbox.decode()}")
            return drafts_folders
        return []

    def _verify_draft_saved(self, mail, subject, recipient):
        """Verify if the draft was actually saved by searching for it."""
        try:
            # Try different drafts folder names
            drafts_folders = [
                '"[Gmail]/Drafts"', 
                'Drafts',
                'DRAFTS',
                '"[Google Mail]/Drafts"',
                '[Gmail]/Drafts'
            ]
            
            for folder in drafts_folders:
                try:
                    logger.info(f"Checking folder: {folder}")
                    result, _ = mail.select(folder, readonly=True)
                    if result != 'OK':
                        continue
                        
                    # Search for drafts with this subject
                    search_criteria = f'SUBJECT "{subject}"'
                    result, data = mail.search(None, search_criteria)
                    
                    if result == 'OK' and data[0]:
                        draft_count = len(data[0].split())
                        logger.info(f"Found {draft_count} drafts matching subject '{subject}' in folder {folder}")
                        return True, folder
                    else:
                        logger.info(f"No drafts found matching subject '{subject}' in folder {folder}")
                except Exception as e:
                    logger.info(f"Error checking folder {folder}: {e}")
                    continue
                    
            return False, None
        except Exception as e:
            logger.info(f"Error verifying draft: {e}")
            return False, None
    
    
    def _run(self, email_id:str,subject: str, body: str, recipient: str,original_subject: Optional[str]=None, thread_info: Optional[Dict[str, Any]] = None,draft_saved:Optional[bool]=False) -> str:
        try:
            
            logger.info(f"running response generator:{subject,body,recipient,thread_info}")
            logger.info(f"original_subject:{thread_info.get('original_subject')}")
            mail, email_address = self._connect()
  
            # # Check available drafts folders
            # drafts_folders = self._check_drafts_folder(mail)
            # logger.info(f"Available drafts folders: {drafts_folders}")
            
            # Try with quoted folder name first
            drafts_folder = '"[Gmail]/Drafts"'
            logger.info(f"Selecting drafts folder: {drafts_folder}")
            result, _ = mail.select(drafts_folder)
            logger.info(f"result:{result}")
            
            # If that fails, try without quotes
            if result != 'OK':
                drafts_folder = '[Gmail]/Drafts'
                logger.info(f"First attempt failed. Trying: {drafts_folder}")
                result, _ = mail.select(drafts_folder)
                
            # If that also fails, try just 'Drafts'
            if result != 'OK':
                drafts_folder = 'Drafts'
                logger.info(f"Second attempt failed. Trying: {drafts_folder}")
                result, _ = mail.select(drafts_folder)
                
            if result != 'OK':
                return f"Error: Could not select drafts folder. Available folders:"
                
            logger.info(f"Successfully selected drafts folder: {drafts_folder}")
            
            # Format body and add signature
            body_with_signature = self._format_body(body)
            
            # Create the email message
            message = email.message.EmailMessage()
            message["From"] = email_address
            message["To"] = recipient
            # message["Subject"] = subject
            message.set_content(body_with_signature)
            logger.info(f"Created message with subject: {subject}")

            def sanitize_header(header):
                    if header:
                        return header.replace('\r','').replace('\n','').strip('<>')
                    return header

            # Add thread headers if this is a reply
            if thread_info:
                # References header should include all previous message IDs
                #sanitize header
                
                references = []
                
                if thread_info.get('references'):
                    # references.extend(thread_info['references'].split())
                    refs = [sanitize_header(r) for r in thread_info['references'].split()]
                    references.extend(refs)
                
                if thread_info.get('message_id'):
                    clean_message_id= sanitize_header(thread_info['message_id'])
                    references.append(clean_message_id)
                    logger.info(f"in-reply-to:{clean_message_id}")
                    message["In-Reply-To"] = clean_message_id
                
                if references:
                    seen = set()
                    unique_refs = [r for r in references if not (r in seen or seen.add(r))]
                    message["References"] = " ".join(unique_refs)
                    logger.info(f"reference:{message['References']}")
            

                # Make sure subject has "Re: " prefix
                if not subject.lower().startswith('re:'):
                    message["Subject"] = f"Re: {subject}"

                if not thread_info.get('original_subject'):
                    logger.info("here")
                    message["Subject"] = "Re: (no subject)"
                    
                logger.info(f"Added thread information for reply")
            logger.info(f"mess:{message}")
            # Save to drafts
            logger.info(f"Attempting to save draft to {drafts_folder}...")
            date = imaplib.Time2Internaldate(time.time())
            result, data = mail.append(drafts_folder, '\\Draft', date, message.as_bytes())
            
            if result != 'OK':
                return f"Error saving draft: {result}, {data}"
                
            logger.info(f"Draft save attempt result: {result}")
            return f"SaveDraftTool Response: draft_saved={True},\
            recipient= {recipient},\
            subject= {subject},\
            email_id={email_id}"
        

        except Exception as e:
            logger.info(f"Error saving draft:{str(e)}")
            return json.dumps({
            "draft_saved": False,
            "error": str(e)
        })
        finally:
            self._disconnect(mail)

class GmailOrganizeSchema(BaseModel):
    """Schema for GmailOrganizeTool input."""
    email_id: str = Field(..., description="Email ID to organize")
    category: str = Field(..., description="Category assigned by agent (LOAN_EMI_PAID/WILL_PAY/UNABLE_TO_PAY/SETTLEMENT_REQUEST")
    priority: str = Field(..., description="Priority level (HIGH/MEDIUM/LOW)")
    should_star: bool = Field(default=False, description="Whether to star the email")
    labels: List[str] = Field(default_list=[], description="Labels to apply")

class GmailOrganizeTool(GmailToolBase):
    """Tool to organize emails based on agent categorization."""
    name: str = "organize_email"
    description: str = "Organizes emails using Gmail's priority features based on category and priority"
    args_schema: Type[BaseModel] = GmailOrganizeSchema

    def _run(self, email_id: str, category: str, priority: str, should_star: bool = False, labels: List[str] = None) -> str:
        """Organize an email with the specified parameters."""
        logger.info(f"running tool:{email_id,category,priority,should_star,labels}")
        if labels is None:
            # Provide a default empty list to avoid validation errors
            labels = []
        
        logger.info(f"Organizing email {email_id} with category {category}, priority {priority}, star={should_star}, labels={labels}")
        
        mail = self._connect()
        try:
            # Select inbox to ensure we can access the email
            mail.select("INBOX")
            
            # Apply organization based on category and priority
            if category == "SETTLEMENT_REQUEST" and priority == "HIGH":
                # Star the email, settlement
                if should_star:
                    mail.store(email_id, '+FLAGS', '\\Flagged')
                
                # Mark as important
                # mail.store(email_id, '+FLAGS', '\\Important')
                
                # Apply URGENT label if it doesn't exist
                # if "SETTLEMENT_REQUEST" not in labels:
                #     labels.append("URGENT")

            # Apply all specified labels
            for label in labels:
                logger.info(f"label:{label}")
                try:
                    # Create label if it doesn't exist
                    mail.create(label)
                except:
                    pass  # Label might already exist
                
                # Apply label
                try:
                    mail.store(email_id, '+X-GM-LABELS', f'"{label}"')
                except Exception as label_err:
                    logger.info(f"DEBUG: Error applying label '{label}' to email {email_id}: {label_err}")

            return f"Email organized: Starred={should_star}, Labels={labels}"

        except Exception as e:
            return f"Error organizing email: {e}"
        finally:
            self._disconnect(mail)
