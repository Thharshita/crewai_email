# Email Handling CrewAI

AI-powered email automation system for debt recovery and customer communication using CrewAI and AWS Bedrock.

## Overview


https://github.com/user-attachments/assets/85d2fa59-77e5-4116-8334-78a427c93b01




Automated email processing system that categorizes, organizes, and generates personalized responses to customer emails regarding loan EMI payments. Uses multi-agent AI architecture with AWS Claude models.

## Features

- **Email Categorization**: Automatically categorizes emails (LOAN_EMI_PAID, WILL_PAY, UNABLE_TO_PAY, SETTLEMENT_REQUEST, OTHER)
- **Priority Assignment**: Assigns priority levels (HIGH, MEDIUM, LOW) based on content
- **Gmail Organization**: Applies labels and stars to emails automatically
- **Personalized Responses**: Generates context-aware draft responses using customer loan data
- **Thread Management**: Handles email threads and conversation history
- **Streamlit UI**: Web interface for monitoring email processing

## Architecture

### Agents
- **Categorizer**: Analyzes email content and assigns categories/priorities
- **Organizer**: Applies Gmail labels and stars based on categorization
- **Response Generator**: Creates personalized draft responses using customer data

### Tasks
1. **Categorization Task**: Reads unread emails and categorizes them
2. **Organization Task**: Applies Gmail organizational features
3. **Response Task**: Generates and saves draft responses

## Prerequisites

- Python 3.10-3.12
- Gmail account with App Password enabled
- AWS account with Bedrock access
- Customer data CSV file

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create `.env` file:

```env
EMAIL_ADDRESS=your-email@gmail.com
APP_PASSWORD=your-gmail-app-password
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION_NAME=us-east-1
```

Update CSV path in `tools/gmail_tools.py`:
```python
df = pd.read_csv("path/to/your/customer_data.csv")
```

## Usage

### Command Line
```bash
# Run email processor
python -m customer_mail_handling.main

# Or use project script
gmail_crew_ai
```

### Streamlit UI
```bash
streamlit run streamlit_app.py
```

## Project Structure

```
src/customer_mail_handling/
├── config/
│   ├── agents.yaml          # Agent configurations
│   └── tasks.yaml           # Task definitions
├── tools/
│   ├── gmail_tools.py       # Gmail integration tools
│   ├── date_tools.py        # Date calculation utilities
│   └── __init__.py
├── crew.py                  # CrewAI setup
├── main.py                  # Entry point
├── models.py                # Pydantic models
├── logger.py                # Logging configuration
└── streamlit_callback.py    # Streamlit integration
```

## Email Categories

- **LOAN_EMI_PAID**: Customer confirms payment
- **WILL_PAY**: Customer commits to pay
- **UNABLE_TO_PAY**: Customer cannot pay
- **SETTLEMENT_REQUEST**: Customer requests settlement
- **OTHER**: Miscellaneous emails

## Labels Applied

- `POSITIVE_CUSTOMER`: For WILL_PAY emails
- `NEGATIVE_CUSTOMER`: For UNABLE_TO_PAY emails
- `SETTLEMENT_REQUEST`: For settlement requests (starred)
- `PAID`: For LOAN_EMI_PAID emails

## Output Files

All outputs saved to `output/` directory:
- `fetched_emails.json`: Retrieved unread emails
- `categorization_report.json`: Categorization results
- `organization_report.json`: Organization results

## AWS Models Used

- **Claude 3.5 Sonnet v2**: Response generation
- **Claude 3.5 Sonnet v1**: Categorization and organization

## Development

### Adding New Tools
1. Create tool class in `tools/`
2. Inherit from `BaseTool` or `GmailToolBase`
3. Implement `_run()` method
4. Add to agent configuration

### Modifying Agents
Edit `config/agents.yaml` to adjust:
- Role descriptions
- Goals
- Backstories

### Modifying Tasks
Edit `config/tasks.yaml` to adjust:
- Task descriptions
- Expected outputs
- Context dependencies

