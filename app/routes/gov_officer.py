from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required

gov_bp = Blueprint('gov', __name__)

@gov_bp.route('/dashboard')
@login_required
@role_required('gov_officer')
def dashboard():
    return render_template('gov_officer/dashboard.html')