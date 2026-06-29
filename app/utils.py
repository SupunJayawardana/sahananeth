from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    Usage:
        @role_required('gov_officer')
        @role_required('field_officer', 'gov_officer')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role_level not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator