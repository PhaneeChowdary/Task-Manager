# repositories/user_repository.py
import logging
from firebase_admin import auth

# Set up logging
logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db):
        self.db = db
        
    def get_user_by_email(self, email):
        """Get a user by email"""
        try:
            user = auth.get_user_by_email(email)
            logger.info(f"Retrieved user with email {email}")
            return user
        except auth.UserNotFoundError:
            logger.warning(f"User with email {email} not found")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user with email {email}: {str(e)}", exc_info=True)
            raise
            
    def get_user_by_id(self, user_id):
        """Get a user by ID"""
        try:
            user = auth.get_user(user_id)
            logger.info(f"Retrieved user with ID {user_id}")
            return user
        except auth.UserNotFoundError:
            logger.warning(f"User with ID {user_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user with ID {user_id}: {str(e)}", exc_info=True)
            raise
            
    def create_user(self, email, password, display_name=None):
        """Create a new user"""
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            logger.info(f"Created user with email {email}")
            return user
        except Exception as e:
            logger.error(f"Error creating user with email {email}: {str(e)}", exc_info=True)
            raise
            
    def update_user(self, user_id, display_name=None):
        """Update a user's profile"""
        try:
            user = auth.update_user(
                user_id,
                display_name=display_name
            )
            logger.info(f"Updated user with ID {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error updating user with ID {user_id}: {str(e)}", exc_info=True)
            raise
            
    def delete_user(self, user_id):
        """Delete a user"""
        try:
            auth.delete_user(user_id)
            logger.info(f"Deleted user with ID {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user with ID {user_id}: {str(e)}", exc_info=True)
            raise