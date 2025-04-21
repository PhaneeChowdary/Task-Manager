# utils/auth_utils.py
from functools import wraps
from flask import session, redirect, url_for, flash
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            logger.warning("Unauthorized access attempt to protected route")
            flash("Please log in to access this page", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function