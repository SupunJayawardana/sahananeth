from app import create_app, db  # <-- import db too

app = create_app('production')

with app.app_context():
    db.create_all()
    import seed  # if seed.py runs its logic at import time, like this file does


if __name__ == '__main__':
    app.run(debug=True)