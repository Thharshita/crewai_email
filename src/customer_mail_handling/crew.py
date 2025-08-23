from dotenv import load_dotenv
load_dotenv()
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, before_kickoff
from crewai_tools import FileReadTool,CSVSearchTool
import json
import os
from typing import List, Dict, Any, Callable
from pydantic import SkipValidation
from datetime import date, datetime
from .tools.gmail_tools import GetUnreadEmailsTool, SaveDraftTool, GmailOrganizeTool, CsvRetrieverTool
# , GmailDeleteTool, EmptyTrashTool
# from .tools.slack_tool import SlackNotificationTool
from .tools.date_tools import DateCalculationTool
from .models import CategorizedEmail, OrganizedEmailList, EmailResponseList,EmailResponse, SimpleCategorizedEmail, EmailDetails, SimpleCategorizedEmailList
from customer_mail_handling.logger import logger
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from customer_mail_handling.streamlit_callback import step_callback
# # csv_tool = FileReadTool(file_path='D:\email_handling_crewai\October_Allocation_23.csv')
@CrewBase
class GmailCrewAi():
	"""Crew that processes emails."""
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
	processed_emails=set()
	current_emails=[]


# 	@before_kickoff
# 	def fetch_emails(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
# 		"""Fetch emails before starting the crew and calculate ages."""
# 		logger.info("Fetching emails before starting the crew...")
		
# 		# Get the email limit from inputs
# 		email_limit = inputs.get('email_limit', 5)
# 		logger.info(f"Fetching {email_limit} emails...")
		
# 		# Create the output directory if it doesn't exist
# 		os.makedirs("output", exist_ok=True)
		
# 		# Use the GetUnreadEmailsTool directly
# 		email_tool = GetUnreadEmailsTool()
# 		email_tuples = email_tool._run(limit=email_limit)
# 		logger.info(f"email_tuples:{len(email_tuples)}")
# 		if  not len(email_tuples)>0:raise ValueError("No unread emails found. Stopping execution.")
# 		# thread_info has {
#         #             'message_id': msg.get('Message-ID', ''),
#         #             'in_reply_to': msg.get('In-Reply-To', ''),
#         #             'references': msg.get('References', ''),
#         #             'date': received_date,  # Use standardized date
#         #             'raw_date': date_str,   # Keep original date string
#         #             'email_id': email_id.decode('utf-8')
#         #         }

# 		# ((subject, sender, full_body, email_id.decode('utf-8'), thread_info))
# # 		[
# #     ("Subject 1", "alice@example.com", "Body text...", "12345", {...}),
# #     ("Subject 2", "bob@example.com", "Another body...", "67890", {...}),
# #     ...
# # ]

# 		# Convert email tuples to EmailDetails objects with pre-calculated ages
# 		emails = []
		
# 		today = date.today()
# 		for email_tuple in email_tuples:
# 			email_detail = EmailDetails.from_email_tuple(email_tuple)
# 			logger.info(f"email_detail:{email_detail}")
			
# 			# Calculate age if date is available
# 			if email_detail.date:
# 				try:
# 					email_date_obj = datetime.strptime(email_detail.date, "%Y-%m-%d").date()
# 					email_detail.age_days = (today - email_date_obj).days
# 					logger.info(f"Email date: {email_detail.date}, age: {email_detail.age_days} days")

					
# 				except Exception as e:
# 					logger.info(f"Error calculating age for email date {email_detail.date}: {e}")
# 					email_detail.age_days = None
			
# 			emails.append(email_detail.dict())
		
# 		# Save emails to file
# 		with open('output/fetched_emails.json', 'w') as f:
# 			json.dump(emails, f, indent=2)
		
# 		logger.info(f"Fetched and saved {len(emails)} emails to output/fetched_emails.json")
		
# 		return inputs

	# @traceable
	def pipeline(self):

	    return LLM(
		# model=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region_name=os.getenv('AWS_REGION_NAME'),
		model="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
		)
	
	# @traceable
	def pipeline_sonnet1(self):
	    return LLM(
		# model=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region_name=os.getenv('AWS_REGION_NAME'),
		model="anthropic.claude-3-5-sonnet-20240620-v1:0"
	)
		

	@agent
	def categorizer(self) -> Agent:
		"""The email categorizer agent."""
		return Agent(
			config=self.agents_config['categorizer'],
			tools=[FileReadTool()],
			llm=self.pipeline_sonnet1(),
		
		)

	@agent
	def organizer(self) -> Agent:
		"""The email organization agent."""
		return Agent(
			config=self.agents_config['organizer'],
			tools=[GmailOrganizeTool(), FileReadTool()],
			llm=self.pipeline_sonnet1(),
		)
		
		#.....................................resume
	@agent
	def response_generator(self) -> Agent:
		"""The email response generator agent."""
		return Agent(
			config=self.agents_config['response_generator'],
			tools=[FileReadTool(),CsvRetrieverTool(),SaveDraftTool()],
			max_iter=1,
			llm=self.pipeline(),

		)

	    
	# @agent
	# def notifier(self) -> Agent:
	# 	"""The email notification agent."""
	# 	return Agent(
	# 		config=self.agents_config['notifier'],
	# 		tools=[SlackNotificationTool()],
	# 		llm=self.llm,
	# 	)

	# @agent
	# def cleaner(self) -> Agent:
	# 	"""The email cleanup agent."""
	# 	return Agent(
	# 		config=self.agents_config['cleaner'],
	# 		tools=[GmailDeleteTool(), EmptyTrashTool()],
	# 		llm=self.llm,
	# 	)

	@task
	def categorization_task(self) -> Task:
		"""The email categorization task."""
		return Task(
			config=self.tasks_config['categorization_task'],
			output_pydantic=SimpleCategorizedEmailList
		)
	
	@task
	def organization_task(self) -> Task:
		"""The email organization task."""
		return Task(
			config=self.tasks_config['organization_task'],
			output_pydantic=OrganizedEmailList,
		)

	@task
	def response_task(self) -> Task:
		"""The email response task."""
		return Task(
			config=self.tasks_config['response_task'],
			output_pydantic=EmailResponseList,
		)
	
	# @task
	# def notification_task(self) -> Task:
	# 	"""The email notification task."""
	# 	return Task(
	# 		config=self.tasks_config['notification_task'],
	# 		output_pydantic=SlackNotification,
	# 	)

	# @task
	# def cleanup_task(self) -> Task:
	# 	"""The email cleanup task."""
	# 	return Task(
	# 		config=self.tasks_config['cleanup_task'],
	# 		output_pydantic=EmailCleanupInfo,
	# 	)

	@crew
	def crew(self) -> Crew:
		"""Creates the email processing crew."""
		return Crew(
			agents=self.agents,
			tasks=self.tasks,
			step_callback=step_callback,
			process=Process.sequential,
			verbose=True,
			max_execution_time=600  # 10 minutes timeout
		)

	


