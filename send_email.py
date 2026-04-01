#!/usr/bin/env python3
"""
Send email notification using SendGrid API
Reads the output log and sends test results
"""

import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_test_results():
    """Send the Selenium test results via email"""
    
    # Get credentials from environment variables (set by GitHub Secrets)
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('FROM_EMAIL', 'anush.avetisyan@wdmarket.lv')
    to_email = os.environ.get('TO_EMAIL', 'anush.avetisyan@wdmarket.lv')
    
    if not sendgrid_api_key:
        print("Error: SENDGRID_API_KEY not set")
        sys.exit(1)
    
    # Read the test output log once
    log_file = 'output.log'
    output_content = ""
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            output_content = f.read()
        # Determine status from last non-empty line (simple heuristic)
        lines = [line.strip() for line in output_content.splitlines() if line.strip()]
        last_line = lines[-1] if lines else ""
        status = "✅ SUCCESS" if "OK" in last_line or "passed" in last_line.lower() else "❌ FAILED"
    else:
        output_content = "No output.log file found"
        status = "⚠️ UNKNOWN"
    
    # Create email content
    subject = f"Hourly Selenium Test Results - {status}"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .status {{ font-size: 18px; font-weight: bold; margin: 10px 0; }}
            .success {{ color: green; }}
            .failed {{ color: red; }}
            .log {{ background: #f4f4f4; padding: 15px; border-radius: 5px; 
                    font-family: monospace; white-space: pre-wrap; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h2>Hourly Selenium Test Results</h2>
        <p><strong>Time:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Status:</strong> 
            <span class="status {'success' if 'SUCCESS' in status else 'failed'}">{status}</span>
        </p>
        <p><strong>Repository:</strong> {os.environ.get('GITHUB_REPOSITORY', 'Unknown')}</p>
        <p><strong>Run ID:</strong> {os.environ.get('GITHUB_RUN_ID', 'Unknown')}</p>
        <div class="log">
            <strong>Test Output:</strong><br>
            {output_content.replace('<', '&lt;').replace('>', '&gt;')}
        </div>
    </body>
    </html>
    """
    
    # Create and send the message
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print(f"Email sent successfully! Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_test_results()
