# utils/activity_utils.py
from firebase_admin import firestore
from flask import session
import logging

# Set up logging
logger = logging.getLogger(__name__)

def add_activity(db, description, user_id=None, user_email=None, board_id=None, board_name=None):
    """
    Add an activity log entry for the current user.
    
    Args:
        db: Firestore database instance
        description: Activity description
        board_id: Optional board ID if activity is related to a board
        board_name: Optional board name if activity is related to a board
    """
    if 'user' not in session and not user_id:
        logger.warning("Attempted to add activity without user in session or user ID")
        return

    try:
        activity_data = {
            'description': description,
            'userId': user_id or session['user']['uid'],
            'userEmail': user_email or session['user']['email'],
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        if board_id:
            activity_data['boardId'] = board_id
        if board_name:
            activity_data['boardName'] = board_name

        db.collection('activity').add(activity_data)
        logger.info(f"Activity added: {description} for user {activity_data['userEmail']}")
    except Exception as e:
        logger.error(f"Error adding activity: {str(e)}", exc_info=True)
