# repositories/board_repository.py
from firebase_admin import firestore
import logging

# Set up logging
logger = logging.getLogger(__name__)

class BoardRepository:
    def __init__(self, db):
        self.db = db
        
    def get_user_boards(self, user_id):
        """Get boards created by a specific user"""
        try:
            boards = []
            boards_ref = self.db.collection('boards').where('createdBy', '==', user_id).stream()
            
            for board in boards_ref:
                board_data = board.to_dict()
                board_data['id'] = board.id
                boards.append(board_data)
                
            logger.info(f"Retrieved {len(boards)} boards for user {user_id}")
            return boards
        except Exception as e:
            logger.error(f"Error retrieving user boards: {str(e)}", exc_info=True)
            return []
            
    def get_shared_boards(self, user_id, user_email):
        """Get boards shared with a specific user"""
        try:
            boards = []
            # This is an optimization over your original code
            # Assuming you have a compound index set up for 'users.uid'
            shared_ref = self.db.collection('boards').stream()
            
            for board in shared_ref:
                board_data = board.to_dict()
                board_users = board_data.get('users', [])
                is_member = any(u.get('uid') == user_id or u.get('email') == user_email for u in board_users)
                
                if is_member and board_data['createdBy'] != user_id:
                    board_data['id'] = board.id
                    boards.append(board_data)
                    
            logger.info(f"Retrieved {len(boards)} shared boards for user {user_id}")
            return boards
        except Exception as e:
            logger.error(f"Error retrieving shared boards: {str(e)}", exc_info=True)
            return []
            
    def get_board(self, board_id):
        """Get a specific board by ID"""
        try:
            board_ref = self.db.collection('boards').document(board_id).get()
            
            if not board_ref.exists:
                logger.warning(f"Board {board_id} not found")
                return None
                
            board_data = board_ref.to_dict()
            board_data['id'] = board_ref.id
            
            logger.info(f"Retrieved board {board_id}")
            return board_data
        except Exception as e:
            logger.error(f"Error retrieving board {board_id}: {str(e)}", exc_info=True)
            return None
            
    def create_board(self, board_data):
        """Create a new board"""
        try:
            new_board = self.db.collection('boards').add(board_data)
            board_id = new_board[1].id
            
            logger.info(f"Created board {board_id}")
            return board_id
        except Exception as e:
            logger.error(f"Error creating board: {str(e)}", exc_info=True)
            raise
            
    def update_board(self, board_id, data):
        """Update a board's data"""
        try:
            self.db.collection('boards').document(board_id).update(data)
            logger.info(f"Updated board {board_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def delete_board(self, board_id):
        """Delete a board and its tasks"""
        try:
            # Delete all tasks in the board
            tasks_ref = self.db.collection('boards').document(board_id).collection('tasks').stream()
            for task in tasks_ref:
                task.reference.delete()
                
            # Delete the board
            self.db.collection('boards').document(board_id).delete()
            
            logger.info(f"Deleted board {board_id} with all its tasks")
            return True
        except Exception as e:
            logger.error(f"Error deleting board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def add_user_to_board(self, board_id, user_data):
        """Add a user to a board"""
        try:
            board_ref = self.db.collection('boards').document(board_id).get()
            if not board_ref.exists:
                logger.warning(f"Board {board_id} not found when adding user")
                return False
                
            board_data = board_ref.to_dict()
            board_data['users'].append(user_data)
            
            self.db.collection('boards').document(board_id).update({
                'users': board_data['users']
            })
            
            logger.info(f"Added user {user_data.get('email')} to board {board_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding user to board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def remove_user_from_board(self, board_id, user_id):
        """Remove a user from a board"""
        try:
            board_ref = self.db.collection('boards').document(board_id).get()
            if not board_ref.exists:
                logger.warning(f"Board {board_id} not found when removing user")
                return False
                
            board_data = board_ref.to_dict()
            board_data['users'] = [u for u in board_data['users'] if u.get('uid') != user_id]
            
            self.db.collection('boards').document(board_id).update({
                'users': board_data['users']
            })
            
            logger.info(f"Removed user {user_id} from board {board_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing user from board {board_id}: {str(e)}", exc_info=True)
            return False