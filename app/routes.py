from flask import Blueprint, request, jsonify, render_template, current_app, send_file
from app import db
from app.models import QueryHistory, Recommendation
from sqlalchemy import func
import pandas as pd
import io, json
from datetime import datetime, timedelta

main = Blueprint("main", __name__)


# ── Helper ────────────────────────────────────────────────────────
def _engine():
    return current_app.ml_engine


def _error(msg, code=400):
    return jsonify({"success": False, "error": msg}), code


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@main.route("/")
def index():
    return render_template("index.html")


@main.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API: RECOMMENDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@main.route("/api/recommend", methods=["POST"])
def recommend():
    """
    POST /api/recommend
    Body: { "product": "Lotion" }
    Returns: ranked top-3 packaging materials with env scores + ML predictions
    """
    data = request.get_json(silent=True) or {}
    product = (data.get("product") or "").strip()

    if not product:
        return _error("'product' field is required.")

    result = _engine().predict(product, top_n=3)

    if "error" in result:
        return _error(result["error"], 404)

    # Persist to PostgreSQL
    # Persist to PostgreSQL
    try:
        query = QueryHistory(
            product_name  = product,
            industry      = data.get("industry", ""),
            top_material  = result["recommendations"][0]["material_name"],
            top_eco_score = result["recommendations"][0]["eco_score"],
        )
        db.session.add(query)
        db.session.flush()

        for rec in result["recommendations"]:
            db.session.add(Recommendation(
                query_id         = query.id,
                rank             = rec["rank"],
                material_name    = rec["material_name"],
                eco_score        = rec["eco_score"],
                biodegradability = rec["biodegradability"],
                co2_predicted    = rec["co2_predicted"],
                recyclability    = rec["recyclability"],
                cost_predicted   = rec["cost_predicted"],
            ))

        db.session.commit()
        result["query_id"] = query.id
    except Exception as e:
        db.session.rollback()
        print(f"DB Error: {e}")
        result["query_id"] = 0

    return jsonify({"success": True, **result})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API: PRODUCT & MATERIAL LISTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@main.route("/api/products", methods=["GET"])
def list_products():
    return jsonify({"products": _engine().available_products()})


