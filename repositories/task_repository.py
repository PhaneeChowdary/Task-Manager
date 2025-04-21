# repositories/task_repository.py
from firebase_admin import firestore
import logging

# Set up logging
logger = logging.getLogger(__name__)

class TaskRepository:
    def __init__(self, db):
        self.db = db
        
    def get_board_tasks(self, board_id):
        """Get all tasks for a specific board"""
        try:
            tasks = []
            tasks_ref = self.db.collection('boards').document(board_id).collection('tasks').stream()
            
            for task in tasks_ref:
                task_data = task.to_dict()
                task_data['id'] = task.id
                tasks.append(task_data)
                
            logger.info(f"Retrieved {len(tasks)} tasks for board {board_id}")
            return tasks
        except Exception as e:
            logger.error(f"Error retrieving tasks for board {board_id}: {str(e)}", exc_info=True)
            return []
            
    def get_task(self, board_id, task_id):
        """Get a specific task by ID"""
        try:
            task_ref = self.db.collection('boards').document(board_id).collection('tasks').document(task_id).get()
            
            if not task_ref.exists:
                logger.warning(f"Task {task_id} not found in board {board_id}")
                return None
                
            task_data = task_ref.to_dict()
            task_data['id'] = task_ref.id
            
            logger.info(f"Retrieved task {task_id} from board {board_id}")
            return task_data
        except Exception as e:
            logger.error(f"Error retrieving task {task_id} from board {board_id}: {str(e)}", exc_info=True)
            return None
            
    def add_task(self, board_id, task_data):
        """Add a new task to a board"""
        try:
            task_ref = self.db.collection('boards').document(board_id).collection('tasks').add(task_data)
            task_id = task_ref[1].id
            
            # Update task count in board
            self.update_task_counts(board_id)
            
            logger.info(f"Added task {task_id} to board {board_id}")
            return task_id
        except Exception as e:
            logger.error(f"Error adding task to board {board_id}: {str(e)}", exc_info=True)
            raise
            
    def update_task(self, board_id, task_id, task_data):
        """Update a task"""
        try:
            self.db.collection('boards').document(board_id).collection('tasks').document(task_id).update(task_data)
            
            # Update task counts in board
            self.update_task_counts(board_id)
            
            logger.info(f"Updated task {task_id} in board {board_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating task {task_id} in board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def delete_task(self, board_id, task_id):
        """Delete a task"""
        try:
            self.db.collection('boards').document(board_id).collection('tasks').document(task_id).delete()
            
            # Update task counts in board
            self.update_task_counts(board_id)
            
            logger.info(f"Deleted task {task_id} from board {board_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting task {task_id} from board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def toggle_task_completion(self, board_id, task_id, update_data):
        """Toggle task completion status"""
        try:
            self.db.collection('boards').document(board_id).collection('tasks').document(task_id).update(update_data)
            
            # Update completed task count in board
            self.update_task_counts(board_id)
            
            logger.info(f"Toggled completion for task {task_id} in board {board_id}")
            return True
        except Exception as e:
            logger.error(f"Error toggling task {task_id} in board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def update_task_counts(self, board_id):
        """Update task count and completed task count in board"""
        try:
            tasks_ref = self.db.collection('boards').document(board_id).collection('tasks').stream()
            task_count = 0
            completed_count = 0
            
            for task in tasks_ref:
                task_count += 1
                if task.to_dict().get('completed', False):
                    completed_count += 1
                    
            self.db.collection('boards').document(board_id).update({
                'taskCount': task_count,
                'completedTaskCount': completed_count
            })
            
            logger.info(f"Updated task counts for board {board_id}: {completed_count}/{task_count}")
            return True
        except Exception as e:
            logger.error(f"Error updating task counts for board {board_id}: {str(e)}", exc_info=True)
            return False
            
    def get_task_comments(self, board_id, task_id):
        """Get comments for a specific task"""
        try:
            comments = []
            comments_ref = self.db.collection('boards').document(board_id).collection('tasks').document(task_id).collection('comments').order_by('createdAt').stream()
            
            for comment in comments_ref:
                comment_data = comment.to_dict()
                comment_data['id'] = comment.id
                comments.append(comment_data)
                
            logger.info(f"Retrieved {len(comments)} comments for task {task_id}")
            return comments
        except Exception as e:
            logger.error(f"Error retrieving comments for task {task_id}: {str(e)}", exc_info=True)
            return []
            
    def add_comment(self, board_id, task_id, comment_data):
        """Add a comment to a task"""
        try:
            comment_ref = self.db.collection('boards').document(board_id).collection('tasks').document(task_id).collection('comments').add(comment_data)
            comment_id = comment_ref[1].id
            
            logger.info(f"Added comment {comment_id} to task {task_id}")
            return comment_id
        except Exception as e:
            logger.error(f"Error adding comment to task {task_id}: {str(e)}", exc_info=True)
            raise