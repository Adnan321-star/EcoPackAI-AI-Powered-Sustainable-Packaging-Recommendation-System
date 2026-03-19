import joblib
import numpy as np
import pandas as pd


class MLEngine:
    """
    Loads trained models from .pkl files (exported from Google Colab).
    Provides predict() to recommend top-N eco packaging materials.
    """

    FEATURES = [
        "Product_enc", "Industry_enc", "Material_enc",
        "MaterialType_enc", "Strength_enc", "Weight_Capacity_kg"
    ]

    # Fallback defaults when product not in encoder
    _DEFAULT_INDUSTRY  = 0
    _DEFAULT_STRENGTH  = 1
    _DEFAULT_WEIGHT    = 10.0

    def __init__(self, config):
        self.rf_model      = joblib.load(config["RF_MODEL_PATH"])
        self.xgb_model     = joblib.load(config["XGB_MODEL_PATH"])
        self.le_product    = joblib.load(config["LE_PRODUCT_PATH"])
        self.le_industry   = joblib.load(config["LE_INDUSTRY_PATH"])
        self.le_material   = joblib.load(config["LE_MATERIAL_PATH"])
        self.le_mattype    = joblib.load(config["LE_MATTYPE_PATH"])
        self.le_strength   = joblib.load(config["LE_STRENGTH_PATH"])
        self.material_stats: pd.DataFrame = joblib.load(config["MATERIAL_STATS_PATH"])

        # Pre-build all material rows for fast candidate generation
        self._all_materials = self._build_material_lookup()

        print(f"[ML Engine] Loaded RF + XGBoost. "
              f"{len(self.le_product.classes_)} products | "
              f"{len(self._all_materials)} materials.")

    def _build_material_lookup(self) -> pd.DataFrame:
        mats = self.material_stats[["Material_Name"]].copy()
        mats["Material_enc"]    = self.le_material.transform(mats["Material_Name"])
        mats["MaterialType_enc"] = [
            self._safe_encode(self.le_mattype, t)
            for t in self._infer_mat_types(mats["Material_Name"])
        ]
        mats = mats.merge(self.material_stats, on="Material_Name", how="left")
        return mats.reset_index(drop=True)

    def _infer_mat_types(self, names):
        # Map material names back to type — derived from training data pattern
        TYPE_MAP = {
            "Plastic": ["Plastic Tube", "Plastic Case", "PET Bottle", "HDPE Container",
                        "HDPE Bottle", "Blister Pack", "Recycled Plastic Box", "Recycled Plastic Shell"],
            "Glass":   ["Glass Vial", "Glass Bottle"],
            "Metal":   ["Aluminum Jar", "Steel Can", "Magnesium Alloy Case", "Steel Case",
                        "Aluminum Body", "Aluminum Bottle", "Aluminum Can", "Tin Container"],
            "Bioplastic": ["PLA Container", "PLA Wrapper"],
            "Paper":   ["Paper Packaging", "Kraft Paper Box"],
            "Natural Fiber": ["Bagasse Container", "Molded Pulp Box"],
            "Cardboard": ["Corrugated Box"],
            "Composite": ["Fiber Composite Board"],
            "Foam":    ["Foam Box"],
        }
        rev = {v: k for k, vs in TYPE_MAP.items() for v in vs}
        return [rev.get(n, "Plastic") for n in names]

    def _safe_encode(self, encoder, value):
        try:
            return encoder.transform([value])[0]
        except ValueError:
            return 0

    def _encode_product(self, product_name: str):
        pname = product_name.strip().title()
        # Exact match
        if pname in self.le_product.classes_:
            return self.le_product.transform([pname])[0], True
        # Fuzzy: partial match
        for cls in self.le_product.classes_:
            if pname.lower() in cls.lower() or cls.lower() in pname.lower():
                return self.le_product.transform([cls])[0], True
        return self._DEFAULT_INDUSTRY, False

    def predict(self, product_name: str, top_n: int = 3) -> dict:
        product_enc, found = self._encode_product(product_name)
        if not found:
            return {
                "error": f"Product '{product_name}' not found.",
                "available_products": sorted(self.le_product.classes_.tolist())
            }

        cand = self._all_materials.copy()

        # Build feature matrix: one row per material
        cand["Product_enc"]       = product_enc
        cand["Industry_enc"]      = self._DEFAULT_INDUSTRY
        cand["Strength_enc"]      = self._DEFAULT_STRENGTH
        cand["Weight_Capacity_kg"] = self._DEFAULT_WEIGHT

        X = cand[self.FEATURES]

        # ── ML Predictions ───────────────────────────────────────────
        cand["Predicted_Cost_USD"] = np.clip(self.rf_model.predict(X), 0, None)
        cand["Predicted_CO2"]      = np.clip(self.xgb_model.predict(X), 0, 100)

        # ── Eco Score (weighted composite) ───────────────────────────
        cand["Eco_Score"] = (
            cand["Biodegradability_Score_%"] * 0.35 +
            (100 - cand["Predicted_CO2"])    * 0.35 +
            cand["Recyclability_%"]          * 0.30
        ).round(2)

        top = (cand.sort_values("Eco_Score", ascending=False)
                   .head(top_n)
                   .reset_index(drop=True))

        results = []
        for i, row in top.iterrows():
            results.append({
                "rank":            i + 1,
                "material_name":   row["Material_Name"],
                "eco_score":       round(row["Eco_Score"], 2),
                "biodegradability": round(row["Biodegradability_Score_%"], 2),
                "co2_predicted":   round(row["Predicted_CO2"], 2),
                "co2_efficiency":  round(100 - row["Predicted_CO2"], 2),
                "recyclability":   round(row["Recyclability_%"], 2),
                "cost_predicted":  round(row["Predicted_Cost_USD"], 2),
                "grade": (
                    "Excellent" if row["Eco_Score"] >= 70 else
                    "Good"      if row["Eco_Score"] >= 50 else "Fair"
                )
            })

        return {
            "product":         product_name,
            "recommendations": results,
            "model_info": {
                "cost_model": "Random Forest Regressor",
                "co2_model":  "XGBoost Regressor",
                "eco_formula": "0.35×Biodeg + 0.35×(100−CO₂) + 0.30×Recyclability"
            }
        }

    def available_products(self):
        return sorted(self.le_product.classes_.tolist())
