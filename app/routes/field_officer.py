from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required

field_bp = Blueprint('field', __name__)

@field_bp.route('/dashboard')
@login_required
@role_required('field_officer')
def dashboard():
    return render_template('field_officer/dashboard.html')