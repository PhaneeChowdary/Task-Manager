# blueprints/task_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import logging
from utils.auth_utils import login_required
from repositories.board_repository import BoardRepository
from repositories.task_repository import TaskRepository
from utils.activity_utils import add_activity
from firebase_admin import firestore

# Set up logging
logger = logging.getLogger(__name__)

task_bp = Blueprint('task', __name__)

def init_task_routes(db):
    board_repo = BoardRepository(db)
    task_repo = TaskRepository(db)
    
    @task_bp.route('/add-task/<board_id>', methods=['POST'])
    @login_required
    def add_task(board_id):
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form.get('due_date', '')
        assigned_to_ids = request.form.getlist('assigned_to[]')  # Get multiple users
        priority = request.form.get('priority', 'medium')
        
        if not title:
            flash("Task title is required", "warning")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        user_in_board = False
        for user in board_data.get('users', []):
            if user.get('uid') == session['user']['uid']:
                user_in_board = True
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))
        
        # Find assigned users (multiple)
        assigned_users = []
        for user_id in assigned_to_ids:
            if user_id:  # Skip empty selections
                for user in board_data.get('users', []):
                    if user.get('uid') == user_id:
                        assigned_users.append(user)
                        break
        
        task_data = {
            'title': title,
            'description': description,
            'dueDate': due_date,
            'assignedTo': assigned_users,  # Now an array of users
            'priority': priority,
            'completed': False,
            'createdBy': session['user']['uid'],
            'creatorName': session['user'].get('displayName', session['user']['email']),
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }
        
        # Add task to board
        task_repo.add_task(board_id, task_data)
        
        # Add activity log
        add_activity(db=db, description=f"Added task '{title}' to board: {board_data['name']}",
                     user_id=session['user']['uid'], user_email=session['user']['email'],
                     board_id=board_id, board_name=board_data['name'])
        
        flash(f"Task '{title}' has been added", "success")
        return redirect(url_for('board.board', board_id=board_id))

    @task_bp.route('/update-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def update_task(board_id, task_id):
        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        # Check if user is part of the board
        current_user_id = session['user']['uid']
        user_in_board = False
        for user in board_data.get('users', []):
            if user.get('uid') == current_user_id:
                user_in_board = True
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))
        
        # Check if task exists
        task_data = task_repo.get_task(board_id, task_id)
        
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Check if user is the task creator or board owner
        is_task_creator = task_data.get('createdBy') == current_user_id
        is_board_owner = board_data.get('createdBy') == current_user_id
        
        # If user is not task creator or board owner, only allow toggling completion status
        if not (is_task_creator or is_board_owner):
            # Get the completion status from the form
            completed = 'completed' in request.form
            
            # Create limited update data (only completion status)
            update_data = {
                'completed': completed,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'updatedBy': current_user_id,
                'updaterName': session['user'].get('displayName', session['user']['email'])
            }
            
            # Update task with limited permissions
            task_repo.update_task(board_id, task_id, update_data)
            
            # Add activity log
            status_text = "Completed" if completed else "Reopened"
            add_activity(db=db, description=f"{status_text} task '{task_data['title']}' in board: {board_data['name']}",
                        user_id=current_user_id, user_email=session['user']['email'], 
                        board_id=board_id, board_name=board_data['name'])
            
            flash(f"Task '{task_data['title']}' has been {status_text.lower()}", "success")
            return redirect(url_for('board.board', board_id=board_id))
        
        # If the user is the task creator or board owner, allow full update
        # Get form data
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form.get('due_date', '')
        assigned_to_ids = request.form.getlist('assigned_to[]')  # Get multiple assignees
        priority = request.form.get('priority', 'medium')
        completed = 'completed' in request.form
        
        if not title:
            flash("Task title is required", "warning")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Find assigned users (multiple)
        assigned_users = []
        for user_id in assigned_to_ids:
            if user_id:  # Skip empty selections
                for user in board_data.get('users', []):
                    if user.get('uid') == user_id:
                        assigned_users.append(user)
                        break
        
        # Create full update data
        update_data = {
            'title': title,
            'description': description,
            'dueDate': due_date,
            'assignedTo': assigned_users,  # Now an array of users
            'priority': priority,
            'completed': completed,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': current_user_id,
            'updaterName': session['user'].get('displayName', session['user']['email'])
        }
        
        # Update task
        task_repo.update_task(board_id, task_id, update_data)
        
        # Add activity log
        add_activity(db=db, description=f"Updated task '{title}' in board: {board_data['name']}",
                    user_id=current_user_id, user_email=session['user']['email'],
                    board_id=board_id, board_name=board_data['name'])
        
        flash(f"Task '{title}' has been updated", "success")
        return redirect(url_for('board.board', board_id=board_id))


    @task_bp.route('/delete-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def delete_task(board_id, task_id):
        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        # Check if user is in the board
        current_user_id = session['user']['uid']
        user_in_board = False
        user_role = None
        for user in board_data.get('users', []):
            if user.get('uid') == current_user_id:
                user_in_board = True
                user_role = user.get('role')
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "warning")
            return redirect(url_for('dashboard'))
        
        # Check if task exists
        task_data = task_repo.get_task(board_id, task_id)
        
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Check permission: only task creator or board owner can delete tasks
        is_task_creator = task_data.get('createdBy') == current_user_id
        is_board_owner = user_role == 'owner' or board_data.get('createdBy') == current_user_id
        
        if not (is_task_creator or is_board_owner):
            flash("You don't have permission to delete this task", "warning")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Delete task
        task_repo.delete_task(board_id, task_id)
        
        # Add activity log
        add_activity(db=db, description=f"Deleted task '{task_data['title']}' from board: {board_data['name']}",
                    user_id=current_user_id, user_email=session['user']['email'],
                    board_id=board_id, board_name=board_data['name'])
        
        flash(f"Task '{task_data['title']}' has been deleted", "warning")
        return redirect(url_for('board.board', board_id=board_id))

    @task_bp.route('/toggle-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def toggle_task(board_id, task_id):
        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        user_in_board = False
        for user in board_data.get('users', []):
            if user.get('uid') == session['user']['uid']:
                user_in_board = True
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))
        
        # Check if task exists
        task_data = task_repo.get_task(board_id, task_id)
        
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        new_status = not task_data.get('completed', False)
        
        # Update task
        update_data = {
            'completed': new_status,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': session['user']['uid'],
            'updaterName': session['user'].get('displayName', session['user']['email'])
        }
        
        task_repo.toggle_task_completion(board_id, task_id, update_data)
        
        # Add activity log
        status_text = "Completed" if new_status else "Reopened"
        add_activity(db=db, description=f"{status_text} task '{task_data['title']}' in board: {board_data['name']}",
                     user_id=session['user']['uid'], user_email=session['user']['email'],
                     board_id=board_id, board_name=board_data['name'])
        
        flash(f"Task '{task_data['title']}' has been {status_text.lower()}")
        return redirect(url_for('board.board', board_id=board_id))

    @task_bp.route('/add-comment/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def add_comment(board_id, task_id):
        comment_text = request.form.get('comment', '').strip()
        
        if not comment_text:
            flash("Comment cannot be empty", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Verify board and task access
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        user_in_board = False
        for user in board_data.get('users', []):
            if user.get('uid') == session['user']['uid']:
                user_in_board = True
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "warning")
            return redirect(url_for('dashboard'))
        
        # Create comment
        comment_data = {
            'text': comment_text,
            'createdBy': session['user']['uid'],
            'creatorName': session['user'].get('displayName', session['user']['email']),
            'creatorEmail': session['user']['email'],
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        
        # Add comment to task
        task_repo.add_comment(board_id, task_id, comment_data)
        
        # Add activity
        add_activity(db=db, description=f"Added a comment to task in board: {board_data['name']}",
                     user_id=session['user']['uid'], user_email=session['user']['email'],
                     board_id=board_id, board_name=board_data['name'])
        
        flash("Comment added successfully", "success")
        return redirect(url_for('board.board', board_id=board_id))
        
    return task_bp