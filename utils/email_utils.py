import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

EMAIL_ADDRESS = os.getenv("SMTP_EMAIL")
EMAIL_PASSWORD = os.getenv("SMTP_PASSWORD")
logger = logging.getLogger(__name__)

def send_email(recipient, subject, message_body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['Reply-To'] = EMAIL_ADDRESS

    msg.attach(MIMEText(message_body, 'html'))
    logger.info(f"Attempting to send email to {recipient} with subject: {subject}")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Error sending email to {recipient}: {str(e)}", exc_info=True)
        return False


def send_email_with_attachment(recipient, subject, message_body, attachment_path):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['Reply-To'] = EMAIL_ADDRESS
    msg.attach(MIMEText(message_body, 'html'))

    # Attach file
    try:
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=Path(attachment_path).name)
            part['Content-Disposition'] = f'attachment; filename="{Path(attachment_path).name}"'
            msg.attach(part)
    except Exception as e:
        logger.error(f"Failed to attach file: {e}", exc_info=True)
        return False

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email with attachment sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Error sending email with attachment to {recipient}: {str(e)}", exc_info=True)
        return False


def build_email_body(recipient_email: str, subject_type: str, link: str = "", context_name: str = "") -> str:
    title = {
        "board": "",
        "task": "",
        "task-completed": "A Task Has Been Completed",
        "removed": f"",
        "unassigned": f"",
        "welcome": "Welcome to Task Manager!",
        "account_deleted": "",
        "invite": "",
    }.get(subject_type, "Notification")

    action_text = {
        "board": "View Board",
        "task": "View Task",
        "task-completed": "View Board",
        "welcome": "",
        "removed": "",
        "account_deleted": "",
        "invite": "Join Board",
    }.get(subject_type, "View")

    message = {
        "board": "You have been added to a board on the <strong>Task Management System</strong>.",
        "task": "You have been assigned a new task on the <strong>Task Management System</strong>.",
        "task-completed": "A task on your board was marked as <strong>completed</strong>.",
        "removed": f"You have been removed from the board <strong>{context_name}</strong>.",
        "unassigned": f"You have been unassigned from a task on the board <strong>{context_name}</strong>.",
        "welcome": "Thank you for registering with the <strong>Task Manager Application</strong>. We are glad to have you on board!",
        "account_deleted": "Your account and all associated data have been permanently deleted from the <strong>Task Management System</strong>. We are sorry to see you go.<br><br>A copy of your exported data is attached with this email.",
        "invite": f"You have been invited to join the board <strong>{context_name}</strong> on the <strong>Task Management System</strong>.<br>If you are interested, click below to view or join."
    }.get(subject_type, "Please check your dashboard.")

    link_section = f"""
        <p style="font-size: 16px; color: #495057;">
            Click the button below to {action_text.lower()}:
        </p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{link}" style="background-color: #101210; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; display: inline-block;">
                {action_text}
            </a>
        </p>
    """ if link and action_text else ""

    return f"""
    <html>
    <body style="font-family: Times New Roman, Arial, sans-serif; padding: 10px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; border: 1px solid #ddd; box-shadow: 0 2px 6px rgba(0,0,0,0.05); padding: 20px;">
        <h2 style="color: #343a40;">{title}</h2>
        <p style="font-size: 16px; color: #495057;">
            Hello {recipient_email},<br><br>
            {message}
        </p>
        {link_section}
        <hr style="border: none; border-top: 1px solid #e9ecef; margin: 20px 0;">
        <p style="font-size: 14px; color: #868e96;">
            If you did not expect this email, you can ignore it.
        </p>
        <p style="font-size: 14px; color: #868e96;">
            Regards,<br>Task Manager Team
        </p>
        </div>
    </body>
    </html>
    """