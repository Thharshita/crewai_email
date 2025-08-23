import sys
import warnings
from dotenv import load_dotenv
from customer_mail_handling.logger import logger

# import litellm
# litellm._turn_on_debug()

warnings.filterwarnings("ignore", message=".*not a Python type.*")
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

from customer_mail_handling.crew import GmailCrewAi
from .tools.gmail_tools import GetUnreadEmailsTool, SaveDraftTool, GmailOrganizeTool, CsvRetrieverTool

import os, json
import streamlit as st
# Ensure output folder exists
os.makedirs("output", exist_ok=True)

def run():
    """Run the Gmail Crew AI one email at a time."""
    try:
        load_dotenv()
        st.write("📬 Fetching unread emails...")

        # Step 1: Get all unread emails first
        from customer_mail_handling.tools.gmail_tools import GetUnreadEmailsTool
        from customer_mail_handling.models import EmailDetails
        import json
        from datetime import date, datetime

        logger.info("Fetching all unread emails...")
        email_tool = GetUnreadEmailsTool()
        email_tuples = email_tool._run(limit=500)  # Fetch up to 500 unread emails

        if not email_tuples:
            logger.info("No unread emails found.")
            st.warning("No unread emails found.")
            return 0

        logger.info(f"Found {len(email_tuples)} unread emails.")

        today = date.today()

        # Step 2: Loop through each email and process individually
        for idx, email_tuple in enumerate(email_tuples, start=1):
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
            with open('output/fetched_emails.json', 'w') as f:
                json.dump([email_detail.dict()], f, indent=2)

            # Step 3: Run the crew for this single email
            crew = GmailCrewAi().crew()
            result = crew.kickoff(inputs={'email_limit': 1})
            logger.info(crew.usage_metrics)

            logger.info(f"✅ Finished processing email {idx}/{len(email_tuples)}")
            logger.debug(f"Result: {result}")

        logger.info("\n🎉 All emails processed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run())  # Use the return value as the exit code