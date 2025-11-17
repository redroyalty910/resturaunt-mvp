import os
from flask import Flask, render_template, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "restaurant_system.db")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Function to for making item names URL-friendly
def slugify(name):
    return (
        name.lower()
            .replace(" & ", " ")   
            .replace("&", " ")
            .replace("'", "")      
            .replace(",", "")
            .replace(".", "")
            .replace("  ", " ")
            .strip()
            .replace(" ", "-")
    )

@app.route('/')
def index():
    return render_template('index.html')

# --- API: Return menu as JSON ---
@app.route('/api/menu')
def get_menu():
    query = text("SELECT item_name, category, price, description FROM Menu WHERE availability = 1")
    rows = db.session.execute(query).fetchall()

    menu = []
    for r in rows:
        filename = f"{slugify(r.item_name)}.jpg"
        menu.append({
            "item_name": r.item_name,
            "category": r.category,
            "price": float(r.price),
            "description": r.description or "",  
            "image": f"/images/{filename}"
        })
    return jsonify(menu)

# --- Route to serve images ---
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

if __name__ == '__main__':
    PORT = 8000
    HOST = "0.0.0.0"
    print(f"--- Flask Application Started Successfully ---")
    print(f"API endpoints available at: http://127.0.0.1:{PORT}/")
    app.run(debug=True, host=HOST, port=PORT)
