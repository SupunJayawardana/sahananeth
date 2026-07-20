import json
from datetime import datetime

from app.extensions import db


class SavedReport(db.Model):
    """
    A self-service report definition built through the Reports UI —
    which data source, which filters, an optional location-radius
    filter, and an optional group-by. Re-running it re-queries current
    data, so it always reflects the live system rather than a snapshot.
    """
    __tablename__ = 'saved_reports'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    source_key = db.Column(db.String(50), nullable=False)
    filters_json = db.Column(db.Text, nullable=True)
    location_filter_json = db.Column(db.Text, nullable=True)
    group_by = db.Column(db.String(50), nullable=True)
    sort_by = db.Column(db.String(50), nullable=True)
    sort_dir = db.Column(db.String(4), default='asc')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User')

    def get_filters(self):
        return json.loads(self.filters_json) if self.filters_json else []

    def set_filters(self, filters):
        self.filters_json = json.dumps(filters) if filters else None

    def get_location_filter(self):
        return json.loads(self.location_filter_json) if self.location_filter_json else None

    def set_location_filter(self, loc):
        self.location_filter_json = json.dumps(loc) if loc else None

    def __repr__(self):
        return f'<SavedReport {self.name!r} | {self.source_key}>'
