cd /Users/charlesparmar/Project/Charles-Fitness-Tracking-Reporting-Function
PYTHONPATH=. .venv/bin/python -c "
from datetime import date
from src.db import get_user_for_report, get_fitness_measurements
from src.decrypt import decrypt_fitness_rows
from src.report import build_report_bytes
from src.email_sender import send_report_email

u = get_user_for_report(1)
r = get_fitness_measurements(1)
d = decrypt_fitness_rows('Jesus@1435cap', u['key_salt'], u['encrypted_data_key'], r)
x = build_report_bytes(d, 'nevergiveup', 1)
display_name = u.get('display_name') or 'User'
safe_name = display_name.replace(' ', '_')
current_date = date.today().strftime('%Y-%m-%d')
filename = f'Fitness_Report_{safe_name}_{current_date}.xlsx'
send_report_email(u['email'], display_name, x, filename)
print('Report sent!')
"