@main.route("/api/materials", methods=["GET"])
def list_materials():
    stats = _engine().material_stats
    return jsonify({
        "materials": stats.to_dict(orient="records")
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API: QUERY HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@main.route("/api/history", methods=["GET"])
def history():
    try:
        limit  = min(int(request.args.get("limit",  50)), 200)
        offset = int(request.args.get("offset", 0))
        rows   = (QueryHistory.query
                  .order_by(QueryHistory.queried_at.desc())
                  .limit(limit).offset(offset).all())
        return jsonify({"history": [r.to_dict() for r in rows]})
    except Exception as e:
        print(f"History error: {e}")
        return jsonify({"history": []})


@main.route("/api/history/<int:query_id>", methods=["GET"])
def history_detail(query_id):
    q = QueryHistory.query.get_or_404(query_id)
    result = q.to_dict()
    result["recommendations"] = [r.to_dict() for r in q.recommendations]
    return jsonify(result)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API: BUSINESS INTELLIGENCE DASHBOARD DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@main.route("/api/dashboard", methods=["GET"])
def dashboard_data():
    try:
        BASELINE_CO2  = 50.0
        BASELINE_COST = 6.10

        recs = db.session.query(Recommendation).all()

        if not recs:
            return jsonify({
                "total_queries":     0,
                "co2_reduction_pct": 0,
                "cost_savings_pct":  0,
                "avg_eco_score":     0,
                "top_materials":     [],
                "daily_trend":       [],
                "eco_score_dist":    [
                    {"label": "Poor (<40)",    "count": 0},
                    {"label": "Fair (40-55)",  "count": 0},
                    {"label": "Good (55-70)",  "count": 0},
                    {"label": "Excellent (70+)","count": 0},
                ],
            })

        df = pd.DataFrame([{
            "material_name":  r.material_name,
            "eco_score":      r.eco_score or 0,
            "co2_predicted":  r.co2_predicted or 0,
            "cost_predicted": r.cost_predicted or 0,
            "rank":           r.rank,
        } for r in recs])

        top1 = df[df["rank"] == 1]
        avg_co2  = top1["co2_predicted"].mean()  if not top1.empty else BASELINE_CO2
        avg_cost = top1["cost_predicted"].mean() if not top1.empty else BASELINE_COST

        co2_reduction_pct  = round((BASELINE_CO2  - avg_co2)  / BASELINE_CO2  * 100, 1)
        cost_savings_pct   = round((BASELINE_COST - avg_cost) / BASELINE_COST * 100, 1)

        top_mats = (top1.groupby("material_name")
                        .size()
                        .sort_values(ascending=False)
                        .head(5)
                        .reset_index(name="count")
                        .to_dict(orient="records"))

        try:
            thirty_ago = datetime.utcnow() - timedelta(days=30)
            daily = (db.session.query(
                         func.date(QueryHistory.queried_at).label("day"),
                         func.count().label("count"))
                     .filter(QueryHistory.queried_at >= thirty_ago)
                     .group_by(func.date(QueryHistory.queried_at))
                     .order_by(func.date(QueryHistory.queried_at))
                     .all())
            daily_trend = [{"day": str(d.day), "count": d.count} for d in daily]
        except:
            daily_trend = []

        bins   = [0, 40, 55, 70, 100]
        labels = ["Poor (<40)", "Fair (40-55)", "Good (55-70)", "Excellent (70+)"]
        df["bucket"] = pd.cut(df["eco_score"], bins=bins, labels=labels, right=False)
        eco_dist = df["bucket"].value_counts().reindex(labels, fill_value=0)
        eco_score_dist = [{"label": l, "count": int(eco_dist[l])} for l in labels]

        total_queries = db.session.query(func.count(QueryHistory.id)).scalar() or 0

        return jsonify({
            "total_queries":     total_queries,
            "co2_reduction_pct": co2_reduction_pct,
            "cost_savings_pct":  cost_savings_pct,
            "avg_eco_score":     round(top1["eco_score"].mean(), 1) if not top1.empty else 0,
            "top_materials":     top_mats,
            "daily_trend":       daily_trend,
            "eco_score_dist":    eco_score_dist,
        })

    except Exception as e:
        print(f"Dashboard error: {e}")
        return jsonify({
            "total_queries": 0, "co2_reduction_pct": 0,
            "cost_savings_pct": 0, "avg_eco_score": 0,
            "top_materials": [], "daily_trend": [],
            "eco_score_dist": []
        })

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API: EXPORT REPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@main.route("/api/export/excel", methods=["GET"])
def export_excel():
    """Export all recommendations to .xlsx"""
    recs = db.session.query(Recommendation, QueryHistory).join(
        QueryHistory, Recommendation.query_id == QueryHistory.id
    ).all()

    rows = [{
        "Product":        q.product_name,
        "Queried At":     q.queried_at.strftime("%Y-%m-%d %H:%M"),
        "Rank":           r.rank,
        "Material":       r.material_name,
        "Eco Score":      round(r.eco_score or 0, 2),
        "Biodegradability %": round(r.biodegradability or 0, 2),
        "CO2 Predicted":  round(r.co2_predicted or 0, 2),
        "Recyclability %": round(r.recyclability or 0, 2),
        "Cost USD":       round(r.cost_predicted or 0, 2),
    } for r, q in recs]

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Recommendations")
    buf.seek(0)

    return send_file(
        buf,
        download_name=f"eco_packaging_report_{datetime.utcnow().strftime('%Y%m%d')}.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@main.route("/api/export/pdf", methods=["GET"])
def export_pdf():
    """Export sustainability summary report as PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                  fontSize=20, spaceAfter=6, textColor=colors.HexColor("#1a5276"))
    sub_style   = ParagraphStyle("Sub", parent=styles["Normal"],
                                  fontSize=11, textColor=colors.HexColor("#5d6d7e"), spaceAfter=20)

    story.append(Paragraph("Eco Packaging Sustainability Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%B %d, %Y')}", sub_style))

    # Summary stats
    total  = db.session.query(func.count(QueryHistory.id)).scalar() or 0
    story.append(Paragraph(f"<b>Total recommendations generated:</b> {total}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Top recommendations table
    recs = (db.session.query(Recommendation, QueryHistory)
            .join(QueryHistory, Recommendation.query_id == QueryHistory.id)
            .filter(Recommendation.rank == 1)
            .order_by(QueryHistory.queried_at.desc())
            .limit(20).all())

    if recs:
        story.append(Paragraph("<b>Top Recommended Materials (Rank #1)</b>", styles["Heading2"]))
        story.append(Spacer(1, 8))

        table_data = [["Product", "Material", "Eco Score", "CO₂", "Cost (USD)"]]
        for r, q in recs:
            table_data.append([
                q.product_name,
                r.material_name,
                f"{r.eco_score:.1f}",
                f"{r.co2_predicted:.1f}",
                f"${r.cost_predicted:.2f}",
            ])

        tbl = Table(table_data, colWidths=[110, 130, 70, 60, 75])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, 0), 10),
            ("FONTSIZE",   (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf2f8")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor("#aed6f1")),
            ("ALIGN",      (2, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tbl)

    doc.build(story)
    buf.seek(0)
    return send_file(
        buf,
        download_name=f"sustainability_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf",
        as_attachment=True,
        mimetype="application/pdf"
    )

