POST https://api.github.com/repos/charlesparmar/Charles-Fitness-Tracking-Reporting-Function/actions/workflows/trigger-report.yml/dispatches
Authorization: Bearer <your_github_pat>
Content-Type: application/json

{
  "ref": "main",
  "inputs": {
    "user_id": "1",
    "login_password": "...",
    "report_password": "..."
  }
}