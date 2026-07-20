# PR_1: Telegram Bot for Coffee Shop Automation

## The Problem
The coffee shop spent approximately 2 hours per week on manual report generation, payroll calculations, and attendance tracking, which led to a high risk of human error.

## The Solution
Developed and deployed a production-ready Telegram bot that automates:
- Daily shift and cleaning reminders based on Google Sheets data (subsequently migrated to PostgreSQL).
- Automated payroll statement generation (calculation → PNG generation → scheduled direct messages to employees).
- Real-time KPI visualization: employee punctuality, daily revenue, and compliance with operational standards.

## Tech Stack
- **Python 3.10+**
- **aiogram** - Asynchronous framework for the Telegram Bot API
- **pandas** - Data processing and complex calculations
- **matplotlib** - Graph and PNG image generation
- **gspread_pandas** - Integration with Google Sheets API
- **schedule** - Task scheduling and cron-like jobs

## Project Structure

```markdown
PR_1.Telegram_bot/
  ├── main.py              # Core bot logic and command handlers
  ├── database.py          # Database operations (Google Sheets / PostgreSQL), read/write logic
  ├── requirements.txt     # Project dependencies
  └── README.md            # Project documentation
```

## Key Results
- 83% time reduction on weekly reporting (from 2 hours down to 10 minutes).
- Elimination of manual errors in payroll calculations.
- Full automation of daily operational reminders for the staff.
- Real-time KPI visualization for better management oversight and decision-making.
