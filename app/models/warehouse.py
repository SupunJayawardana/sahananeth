from app.extensions import db

class Warehouse(db.Model):
    __tablename__ = 'warehouses'

    id = db.Column(db.Integer, primary_key=True)
    warehouse_name = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    # Relationship — one warehouse has many stock items
    stock_items = db.relationship('InventoryStock', backref='warehouse', lazy=True)

    def __repr__(self):
        return f'<Warehouse {self.warehouse_name}>'


class InventoryStock(db.Model):
    __tablename__ = 'inventory_stock'

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    sku_name = db.Column(db.String(120), nullable=False)       # e.g. "Rice 5kg"
    quantity_available = db.Column(db.Integer, default=0)
    metric_unit = db.Column(db.String(30), nullable=False)     # e.g. "kg", "units"

    def __repr__(self):
        return f'<Stock {self.sku_name} | {self.quantity_available} {self.metric_unit}>'