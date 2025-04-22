from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from firebase_admin import auth as admin_auth
from utils.auth_utils import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route('/users')
@login_required
def list_users():
    if not session.get('user', {}).get('is_admin', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    try:
        users = []
        page = admin_auth.list_users()
        while page:
            for user in page.users:
                users.append({
                    'uid': user.uid,
                    'email': user.email,
                    'display_name': user.display_name,
                    'disabled': user.disabled,
                    'custom_claims': user.custom_claims
                })
            page = page.get_next_page()
        return render_template('users.html', users=users, user=session.get('user'))

    except Exception as e:
        flash(f'Error fetching users: {str(e)}', 'danger')
        return redirect(url_for('index'))

@admin_bp.route('/user/<uid>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(uid):
    if not session.get('user', {}).get('is_admin', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        display_name = request.form.get('display_name')
        disabled = request.form.get('disabled') == 'on'

        try:
            admin_auth.update_user(
                uid,
                display_name=display_name,
                disabled=disabled
            )
            flash('User updated successfully.', 'success')
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'danger')
        return redirect(url_for('admin.list_users'))

    try:
        user = admin_auth.get_user(uid)
        return render_template(
            'edit_user.html',
            edited_user={
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'disabled': user.disabled
            },
        )
    except Exception as e:
        flash(f'Error loading user: {str(e)}', 'danger')
        return redirect(url_for('admin.list_users'))
    
@admin_bp.route('/user/<uid>/delete', methods=['POST'])
@login_required
def delete_user(uid):
    if not session.get('user', {}).get('is_admin', False):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))

    try:
        admin_auth.delete_user(uid)
        flash('User deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'danger')

    return redirect(url_for('admin.list_users'))