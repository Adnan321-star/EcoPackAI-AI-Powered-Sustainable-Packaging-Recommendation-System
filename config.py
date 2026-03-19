import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/eco_packaging")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    RF_MODEL_PATH    = os.getenv("RF_MODEL_PATH",    "ml_models/rf_cost.pkl")
    XGB_MODEL_PATH   = os.getenv("XGB_MODEL_PATH",   "ml_models/xgb_co2.pkl")
    LE_PRODUCT_PATH  = os.getenv("LE_PRODUCT_PATH",  "ml_models/le_product.pkl")
    LE_INDUSTRY_PATH = os.getenv("LE_INDUSTRY_PATH", "ml_models/le_industry.pkl")
    LE_MATERIAL_PATH = os.getenv("LE_MATERIAL_PATH", "ml_models/le_material.pkl")
    LE_MATTYPE_PATH  = os.getenv("LE_MATTYPE_PATH",  "ml_models/le_mattype.pkl")
    LE_STRENGTH_PATH = os.getenv("LE_STRENGTH_PATH", "ml_models/le_strength.pkl")
    MATERIAL_STATS_PATH = os.getenv("MATERIAL_STATS_PATH", "ml_models/material_stats.pkl")
