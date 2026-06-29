from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required

citizen_bp = Blueprint('citizen', __name__)

@citizen_bp.route('/dashboard')
@login_required
@role_required('citizen')
def dashboard():
    return render_template('citizen/dashboard.html')