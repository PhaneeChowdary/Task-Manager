# utils/export_utils.py
import os
import csv
import smtplib
from datetime import datetime
from pathlib import Path
import zipfile
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import json


# Set up logging
logger = logging.getLogger(__name__)

def export_user_data(db, uid: str, email: str) -> str:
    export_dir = Path("exports") / uid
    export_dir.mkdir(parents=True, exist_ok=True)

    # Export boards owned by user
    boards_data = []
    boards_ref = db.collection("boards").where("createdBy", "==", uid).stream()
    for board in boards_ref:
        board_dict = board.to_dict()
        board_dict["id"] = board.id
        
        # Convert any DatetimeWithNanoseconds objects
        for key, value in board_dict.items():
            if hasattr(value, 'timestamp'):  # Check if it's a Firestore timestamp
                board_dict[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                
        boards_data.append(board_dict)
    with open(export_dir / "boards.json", "w") as f:
        json.dump(boards_data, f, indent=2)

    # Export tasks assigned or created by user
    tasks_data = []
    all_boards = db.collection("boards").stream()
    for board in all_boards:
        board_dict = board.to_dict()
        board_id = board.id
        task_ref = db.collection("boards").document(board_id).collection("tasks").stream()
        for task in task_ref:
            task_data = task.to_dict()
            if (
                task_data.get("createdBy") == uid or
                any(u.get("uid") == uid for u in task_data.get("assignedTo", []))
            ):
                task_data["boardId"] = board_id
                task_data["id"] = task.id
                
                # Convert any DatetimeWithNanoseconds objects
                for key, value in task_data.items():
                    if hasattr(value, 'timestamp'):  # Check if it's a Firestore timestamp
                        task_data[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                
                tasks_data.append(task_data)
    with open(export_dir / "tasks.json", "w") as f:
        json.dump(tasks_data, f, indent=2)

    # Export activity logs
    activities_data = []
    activities = db.collection("activity").where("userId", "==", uid).stream()
    for activity in activities:
        activity_data = activity.to_dict()
        activity_data["id"] = activity.id
        
        # Convert any DatetimeWithNanoseconds objects
        for key, value in activity_data.items():
            if hasattr(value, 'timestamp'):  # Check if it's a Firestore timestamp
                activity_data[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
        
        activities_data.append(activity_data)
    with open(export_dir / "activities.json", "w") as f:
        json.dump(activities_data, f, indent=2)

    # Create ZIP
    zip_filename = f"{uid}_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.zip"
    zip_path = Path("exports") / zip_filename
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in export_dir.iterdir():
            zipf.write(file, arcname=file.name)

    # Clean up JSON files after zipping
    for file in export_dir.iterdir():
        file.unlink()
    export_dir.rmdir()

    return str(zip_path)


def export_and_email_user_data(db, user_id, user_email):
    """
    Export user data and email it as a ZIP file.
    
    Args:
        db: Firestore database instance
        user_id: User ID to export data for
        user_email: Email address to send data to
    """
    logger.info(f"Starting data export for user {user_email}")
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"{user_id}_data.zip")

    try:
        # Export Boards and Tasks
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Export boards
            boards = db.collection('boards').where('createdBy', '==', user_id).stream()
            board_data = []
            for board in boards:
                b = board.to_dict()
                b['id'] = board.id
                board_data.append(b)

                # Export tasks
                tasks = db.collection('boards').document(board.id).collection('tasks').stream()
                task_file = os.path.join(temp_dir, f"{board.id}_tasks.csv")
                with open(task_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(['Title', 'Description', 'Completed', 'DueDate'])
                    for task in tasks:
                        t = task.to_dict()
                        writer.writerow([
                            t.get('title'),
                            t.get('description'),
                            t.get('completed'),
                            t.get('dueDate')
                        ])
                zipf.write(task_file, arcname=f"{board.id}_tasks.csv")

            # Export activity
            activities = db.collection('activity').where('userId', '==', user_id).stream()
            activity_file = os.path.join(temp_dir, "activity.csv")
            with open(activity_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(['Description', 'Timestamp'])
                for act in activities:
                    a = act.to_dict()
                    writer.writerow([a.get('description'), a.get('timestamp')])
            zipf.write(activity_file, arcname="activity.csv")

        # Email setup
        SMTP_EMAIL = os.getenv('SMTP_EMAIL')
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = user_email
        msg['Subject'] = "Your Task Management Data Export"

        body = "Attached is a ZIP of your boards, tasks, and activity before account deletion."
        msg.attach(MIMEText(body, 'plain'))

        with open(zip_path, 'rb') as f:
            part = MIMEBase('application', 'zip')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="your_data.zip"')
            msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Successfully sent data export to {user_email}")
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}", exc_info=True)
        raise