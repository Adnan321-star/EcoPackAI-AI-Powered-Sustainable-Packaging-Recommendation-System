from datetime import datetime
from app import db

class QueryHistory(db.Model):
    __tablename__ = "query_history"

    id           = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(120), nullable=False)
    industry     = db.Column(db.String(80))
    queried_at   = db.Column(db.DateTime, default=datetime.utcnow)
    top_material = db.Column(db.String(120))
    top_eco_score = db.Column(db.Float)

    recommendations = db.relationship("Recommendation", back_populates="query", cascade="all, delete")

    def to_dict(self):
        return {
            "id": self.id,
            "product_name": self.product_name,
            "industry": self.industry,
            "queried_at": self.queried_at.isoformat(),
            "top_material": self.top_material,
            "top_eco_score": round(self.top_eco_score or 0, 2),
        }


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id              = db.Column(db.Integer, primary_key=True)
    query_id        = db.Column(db.Integer, db.ForeignKey("query_history.id"), nullable=False)
    rank            = db.Column(db.Integer)
    material_name   = db.Column(db.String(120))
    material_type   = db.Column(db.String(80))
    eco_score       = db.Column(db.Float)
    biodegradability = db.Column(db.Float)
    co2_predicted   = db.Column(db.Float)
    recyclability   = db.Column(db.Float)
    cost_predicted  = db.Column(db.Float)

    query = db.relationship("QueryHistory", back_populates="recommendations")

    def to_dict(self):
        return {
            "rank":            self.rank,
            "material_name":   self.material_name,
            "material_type":   self.material_type,
            "eco_score":       round(self.eco_score or 0, 2),
            "biodegradability": round(self.biodegradability or 0, 2),
            "co2_predicted":   round(self.co2_predicted or 0, 2),
            "co2_efficiency":  round(100 - (self.co2_predicted or 0), 2),
            "recyclability":   round(self.recyclability or 0, 2),
            "cost_predicted":  round(self.cost_predicted or 0, 2),
        }
