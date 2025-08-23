from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import time
from customer_mail_handling.logger import logger

class DateCalculationSchema(BaseModel):
    """Schema for DateCalculationTool input."""
    email_date: str = Field(..., description="Email date in ISO format (YYYY-MM-DD)")
    # Remove reference_date from schema to prevent agent from using it
    # reference_date: Optional[str] = Field(None, description="Reference date in ISO format (YYYY-MM-DD). Defaults to today.")

class DateCalculationTool(BaseTool):
    """Tool to calculate the age of an email in days."""
    name: str = "calculate_email_age"
    description: str = "Calculate how many days old an email is compared to today's date"
    args_schema: type[BaseModel] = DateCalculationSchema

    def _run(self, email_date: str, reference_date: Optional[str] = None) -> str:
        """Calculate the age of an email in days compared to today.
        
        Args:
            email_date: The date of the email in YYYY-MM-DD format
            
        Returns:
            A string with the email age information
        """
        try:
            # Parse the email date
            email_date_obj = datetime.strptime(email_date, "%Y-%m-%d").date()
            
            # Always use today's date - ignore any provided reference_date
            today = date.today()
            
            # Calculate the age in days
            age_days = (today - email_date_obj).days
            
            # Create the response
            response = f"Email age: {age_days} days from today ({today})\n"
            response += f"Email date: {email_date_obj}\n"
            response += f"- Less than 5 days old: {'Yes' if age_days < 5 else 'No'}\n"
            response += f"- Older than 7 days: {'Yes' if age_days > 7 else 'No'}\n"
            response += f"- Older than 10 days: {'Yes' if age_days > 10 else 'No'}\n"
            response += f"- Older than 14 days: {'Yes' if age_days > 14 else 'No'}\n"
            response += f"- Older than 30 days: {'Yes' if age_days > 30 else 'No'}\n"
            
            return response
            
        except Exception as e:
            return f"Error calculating email age: {str(e)}" 