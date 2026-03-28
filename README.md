# 🌱 EcoPackAI – Sustainable Packaging Recommendation System

EcoPackAI is a machine learning-powered web application that recommends eco-friendly packaging materials based on environmental impact metrics such as biodegradability, CO₂ emissions, recyclability, and cost.

---

## 🚀 Features

- 🔍 Intelligent packaging recommendation using ML models (XGBoost, Random Forest)
- 🌱 Sustainability-focused analysis (CO₂, biodegradability, recyclability)
- 📊 Interactive dashboard with data visualizations
- 📁 Export reports in Excel and PDF
- 🗄️ PostgreSQL integration for storing user queries and results
- 🌐 Full-stack web application (Frontend + Backend)

---

## 🧠 Machine Learning Models

- XGBoost
- Random Forest

Models are trained to predict the most suitable packaging material based on environmental and cost-related features.

---

## 🛠️ Tech Stack

- **Language:** Python
- **Libraries:** Pandas, NumPy, Matplotlib, Scikit-learn
- **Backend:** Flask / Django
- **Frontend:** HTML, CSS, JavaScript
- **Database:** PostgreSQL

---

## ⚙️ How It Works

1. User enters product details
2. Data is processed and sent to ML models
3. Model predicts best packaging material
4. Results displayed on UI
5. Data stored in PostgreSQL
6. Dashboard visualizes data
7. Reports can be exported

---

## 📊 Dashboard

- Bar charts and visual analytics
- Displays user queries and predictions
- Export functionality (Excel/PDF)

---

## 📦 Installation

```bash
git clone https://github.com/your-username/ecopackai.git
cd ecopackai
pip install -r requirements.txt
python app.py
