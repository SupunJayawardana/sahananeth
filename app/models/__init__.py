# Importing all models here so Flask-Migrate can detect them
from app.models.user import User
from app.models.shelter import Shelter, Beneficiary
from app.models.warehouse import Warehouse, InventoryStock
from app.models.procurement import ProcurementRequest