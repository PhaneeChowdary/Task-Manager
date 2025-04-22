# blueprints/board_routes.py
import csv
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
import logging
from utils.date_utils import format_datetime_exact
from utils.auth_utils import login_required
from repositories.board_repository import BoardRepository
from repositories.task_repository import TaskRepository
from utils.activity_utils import add_activity
from firebase_admin import firestore

# Set up logging
logger = logging.getLogger(__name__)

board_bp = Blueprint('board', __name__)

def init_board_routes(db):
    board_repo = BoardRepository(db)
    task_repo = TaskRepository(db)
    
    @board_bp.route('/boards')
    @login_required
    def boards():
        # Get user's boards
        user_boards = board_repo.get_user_boards(session['user']['uid'])
        
        return render_template('boards.html', user=session['user'], boards=user_boards)

    @board_bp.route('/shared')
    @login_required
    def shared_boards():
        # Get shared boards
        shared_boards = board_repo.get_shared_boards(
            session['user']['uid'], 
            session['user']['email']
        )
        
        return render_template('shared.html', user=session['user'], boards=shared_boards)

    @board_bp.route('/board/<board_id>')
    @login_required
    def board(board_id):
        # Get board details
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        creator_id = board_data.get('createdBy')
        creator_name = board_data.get('creatorName', 'Unknown')
        creator_status = "active"

        from firebase_admin import auth as admin_auth
        try:
            admin_auth.get_user(creator_id)
        except Exception:
            creator_status = "deleted"

        # Check if user is part of this board
        current_user_id = session['user']['uid']
        current_user_email = session['user']['email']
        user_in_board = False
        user_role = None
        
        for user in board_data.get('users', []):
            if user.get('uid') == current_user_id or user.get('email') == current_user_email:
                user_in_board = True
                user_role = user.get('role')
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))
        
        # Get tasks for this board
        all_tasks = task_repo.get_board_tasks(board_id)
        
        # Filter tasks based on user role and assignments
        is_board_owner = user_role == 'owner'
        
        if is_board_owner:
            # Board owners see all tasks
            visible_tasks = all_tasks
        else:
            # Regular users only see tasks assigned to them
            visible_tasks = []
            for task in all_tasks:
                # Check if user is assigned to this task
                is_assigned = False
                
                # Handle different ways tasks might be assigned
                assigned_to = task.get('assignedTo', [])
                if isinstance(assigned_to, list):
                    for assigned_user in assigned_to:
                        if (assigned_user.get('uid') == current_user_id or 
                            assigned_user.get('email') == current_user_email):
                            is_assigned = True
                            break
                elif isinstance(assigned_to, dict):
                    # Handle single assignment as dict case
                    if (assigned_to.get('uid') == current_user_id or 
                        assigned_to.get('email') == current_user_email):
                        is_assigned = True
                
                # Include tasks assigned to the user
                if is_assigned:
                    visible_tasks.append(task)
        
        # Get comments for each task
        for task in visible_tasks:
            task['comments'] = task_repo.get_task_comments(board_id, task['id'])
        
        # Calculate stats
        all_tasks_count = len(all_tasks)
        visible_tasks_count = len(visible_tasks)
        
        return render_template('board.html', 
                            user=session['user'], 
                            board=board_data, 
                            tasks=visible_tasks,
                            all_tasks_count=all_tasks_count,
                            visible_tasks_count=visible_tasks_count,
                            is_owner=is_board_owner,
                            creator_status=creator_status)
    
    @board_bp.route('/shared-board/<board_id>')
    @login_required
    def shared_board(board_id):
        # Get board details
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        creator_id = board_data.get('createdBy')
        creator_name = board_data.get('creatorName', 'Unknown')
        creator_status = "deleted"  # default

        # Check if creator is still in the board users list
        for user in board_data.get('users', []):
            if user.get('uid') == creator_id:
                creator_status = "active"
                break


        # Check if user is part of this board
        current_user_id = session['user']['uid']
        current_user_email = session['user']['email']
        user_in_board = False
        user_role = None
        
        for user in board_data.get('users', []):
            if user.get('uid') == current_user_id or user.get('email') == current_user_email:
                user_in_board = True
                user_role = user.get('role')
                break
        
        if not user_in_board:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))
        
        # Get tasks for this board
        all_tasks = task_repo.get_board_tasks(board_id)
        
        # Filter tasks based on user role and assignments
        is_board_owner = user_role == 'owner'
        
        if is_board_owner:
            # Board owners see all tasks
            visible_tasks = all_tasks
        else:
            # Regular users only see tasks assigned to them
            visible_tasks = []
            for task in all_tasks:
                # Check if user is assigned to this task
                is_assigned = False
                
                # Handle different ways tasks might be assigned
                assigned_to = task.get('assignedTo', [])
                if isinstance(assigned_to, list):
                    for assigned_user in assigned_to:
                        if (assigned_user.get('uid') == current_user_id or 
                            assigned_user.get('email') == current_user_email):
                            is_assigned = True
                            break
                elif isinstance(assigned_to, dict):
                    # Handle single assignment as dict case
                    if (assigned_to.get('uid') == current_user_id or 
                        assigned_to.get('email') == current_user_email):
                        is_assigned = True
                
                # Include tasks assigned to the user
                if is_assigned:
                    visible_tasks.append(task)
        
        # Get comments for each task
        for task in visible_tasks:
            task['comments'] = task_repo.get_task_comments(board_id, task['id'])
        
        # Calculate stats
        all_tasks_count = len(all_tasks)
        visible_tasks_count = len(visible_tasks)
        
        return render_template('shared_board.html', 
                            user=session['user'], 
                            board=board_data, 
                            tasks=visible_tasks,
                            all_tasks_count=all_tasks_count,
                            visible_tasks_count=visible_tasks_count,
                            is_owner=board_data['createdBy'] == session['user']['uid'],
                            creator_name=creator_name,
                            creator_status=creator_status)


    @board_bp.route('/create-board', methods=['POST'])
    @login_required
    def create_board():
        name = request.form['name']
        description = request.form.get('description', '')
        
        if not name:
            flash("Board name is required", "warning")
            return redirect(url_for('board.boards'))
        
        board_data = {
            'name': name,
            'description': description,
            'createdBy': session['user']['uid'],
            'creatorName': session['user'].get('displayName', session['user']['email']),
            'createdAt': firestore.SERVER_TIMESTAMP,
            'taskCount': 0,
            'completedTaskCount': 0,
            'users': [{
                'uid': session['user']['uid'],
                'email': session['user']['email'],
                'displayName': session['user'].get('displayName', session['user']['email']),
                'role': 'owner'
            }]
        }
        
        # Add board to Firestore
        board_id = board_repo.create_board(board_data)
        
        # Add activity
        add_activity(db, f"Created board: {name}", session['user']['uid'], session['user']['email'])
        
        flash(f"Board '{name}' created successfully", "success")
        return redirect(url_for('board.board', board_id=board_id))

    @board_bp.route('/delete-board/<board_id>', methods=['POST'])
    @login_required
    def delete_board(board_id):
        # Get board details
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('board.boards'))
        
        # Check if user is the owner
        if board_data['createdBy'] != session['user']['uid']:
            flash("Only the board owner can delete the board", "warning")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Delete the board and its tasks
        board_repo.delete_board(board_id)
        
        # Add activity log
        add_activity(db, f"Deleted board: {board_data['name']}", session['user']['uid'], session['user']['email'])
        
        flash(f"Board '{board_data['name']}' has been deleted", "warning")
        return redirect(url_for('board.boards'))

    @board_bp.route('/add-user/<board_id>', methods=['POST'])
    @login_required
    def add_user(board_id):
        email = request.form['email']
        
        # Get board details
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('board.boards'))
        
        # Check if user is the owner
        if board_data['createdBy'] != session['user']['uid']:
            flash("Only the board owner can add users", "warning")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Check if user is already in the board
        for user in board_data.get('users', []):
            if user.get('email') == email:
                flash(f"User {email} is already part of this board", "warning")
                return redirect(url_for('board.board', board_id=board_id))
        
        # Try to find user by email in Firebase
        from repositories.user_repository import UserRepository
        user_repo = UserRepository(db)
        
        try:
            user_record = user_repo.get_user_by_email(email)
            if user_record:
                # User exists in Firebase, use their real UID
                new_user = {
                    'uid': user_record.uid,
                    'email': user_record.email,
                    'displayName': user_record.display_name or email.split('@')[0],
                    'role': 'member'
                }
                
                # Add user to board
                board_repo.add_user_to_board(board_id, new_user)
                
                # Add activity
                add_activity(
                    db, 
                    f"Added user {email} to board: {board_data['name']}", 
                    session['user']['uid'], 
                    session['user']['email'],
                    board_id,
                    board_data['name']
                )
                
                flash(f"User {email} has been added to the board", "success")
            else:
                flash(f"User with email {email} does not exist in the system", "danger")

        except Exception as e:
            logger.error(f"Error adding user {email} to board: {str(e)}", exc_info=True)
            flash(f"Error adding user: {str(e)}", "danger")

        return redirect(url_for('board.board', board_id=board_id))

    @board_bp.route('/remove-user/<board_id>/<user_id>', methods=['POST'])
    @login_required
    def remove_user(board_id, user_id):
        # Get board details
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('board.boards'))
        
        # Check if user is the owner
        if board_data['createdBy'] != session['user']['uid']:
            flash("Only the board owner can remove users", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Find user in the board
        user_found = None
        for user in board_data.get('users', []):
            if user.get('uid') == user_id:
                user_found = user
                break
        
        if not user_found:
            flash("User not found in this board", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Cannot remove owner
        if user_found.get('role') == 'owner':
            flash("Cannot remove the board owner", "danger")
            return redirect(url_for('board.board', board_id=board_id))
        
        # Remove user from board
        board_repo.remove_user_from_board(board_id, user_id)
        
        # Add activity log
        add_activity(
            db,
            f"Removed user {user_found.get('email')} from board: {board_data['name']}",
            session['user']['uid'],
            session['user']['email'],
            board_id,
            board_data['name']
        )
        
        flash(f"User {user_found.get('email')} has been removed from the board", "warning")
        return redirect(url_for('board.board', board_id=board_id))
        
    @board_bp.route('/export/board/<board_id>/csv')
    @login_required
    def export_board_csv(board_id):
        from flask import Response
        from io import StringIO
        import csv
        
        # Get board details
        board_data = board_repo.get_board(board_id)
        
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))
        
        # Check if user has access to this board
        user_has_access = False
        for user in board_data.get('users', []):
            if user.get('uid') == session['user']['uid'] or user.get('email') == session['user']['email']:
                user_has_access = True
                break
        
        if not user_has_access:
            flash("You do not have access to this board", "danger")
            return redirect(url_for('dashboard'))
        
        # Get tasks for this board
        tasks = task_repo.get_board_tasks(board_id)
        
        # Create CSV file
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Task ID', 'Title', 'Description', 'Status', 'Priority', 'Due Date', 
                        'Assigned To', 'Created By', 'Created At', 'Updated At'])
        
        # Write task data
        for task in tasks:
            # Handle assigned to field (might be single user or list)
            if isinstance(task.get('assignedTo'), list):
                assigned_to = ', '.join([u.get('email', '') for u in task.get('assignedTo', [])])
            elif task.get('assignedTo'):
                assigned_to = task.get('assignedTo', {}).get('email', '')
            else:
                assigned_to = 'Unassigned'
            
            # Format timestamps
            created_at = format_datetime_exact(task.get('createdAt', ''))
            updated_at = format_datetime_exact(task.get('updatedAt', ''))
            
            writer.writerow([
                task.get('id', ''),
                task.get('title', ''),
                task.get('description', ''),
                'Completed' if task.get('completed', False) else 'Active',
                task.get('priority', ''),
                task.get('dueDate', ''),
                assigned_to,
                task.get('creatorName', ''),
                created_at,
                updated_at
            ])
        
        # Prepare response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=board_{board_id}.csv"}
        )
    
    @board_bp.route('/export/my-boards/csv')
    @login_required
    def export_my_boards_csv():
        user_id = session['user']['uid']
        board_repo = BoardRepository(db)
        boards = board_repo.get_user_boards(user_id)

        return generate_board_csv_response(boards, filename='my_boards.csv')

    @board_bp.route('/export/shared-boards/csv')
    @login_required
    def export_shared_boards_csv():
        user_id = session['user']['uid']
        user_email = session['user']['email']
        board_repo = BoardRepository(db)
        boards = board_repo.get_shared_boards(user_id, user_email)

        return generate_board_csv_response(boards, filename='shared_boards.csv')
    
    @board_bp.route('/leave-board/<board_id>', methods=['POST'])
    @login_required
    def leave_board(board_id):
        board_data = board_repo.get_board(board_id)
        current_uid = session['user']['uid']

        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        # If owner is leaving, delete the board and notify
        if board_data['createdBy'] == current_uid:
            board_repo.delete_board(board_id)
            flash("You were the owner. Board and all members were removed.", "warning")
            return redirect(url_for('dashboard'))

        # Otherwise, remove the user
        board_repo.remove_user_from_board(board_id, current_uid)
        flash("You have left the board.", "warning")
        return redirect(url_for('board.shared_boards'))
    
    @board_bp.route('/edit-board/<board_id>', methods=['POST'])
    @login_required
    def edit_board(board_id):
        board_data = board_repo.get_board(board_id)
        if not board_data:
            flash("Board not found", "danger")
            return redirect(url_for('dashboard'))

        current_uid = session['user']['uid']
        user_is_owner = board_data['createdBy'] == current_uid

        # Check if user is in board
        if not any(user['uid'] == current_uid for user in board_data.get('users', [])):
            flash("You don't have access to edit this board", "danger")
            return redirect(url_for('dashboard'))

        # Update name and description
        name = request.form.get('name')
        description = request.form.get('description')

        update_data = {'name': name, 'description': description}
        board_repo.update_board(board_id, update_data)

        flash("Board updated successfully", "success")
        if user_is_owner:
            return redirect(url_for('board.board', board_id=board_id))
        else:
            return redirect(url_for('board.shared_board', board_id=board_id))



    def generate_board_csv_response(boards, filename='boards.csv'):
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Board Name', 'Description', 'Created At', 'Total Tasks', 'Completed Tasks', 'Users'])

        # Write each board's data
        for board in boards:
            created_at = format_datetime_exact(board.get('createdAt'))
            users = ', '.join([user.get('email', '') for user in board.get('users', [])])
            writer.writerow([
                board.get('name', ''),
                board.get('description', ''),
                created_at,
                board.get('taskCount', 0),
                board.get('completedTaskCount', 0),
                users
            ])

        # Send response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
        
    return board_bp