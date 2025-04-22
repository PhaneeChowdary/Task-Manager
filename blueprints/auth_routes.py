# blueprints/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import logging
from repositories.user_repository import UserRepository
from utils.auth_utils import login_required
from firebase_admin import auth as admin_auth
import json

# Set up logging
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def init_auth_routes(db, firebase_auth):
    user_repo = UserRepository(db)

    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            try:
                user = user_repo.get_user_by_email(email)
                if not user:
                    flash("Login failed: User not found", "danger")
                    return render_template('login.html')

                # Fetch Firebase user to get custom claims
                admin_user = admin_auth.get_user(user.uid)
                is_admin = admin_user.custom_claims.get('is_admin') if admin_user.custom_claims else False

                # Store user in session
                session['user'] = {
                    'uid': user.uid,
                    'email': user.email,
                    'displayName': user.display_name or user.email,
                    'is_admin': is_admin
                }
                logger.info(f"User {email} logged in successfully")
                flash('Login successful!', "success")
                return redirect(url_for('dashboard'))
            except Exception as e:
                error_message = str(e)
                logger.error(f"Login error: {error_message}", exc_info=True)
                flash(f"Login failed: {error_message}", "danger")

        return render_template('login.html')

    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            try:
                logger.info(f"Attempting to register: {email}")
                user = user_repo.create_user(email=email, password=password)
                logger.info(f"User created with ID: {user.uid}")

                session['user'] = {
                    'uid': user.uid,
                    'email': email,
                    'displayName': email.split('@')[0],
                    'is_admin': False
                }
                return redirect(url_for('dashboard'))
            except Exception as e:
                error_message = str(e)
                logger.error(f"Registration error: {error_message}", exc_info=True)
                flash(f"Registration failed: {error_message}", "danger")

        return render_template('register.html')

    @auth_bp.route('/google-login')
    def google_login():
        return render_template('google_login.html')

    @auth_bp.route('/process-google-login', methods=['POST'])
    def process_google_login():
        id_token = request.form.get('idToken')
        if not id_token:
            logger.warning("No idToken received in Google login request")
            return jsonify({'success': False, 'error': 'No ID token provided'})

        try:
            logger.info(f"Processing Google login with token: {id_token[:10]}...")
            decoded_token = firebase_auth.verify_id_token(id_token)
            uid = decoded_token['uid']

            user_record = user_repo.get_user_by_id(uid)
            admin_user = admin_auth.get_user(uid)
            is_admin = admin_user.custom_claims.get('is_admin') if admin_user.custom_claims else False

            session['user'] = {
                'uid': uid,
                'email': user_record.email,
                'displayName': user_record.display_name or user_record.email,
                'is_admin': is_admin
            }
            logger.debug(f"Session after login: {session}")
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        except Exception as e:
            logger.error(f"Google login error: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)})

    @auth_bp.route('/logout')
    def logout():
        if 'user' in session:
            logger.info(f"User {session['user'].get('email')} logged out")
            session.pop('user', None)
        return redirect(url_for('index'))

    @auth_bp.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            display_name = request.form.get('display_name', '')
            try:
                user_repo.update_user(
                    session['user']['uid'],
                    display_name=display_name
                )
                session['user']['displayName'] = display_name
                logger.info(f"Profile updated for user {session['user']['email']}")
                flash('Profile updated successfully!', "success")
            except Exception as e:
                logger.error(f"Error updating profile: {str(e)}", exc_info=True)
                flash(f'Error updating profile: {str(e)}', "danger")
            return redirect(url_for('auth.profile'))

        user_id = session['user']['uid']
        user_email = session['user']['email']

        from repositories.board_repository import BoardRepository
        board_repo = BoardRepository(db)
        user_boards = board_repo.get_user_boards(user_id)
        shared_boards = board_repo.get_shared_boards(user_id, user_email)
        all_boards = user_boards + shared_boards

        from repositories.task_repository import TaskRepository
        task_repo = TaskRepository(db)
        all_tasks = []
        for board in all_boards:
            tasks = task_repo.get_board_tasks(board['id'])
            for task in tasks:
                is_assigned = False
                if 'assignedTo' in task:
                    if isinstance(task['assignedTo'], list):
                        for user in task['assignedTo']:
                            if user.get('uid') == user_id:
                                is_assigned = True
                                break
                    elif task['assignedTo'] and task['assignedTo'].get('uid') == user_id:
                        is_assigned = True
                if is_assigned or task.get('createdBy') == user_id:
                    task['boardId'] = board['id']
                    task['boardName'] = board['name']
                    all_tasks.append(task)
        all_tasks.sort(key=lambda x: x.get('createdAt', 0), reverse=True)

        return render_template(
            'profile.html',
            user=session['user'],
            boards=all_boards,
            tasks=all_tasks
        )

    @auth_bp.route('/delete-account', methods=['POST'])
    @login_required
    def delete_account():
        uid = session['user']['uid']
        email = session['user']['email']

        from utils.export_utils import export_and_email_user_data
        try:
            export_and_email_user_data(db, uid, email)
            logger.info(f"Exported data for user {email} before account deletion")
        except Exception as e:
            logger.error(f"Failed to send user data export email: {e}", exc_info=True)

        try:
            user_repo.delete_user(uid)
            logger.info(f"Deleted user {email} from Firebase Auth")
        except Exception as e:
            logger.error(f"Error deleting user from Firebase Auth: {e}", exc_info=True)

        from repositories.board_repository import BoardRepository
        board_repo = BoardRepository(db)
        boards = board_repo.get_user_boards(uid)
        for board in boards:
            board_repo.delete_board(board['id'])

        all_boards = db.collection('boards').stream()
        for board in all_boards:
            board_data = board.to_dict()
            users = board_data.get('users', [])
            updated_users = [user for user in users if user.get('uid') != uid]
            if len(users) != len(updated_users):
                db.collection('boards').document(board.id).update({'users': updated_users})

        activities = db.collection('activity').where('userId', '==', uid).stream()
        for activity in activities:
            activity.reference.delete()

        session.clear()
        logger.info(f"User {email} deleted their account")
        flash("Your data is sent to your mail, account and all related data have been deleted.")
        return redirect(url_for('index'))
    
    return auth_bp