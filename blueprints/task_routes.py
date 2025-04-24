# blueprints/task_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import logging
from utils.auth_utils import login_required
from repositories.board_repository import BoardRepository
from repositories.task_repository import TaskRepository
from utils.activity_utils import add_activity
from firebase_admin import firestore
from utils.email_utils import build_email_body, send_email

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
        assigned_to_ids = request.form.getlist('assigned_to[]')
        priority = request.form.get('priority', 'medium')

        if not title:
            flash("Task title is required", "warning")
            return redirect(url_for('board.board', board_id=board_id))

        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        user_in_board = any(user.get('uid') == current_user_id for user in board_data.get('users', []))
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        # Resolve assigned users
        assigned_users = []
        for user_id in assigned_to_ids:
            if user_id:
                user = next((u for u in board_data.get('users', []) if u.get('uid') == user_id), None)
                if user:
                    assigned_users.append(user)

        task_data = {
            'title': title,
            'description': description,
            'dueDate': due_date,
            'assignedTo': assigned_users,
            'priority': priority,
            'completed': False,
            'createdBy': current_user_id,
            'creatorName': session['user'].get('displayName', session['user']['email']),
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        logger.debug(f"Creating task with createdBy: {current_user_id} ({session['user']['email']})")
        task_repo.add_task(board_id, task_data)

        # Add activity
        add_activity(db=db, description=f"Added task '{title}' to board: {board_data['name']}",
                    user_id=current_user_id, user_email=session['user']['email'],
                    board_id=board_id, board_name=board_data['name'])

        flash(f"Task '{title}' has been added", "success")

        task_link = url_for('board.board', board_id=board_id, _external=True)

        # Send notifications
        for user in assigned_users:
            if user['email'] != session['user']['email']:
                subject = "You have been assigned a task"
                body = build_email_body(user['email'], "task", task_link)
                send_email(user['email'], subject, body)

        return redirect(url_for('board.board', board_id=board_id))


    @task_bp.route('/update-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def update_task(board_id, task_id):
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        current_user_email = session['user']['email']
        user_in_board = any(user.get('uid') == current_user_id for user in board_data.get('users', []))

        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        task_data = task_repo.get_task(board_id, task_id)
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.board', board_id=board_id))

        is_task_creator = task_data.get('createdBy') == current_user_id
        is_board_owner = board_data.get('createdBy') == current_user_id
        task_link = url_for('board.board', board_id=board_id, _external=True)

        # Limited permission: toggle completion only
        if not (is_task_creator or is_board_owner):
            completed = 'completed' in request.form

            # Notify board owner if completed
            if completed:
                board_owner = next((u for u in board_data['users'] if u.get('uid') == board_data.get('createdBy')), None)
                if board_owner and board_owner.get('email') != current_user_email:
                    subject = "A Task Has Been Completed"
                    body = build_email_body(
                        recipient_email=board_owner['email'],
                        subject_type="task_completed",
                        link=task_link,
                        extra_info=task_data.get('title', '')
                    )
                    send_email(board_owner['email'], subject, body)

            update_data = {
                'completed': completed,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'updatedBy': current_user_id,
                'updaterName': session['user'].get('displayName', current_user_email)
            }

            task_repo.update_task(board_id, task_id, update_data)
            status_text = "Completed" if completed else "Reopened"

            add_activity(db=db,
                        description=f"{status_text} task '{task_data['title']}' in board: {board_data['name']}",
                        user_id=current_user_id, user_email=current_user_email,
                        board_id=board_id, board_name=board_data['name'])

            flash(f"Task '{task_data['title']}' has been {status_text.lower()}", "success")
            return redirect(url_for('board.board', board_id=board_id))

        # Full permission update
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form.get('due_date', '')
        assigned_to_ids = request.form.getlist('assigned_to[]')
        priority = request.form.get('priority', 'medium')
        completed = 'completed' in request.form

        if not title:
            flash("Task title is required", "warning")
            return redirect(url_for('board.board', board_id=board_id))

        assigned_users = []
        for user_id in assigned_to_ids:
            user = next((u for u in board_data.get('users', []) if u.get('uid') == user_id), None)
            if user:
                assigned_users.append(user)

        previous_assigned = task_data.get('assignedTo', [])
        previous_user_ids = {u.get('uid') for u in previous_assigned if u.get('uid')}
        new_user_ids = {u.get('uid') for u in assigned_users if u.get('uid')}
        new_assignees = new_user_ids - previous_user_ids
        removed_users = previous_user_ids - new_user_ids

        update_data = {
            'title': title,
            'description': description,
            'dueDate': due_date,
            'assignedTo': assigned_users,
            'priority': priority,
            'completed': completed,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': current_user_id,
            'updaterName': session['user'].get('displayName', current_user_email)
        }

        task_repo.update_task(board_id, task_id, update_data)

        add_activity(db=db,
                    description=f"Updated task '{title}' in board: {board_data['name']}",
                    user_id=current_user_id, user_email=current_user_email,
                    board_id=board_id, board_name=board_data['name'])

        flash(f"Task '{title}' has been updated", "success")

        # Notify new assignees
        for user in assigned_users:
            if user.get('uid') in new_assignees and user.get('email') != current_user_email:
                subject = "You have been assigned a task"
                body = build_email_body(user['email'], "task", task_link)
                send_email(user['email'], subject, body)

        # Notify removed assignees
        for user in previous_assigned:
            if user.get('uid') in removed_users and user.get('email') != current_user_email:
                subject = "You have been unassigned from a task"
                body = build_email_body(
                    recipient_email=user['email'],
                    subject_type="unassigned",
                    link=None,
                    context_name=board_data.get('name', '')
                )
                send_email(user['email'], subject, body)

        return redirect(url_for('board.board', board_id=board_id))
    

    @task_bp.route('/delete-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def delete_task(board_id, task_id):
        # Check board exists
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        user_role = None
        user_in_board = False

        for user in board_data.get('users', []):
            if user.get('uid') == current_user_id:
                user_in_board = True
                user_role = user.get('role')
                break

        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        # Check task exists
        task_data = task_repo.get_task(board_id, task_id)
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.board', board_id=board_id))

        # Check permission: only task creator or board owner can delete
        is_task_creator = task_data.get('createdBy') == current_user_id
        is_board_owner = user_role == 'owner' or board_data.get('createdBy') == current_user_id

        if not (is_task_creator or is_board_owner):
            flash("You don't have permission to delete this task", "warning")
            return redirect(url_for('board.board', board_id=board_id))

        # Delete the task
        task_repo.delete_task(board_id, task_id)

        # Log the deletion
        add_activity(
            db=db,
            description=f"Deleted task '{task_data['title']}' from board: {board_data['name']}",
            user_id=current_user_id,
            user_email=session['user']['email'],
            board_id=board_id,
            board_name=board_data['name']
        )

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

        current_user_id = session['user']['uid']
        current_user_email = session['user']['email']

        # Ensure user is in board (by uid or fallback email)
        user_in_board = any(user.get('uid') == current_user_id for user in board_data.get('users', []))
        if not user_in_board:
            user_in_board = any(user.get('email') == current_user_email for user in board_data.get('users', []))
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        # Check if task exists
        task_data = task_repo.get_task(board_id, task_id)
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.board', board_id=board_id))

        new_status = not task_data.get('completed', False)

        # Update task status
        update_data = {
            'completed': new_status,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': current_user_id,
            'updaterName': session['user'].get('displayName', current_user_email)
        }
        task_repo.toggle_task_completion(board_id, task_id, update_data)

        # Notify board owner if task is completed
        if new_status:
            board_owner = next((u for u in board_data['users'] if u['uid'] == board_data['createdBy']), None)
            if board_owner and board_owner.get('email') != current_user_email:
                task_link = url_for('board.board', board_id=board_id, _external=True)
                subject = "A task was marked as completed"
                body = build_email_body(board_owner['email'], "task-completed", task_link)
                send_email(board_owner['email'], subject, body)

        # Log activity
        status_text = "Completed" if new_status else "Reopened"
        add_activity(
            db=db,
            description=f"{status_text} task '{task_data['title']}' in board: {board_data['name']}",
            user_id=current_user_id,
            user_email=current_user_email,
            board_id=board_id,
            board_name=board_data['name']
        )

        flash(f"Task '{task_data['title']}' has been {status_text.lower()}", "success")
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

        current_uid = session['user']['uid']
        current_email = session['user']['email']

        user_in_board = any(user.get('uid') == current_uid or user.get('email') == current_email for user in board_data.get('users', []))
        if not user_in_board:
            flash("You do not have access to this board", "warning")
            return redirect(url_for('dashboard'))

        # Create comment
        comment_data = {
            'text': comment_text,
            'createdBy': current_uid,
            'creatorName': session['user'].get('displayName', current_email),
            'creatorEmail': current_email,
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        # Add comment to task
        task_repo.add_comment(board_id, task_id, comment_data)

        # Log activity
        add_activity(
            db=db,
            description=f"Added a comment to task in board: {board_data['name']}",
            user_id=current_uid,
            user_email=current_email,
            board_id=board_id,
            board_name=board_data['name']
        )

        flash("Comment added successfully", "success")
        return redirect(url_for('board.board', board_id=board_id))
    

    @task_bp.route('/shared-add-task/<board_id>', methods=['POST'])
    @login_required
    def shared_add_task(board_id):
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form.get('due_date', '')
        assigned_to_ids = request.form.getlist('assigned_to[]')
        priority = request.form.get('priority', 'medium')

        if not title:
            flash("Task title is required", "warning")
            return redirect(url_for('board.shared_board', board_id=board_id))

        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        user_in_board = any(user.get('uid') == current_user_id for user in board_data.get('users', []))
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        # Resolve assigned users
        assigned_users = []
        for user_id in assigned_to_ids:
            if user_id:
                user = next((u for u in board_data.get('users', []) if u.get('uid') == user_id), None)
                if user:
                    assigned_users.append(user)

        task_data = {
            'title': title,
            'description': description,
            'dueDate': due_date,
            'assignedTo': assigned_users,
            'priority': priority,
            'completed': False,
            'createdBy': current_user_id,
            'creatorName': session['user'].get('displayName', session['user']['email']),
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        task_repo.add_task(board_id, task_data)

        # Add activity
        add_activity(db=db, description=f"Added task '{title}' to board: {board_data['name']}",
                    user_id=current_user_id, user_email=session['user']['email'],
                    board_id=board_id, board_name=board_data['name'])

        flash(f"Task '{title}' has been added", "success")

        task_link = url_for('board.shared_board', board_id=board_id, _external=True)

        # Send notifications
        for user in assigned_users:
            if user['email'] != session['user']['email']:
                subject = "You have been assigned a task"
                body = build_email_body(user['email'], "task", task_link)
                send_email(user['email'], subject, body)

        return redirect(url_for('board.shared_board', board_id=board_id))


    @task_bp.route('/shared-update-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def shared_update_task(board_id, task_id):
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        current_user_email = session['user']['email']
        user_in_board = any(user.get('uid') == current_user_id for user in board_data.get('users', []))

        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        task_data = task_repo.get_task(board_id, task_id)
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.shared_board', board_id=board_id))

        is_task_creator = task_data.get('createdBy') == current_user_id
        is_board_owner = board_data.get('createdBy') == current_user_id
        task_link = url_for('board.shared_board', board_id=board_id, _external=True)

        # Limited permission: toggle completion only
        if not (is_task_creator or is_board_owner):
            completed = 'completed' in request.form

            # Notify board owner if completed
            if completed:
                board_owner = next((u for u in board_data['users'] if u.get('uid') == board_data.get('createdBy')), None)
                if board_owner and board_owner.get('email') != current_user_email:
                    subject = "A Task Has Been Completed"
                    body = build_email_body(
                        recipient_email=board_owner['email'],
                        subject_type="task_completed",
                        link=task_link,
                        extra_info=task_data.get('title', '')
                    )
                    send_email(board_owner['email'], subject, body)

            update_data = {
                'completed': completed,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'updatedBy': current_user_id,
                'updaterName': session['user'].get('displayName', current_user_email)
            }

            task_repo.update_task(board_id, task_id, update_data)
            status_text = "Completed" if completed else "Reopened"

            add_activity(db=db,
                        description=f"{status_text} task '{task_data['title']}' in board: {board_data['name']}",
                        user_id=current_user_id, user_email=current_user_email,
                        board_id=board_id, board_name=board_data['name'])

            flash(f"Task '{task_data['title']}' has been {status_text.lower()}", "success")
            return redirect(url_for('board.shared_board', board_id=board_id))

        # Full permission update
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form.get('due_date', '')
        assigned_to_ids = request.form.getlist('assigned_to[]')
        priority = request.form.get('priority', 'medium')
        completed = 'completed' in request.form

        if not title:
            flash("Task title is required", "warning")
            return redirect(url_for('board.shared_board', board_id=board_id))

        assigned_users = []
        for user_id in assigned_to_ids:
            user = next((u for u in board_data.get('users', []) if u.get('uid') == user_id), None)
            if user:
                assigned_users.append(user)

        previous_assigned = task_data.get('assignedTo', [])
        previous_user_ids = {u.get('uid') for u in previous_assigned if u.get('uid')}
        new_user_ids = {u.get('uid') for u in assigned_users if u.get('uid')}
        new_assignees = new_user_ids - previous_user_ids
        removed_users = previous_user_ids - new_user_ids

        update_data = {
            'title': title,
            'description': description,
            'dueDate': due_date,
            'assignedTo': assigned_users,
            'priority': priority,
            'completed': completed,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': current_user_id,
            'updaterName': session['user'].get('displayName', current_user_email)
        }

        task_repo.update_task(board_id, task_id, update_data)

        add_activity(db=db,
                    description=f"Updated task '{title}' in board: {board_data['name']}",
                    user_id=current_user_id, user_email=current_user_email,
                    board_id=board_id, board_name=board_data['name'])

        flash(f"Task '{title}' has been updated", "success")

        # Notify new assignees
        for user in assigned_users:
            if user.get('uid') in new_assignees and user.get('email') != current_user_email:
                subject = "You have been assigned a task"
                body = build_email_body(user['email'], "task", task_link)
                send_email(user['email'], subject, body)

        # Notify removed assignees
        for user in previous_assigned:
            if user.get('uid') in removed_users and user.get('email') != current_user_email:
                subject = "You have been unassigned from a task"
                body = build_email_body(
                    recipient_email=user['email'],
                    subject_type="unassigned",
                    link=None,
                    context_name=board_data.get('name', '')
                )
                send_email(user['email'], subject, body)

        return redirect(url_for('board.shared_board', board_id=board_id))


    @task_bp.route('/shared-delete-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def shared_delete_task(board_id, task_id):
        # Check board exists
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        user_role = None
        user_in_board = False

        for user in board_data.get('users', []):
            if user.get('uid') == current_user_id:
                user_in_board = True
                user_role = user.get('role')
                break

        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        # Check task exists
        task_data = task_repo.get_task(board_id, task_id)
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.shared_board', board_id=board_id))

        # Check permission: only task creator or board owner can delete
        is_task_creator = task_data.get('createdBy') == current_user_id
        is_board_owner = user_role == 'owner' or board_data.get('createdBy') == current_user_id

        if not (is_task_creator or is_board_owner):
            flash("You don't have permission to delete this task", "warning")
            return redirect(url_for('board.shared_board', board_id=board_id))

        # Delete the task
        task_repo.delete_task(board_id, task_id)

        # Log the deletion
        add_activity(
            db=db,
            description=f"Deleted task '{task_data['title']}' from board: {board_data['name']}",
            user_id=current_user_id,
            user_email=session['user']['email'],
            board_id=board_id,
            board_name=board_data['name']
        )

        flash(f"Task '{task_data['title']}' has been deleted", "warning")
        return redirect(url_for('board.shared_board', board_id=board_id))


    @task_bp.route('/shared-toggle-task/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def shared_toggle_task(board_id, task_id):
        # Check board exists and user has access
        board_data = board_repo.get_board(board_id)

        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_user_id = session['user']['uid']
        current_user_email = session['user']['email']

        # Ensure user is in board (by uid or fallback email)
        user_in_board = any(user.get('uid') == current_user_id for user in board_data.get('users', []))
        if not user_in_board:
            user_in_board = any(user.get('email') == current_user_email for user in board_data.get('users', []))
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))

        # Check if task exists
        task_data = task_repo.get_task(board_id, task_id)
        if not task_data:
            flash("Task not found", "danger")
            return redirect(url_for('board.shared_board', board_id=board_id))

        new_status = not task_data.get('completed', False)

        # Update task status
        update_data = {
            'completed': new_status,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'updatedBy': current_user_id,
            'updaterName': session['user'].get('displayName', current_user_email)
        }
        task_repo.toggle_task_completion(board_id, task_id, update_data)

        # Notify board owner if task is completed
        if new_status:
            board_owner = next((u for u in board_data['users'] if u['uid'] == board_data['createdBy']), None)
            if board_owner and board_owner.get('email') != current_user_email:
                task_link = url_for('board.shared_board', board_id=board_id, _external=True)
                subject = "A task was marked as completed"
                body = build_email_body(board_owner['email'], "task-completed", task_link)
                send_email(board_owner['email'], subject, body)

        # Log activity
        status_text = "Completed" if new_status else "Reopened"
        add_activity(
            db=db,
            description=f"{status_text} task '{task_data['title']}' in board: {board_data['name']}",
            user_id=current_user_id,
            user_email=current_user_email,
            board_id=board_id,
            board_name=board_data['name']
        )

        flash(f"Task '{task_data['title']}' has been {status_text.lower()}", "success")
        return redirect(url_for('board.shared_board', board_id=board_id))


    @task_bp.route('/shared-add-comment/<board_id>/<task_id>', methods=['POST'])
    @login_required
    def shared_add_comment(board_id, task_id):
        comment_text = request.form.get('comment', '').strip()
        if not comment_text:
            flash("Comment cannot be empty", "danger")
            return redirect(url_for('board.shared_board', board_id=board_id))

        # Verify board and task access
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_uid = session['user']['uid']
        current_email = session['user']['email']

        user_in_board = any(user.get('uid') == current_uid or user.get('email') == current_email for user in board_data.get('users', []))
        if not user_in_board:
            flash("You do not have access to this board", "warning")
            return redirect(url_for('dashboard'))

        # Create comment
        comment_data = {
            'text': comment_text,
            'createdBy': current_uid,
            'creatorName': session['user'].get('displayName', current_email),
            'creatorEmail': current_email,
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        # Add comment to task
        task_repo.add_comment(board_id, task_id, comment_data)

        # Log activity
        add_activity(
            db=db,
            description=f"Added a comment to task in board: {board_data['name']}",
            user_id=current_uid,
            user_email=current_email,
            board_id=board_id,
            board_name=board_data['name']
        )

        flash("Comment added successfully", "success")
        return redirect(url_for('board.shared_board', board_id=board_id))
        
    return task_bp