import os
from flask import Flask, render_template, session, jsonify, redirect, url_for, request
import logging
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialize Firebase
from config.firebase_config import init_firebase_admin, init_pyrebase
db, bucket = init_firebase_admin()
firebase_auth = init_pyrebase()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

@app.context_processor
def inject_firebase_config():
    return {
        'firebase_config': {
            'apiKey': os.getenv('FIREBASE_API_KEY'),
            'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN'),
            'projectId': os.getenv('FIREBASE_PROJECT_ID'),
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET'),
            'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
            'appId': os.getenv('FIREBASE_APP_ID'),
        }
    }

@app.template_filter('format_datetime_exact')
def format_datetime_exact(timestamp):
    if not timestamp:
        return ''
    
    try:
        if hasattr(timestamp, 'todate'):
            return timestamp.todate().date()
        elif isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp).date()
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp).date()
        else:
            return timestamp.date() if hasattr(timestamp, 'date') else timestamp
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}, raw timestamp: {timestamp}")
        return timestamp

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {request.path}")
    return render_template('error.html', error=f"404 Not Found: {request.path} was not found"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {str(e)}")
    return render_template('error.html', error=f"500 Server Error: {str(e)}"), 500

# Register blueprints
from blueprints.auth_routes import init_auth_routes
from blueprints.board_routes import init_board_routes
from blueprints.task_routes import init_task_routes
from blueprints.admin_routes import admin_bp

auth_bp = init_auth_routes(db, firebase_auth)
board_bp = init_board_routes(db)
task_bp = init_task_routes(db)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(board_bp, url_prefix='/boards')
app.register_blueprint(task_bp, url_prefix='/tasks')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Route aliases for backward compatibility with method handling
@app.route('/boards')
def boards():
    return redirect(url_for('board.boards'))

@app.route('/shared')
def shared_boards():
    return redirect(url_for('board.shared_boards'))

@app.route('/board/<board_id>')
def board(board_id):
    return redirect(url_for('board.board', board_id=board_id))

@app.route('/shared-board/<board_id>')
def shared_board(board_id):
    return redirect(url_for('shared_board', board_id=board_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('auth.login'), code=307)  # 307 preserves the POST data
    return redirect(url_for('auth.login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect(url_for('auth.register'), code=307)
    return redirect(url_for('auth.register'))

@app.route('/logout')
def logout():
    return redirect(url_for('auth.logout'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        return redirect(url_for('auth.profile'), code=307)
    return redirect(url_for('auth.profile'))

@app.route('/google-login')
def google_login():
    return redirect(url_for('auth.google_login'))

@app.route('/process-google-login', methods=['POST'])
def process_google_login():
    return redirect(url_for('auth.process_google_login'), code=307)

@app.route('/delete-account', methods=['POST'])
def delete_account():
    return redirect(url_for('auth.delete_account'), code=307)

@app.route('/create-board', methods=['POST'])
def create_board():
    return redirect(url_for('board.create_board'), code=307)

@app.route('/delete-board/<board_id>', methods=['POST'])
def delete_board(board_id):
    return redirect(url_for('board.delete_board', board_id=board_id), code=307)

@app.route('/add-user/<board_id>', methods=['POST'])
def add_user(board_id):
    return redirect(url_for('board.add_user', board_id=board_id), code=307)

@app.route('/remove-user/<board_id>/<user_id>', methods=['POST'])
def remove_user(board_id, user_id):
    return redirect(url_for('board.remove_user', board_id=board_id, user_id=user_id), code=307)

@app.route('/export/board/<board_id>/csv')
def export_board_csv(board_id):
    return redirect(url_for('board.export_board_csv', board_id=board_id))

@app.route('/export/my-boards/csv')
def export_my_boards_csv():
    return redirect(url_for('board.export_my_boards_csv'))

@app.route('/export/shared-boards/csv')
def export_shared_boards_csv():
    return redirect(url_for('board.export_shared_boards_csv'))


@app.route('/add-task/<board_id>', methods=['POST'])
def add_task(board_id):
    return redirect(url_for('task.add_task', board_id=board_id), code=307)

@app.route('/update-task/<board_id>/<task_id>', methods=['POST'])
def update_task(board_id, task_id):
    return redirect(url_for('task.update_task', board_id=board_id, task_id=task_id), code=307)

@app.route('/delete-task/<board_id>/<task_id>', methods=['POST'])
def delete_task(board_id, task_id):
    return redirect(url_for('task.delete_task', board_id=board_id, task_id=task_id), code=307)

@app.route('/toggle-task/<board_id>/<task_id>', methods=['POST'])
def toggle_task(board_id, task_id):
    return redirect(url_for('task.toggle_task', board_id=board_id, task_id=task_id), code=307)

@app.route('/add-comment/<board_id>/<task_id>', methods=['POST'])
def add_comment(board_id, task_id):
    return redirect(url_for('task.add_comment', board_id=board_id, task_id=task_id), code=307)

@app.route('/leave-board/<board_id>', methods=['POST'])
def leave_board(board_id):
    return redirect(url_for('board.leave_board', board_id=board_id), code=307)


# Main routes
@app.route('/')
def index():
    from repositories.board_repository import BoardRepository
    from repositories.task_repository import TaskRepository
    from repositories.activity_repository import ActivityRepository
    
    try:
        board_repo = BoardRepository(db)
        task_repo = TaskRepository(db)
        activity_repo = ActivityRepository(db)
        
        if 'user' in session:
            user = session['user']
            user_id = user['uid']
            user_email = user['email']

            # Get user's boards
            user_boards = board_repo.get_user_boards(user_id)

            # Get shared boards
            shared_boards = board_repo.get_shared_boards(user_id, user_email)
            total_boards_count = len(user_boards) + len(shared_boards)

            # Count total tasks and completed tasks
            total_tasks = []
            completed_tasks = []
            
            # Tasks of user boards
            for board in user_boards:
                tasks = task_repo.get_board_tasks(board['id'])
                total_tasks.extend(tasks)
                completed_tasks.extend([t for t in tasks if t.get('completed')])
            
            # Tasks of shared boards
            for board in shared_boards:
                tasks = task_repo.get_board_tasks(board['id'])
                total_tasks.extend(tasks)
                completed_tasks.extend([t for t in tasks if t.get('completed')])
            
            # Get recent activities and chart data
            activities = activity_repo.get_user_activities(user_id, limit=50)
            chart_labels, chart_data = activity_repo.get_activity_chart_data(user_id)
            
            # Only show the 5 most recent activities in the list
            recent_activities = activities[:5]

            return render_template(
                'index.html',
                user=user,
                user_boards=user_boards,
                shared_boards=shared_boards,
                total_boards=total_boards_count,  
                total_tasks=len(total_tasks),     
                completed_tasks=len(completed_tasks),
                activities=recent_activities,
                chart_labels=chart_labels,
                chart_data=chart_data
            )

        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500

# Dashboard route
@app.route('/dashboard')
def dashboard():
    try:
        from utils.auth_utils import login_required
        from repositories.board_repository import BoardRepository
        from repositories.task_repository import TaskRepository
        from repositories.activity_repository import ActivityRepository
        
        # Check if user is logged in
        if 'user' not in session:
            logger.warning("No user in session for dashboard route")
            return redirect(url_for('login'))
            
        user_id = session['user']['uid']
        user_email = session['user']['email']
        
        logger.info(f"Dashboard accessed by user: {user_id}")
        
        board_repo = BoardRepository(db)
        activity_repo = ActivityRepository(db)
        
        # Get user's boards and shared boards
        user_boards = board_repo.get_user_boards(user_id)
        shared_boards = board_repo.get_shared_boards(user_id, user_email)
        total_boards_count = len(user_boards) + len(shared_boards)

        # Count total tasks and completed tasks
        total_tasks = 0
        completed_tasks = 0
        
        # Count from user's own boards
        for board in user_boards:
            total_tasks += board.get('taskCount', 0)
            completed_tasks += board.get('completedTaskCount', 0)
        
        # Count from shared boards
        for board in shared_boards:
            total_tasks += board.get('taskCount', 0)
            completed_tasks += board.get('completedTaskCount', 0)
        
        # Get recent activities and chart data
        activities = activity_repo.get_user_activities(user_id, limit=50)
        chart_labels, chart_data = activity_repo.get_activity_chart_data(user_id)
        
        # Only show the 5 most recent activities
        recent_activities = activities[:5]
        
        return render_template('dashboard.html', 
                            user=session['user'], 
                            user_boards=user_boards, 
                            shared_boards=shared_boards,
                            total_boards=total_boards_count,
                            total_tasks=total_tasks,
                            completed_tasks=completed_tasks,
                            activities=recent_activities,
                            chart_labels=chart_labels,
                            chart_data=chart_data)
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500

@app.route('/debug-session')
def debug_session():
    return jsonify({
        'has_session': 'user' in session,
        'session_data': session.get('user', 'No user in session')
    })

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

@app.context_processor
def inject_user():
    return {'user': session.get('user')}


if __name__ == '__main__':
    app.run(debug=True)