# @CrewBase
# class GmailCrewAi():
#     """Crew that processes emails."""
#     agents_config = 'config/agents.yaml'
#     tasks_config = 'config/tasks.yaml'
#     processed_emails = set()  # Track processed email IDs
#     current_emails = []
#     llm = LLM(
#         aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
#         aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
#         aws_region_name=os.getenv('AWS_REGION_NAME'),
#         model="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
#     )
    

#     @before_kickoff
#     def fetch_emails(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
#         """Fetch emails before starting the crew and calculate ages."""
#         logger.info("Fetching emails before starting the crew...")
        
#         # Get the email limit from inputs
#         email_limit = inputs.get('email_limit', 5)
#         logger.info(f"Fetching {email_limit} emails...")
        
#         # Create the output directory if it doesn't exist
#         os.makedirs("output", exist_ok=True)
        
#         # Use the GetUnreadEmailsTool directly
#         email_tool = GetUnreadEmailsTool()
#         email_tuples = email_tool._run(limit=email_limit)
#         logger.info(f"email_tuples:{len(email_tuples)}")
#         if not len(email_tuples)>0:
#             raise ValueError("No unread emails found. Stopping execution.")

#         # Convert email tuples to EmailDetails objects with pre-calculated ages
#         emails = []
        
#         today = date.today()
#         for email_tuple in email_tuples:
#             email_detail = EmailDetails.from_email_tuple(email_tuple)
#             logger.info(f"email_detail:{email_detail}")
            
#             # Calculate age if date is available
#             if email_detail.date:
#                 try:
#                     email_date_obj = datetime.strptime(email_detail.date, "%Y-%m-%d").date()
#                     email_detail.age_days = (today - email_date_obj).days
#                     logger.info(f"Email date: {email_detail.date}, age: {email_detail.age_days} days")
#                 except Exception as e:
#                     logger.info(f"Error calculating age for email date {email_detail.date}: {e}")
#                     email_detail.age_days = None
            
#             emails.append(email_detail.dict())
        
#         # Save emails to file
#         with open('output/fetched_emails.json', 'w') as f:
#             json.dump(emails, f, indent=2)
        
#         logger.info(f"Fetched and saved {len(emails)} emails to output/fetched_emails.json")
        
#         return inputs
    
    

#     @agent
#     def categorizer(self) -> Agent:
#         """The email categorizer agent."""
#         return Agent(
#             config=self.agents_config['categorizer'],
#             tools=[FileReadTool()],
#             llm=self.llm,
#         )

#     @agent
#     def organizer(self) -> Agent:
#         """The email organization agent."""
#         return Agent(
#             config=self.agents_config['organizer'],
#             tools=[GmailOrganizeTool(), FileReadTool()],
#             llm=self.llm,
#         )
        
#     @agent
#     def response_generator(self) -> Agent:
#         """The email response generator agent."""
#         return Agent(
#             config=self.agents_config['response_generator'],
#             tools=[FileReadTool(), CsvRetrieverTool(), SaveDraftTool()],
#             llm=self.llm,
#             step_callback=self._check_processed
#         )

#     def _check_processed(self, step_output):
#         """Skip already processed emails."""
#         if hasattr(step_output, 'email_id'):
#             return step_output.email_id not in self.processed_emails
#         return True

#     def _mark_as_processed(self, output):
#         """Mark emails as processed after successful response."""
#         if hasattr(output, 'email_id'):
#             self.processed_emails.add(output.email_id)

#     @task
#     def categorization_task(self) -> Task:
#         """The email categorization task."""
#         return Task(
#             config=self.tasks_config['categorization_task'],
#             output_pydantic=SimpleCategorizedEmailList
#         )
    
#     @task
#     def organization_task(self) -> Task:
#         """The email organization task."""
#         return Task(
#             config=self.tasks_config['organization_task'],
#             output_pydantic=OrganizedEmailList,
#         )

#     @task
#     def response_task(self) -> Task:
#         """The email response task."""
#         return Task(
#             config=self.tasks_config['response_task'],
#             output_pydantic=EmailResponse,
#             callback=lambda output: self._mark_as_processed(output)
#         )

#     @crew
#     def crew(self) -> Crew:
#         """Creates the email processing crew."""
#         return Crew(
# 			agents=self.agents,
# 			tasks=self.tasks,
# 			process=Process.sequential,
# 			verbose=True
# 		)