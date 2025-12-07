from concurrent.futures import thread
import os
import webbrowser
import threading
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, jsonify, send_from_directory, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "restaurant_system_test.db")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.secret_key = "asecretkey" # this is used for session handling

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
    query = text("SELECT item_name, category, price, description, image_filename FROM Menu WHERE availability = 1")
    rows = db.session.execute(query).fetchall()

    menu = []
    for r in rows:
        filename = r.image_filename or f"{slugify(r.item_name)}.jpg"

        image_path = os.path.join(BASE_DIR, "static", "images", filename)
        if not os.path.exists(image_path):
            filename = "placeholder.jpg"

        menu.append({
            "item_name": r.item_name,
            "category": r.category,
            "price": float(r.price),
            "description": r.description or "",  
            "image": f"/images/{filename}"
        })
    return jsonify(menu)

@app.route('/api/place_order', methods=['POST'])
def place_order():
    data = request.get_json()

    customer_name = data.get('name')
    customer_phone = data.get('phone')
    customer_address = data.get('address') or None 
    order_items = data.get('items')
    
    if not customer_name or not customer_phone or not order_items:
        return jsonify({"success": False, "message": "Missing required fields "}), 400

    # Insert customer 
    query = text("""
        INSERT INTO Customer (name, phone, address)
        VALUES (:name, :phone, :address)
    """)
    result = db.session.execute(query, {"name": customer_name, "phone": customer_phone, "address": customer_address})
    customer_id = result.lastrowid

    # Insert order
    total_amount = sum(item['price'] * item['quantity'] for item in order_items)
    query = text("""
        INSERT INTO `Order` (amount, status, C_ID, S_ID)
        VALUES (:amount, 'Pending', :cid, 1)
    """)
    result = db.session.execute(query, {"amount": total_amount, "cid": customer_id})
    order_id = result.lastrowid

    # Insert order details
    for item in order_items:
        query = text("""
            INSERT INTO OrderDetails (O_ID, M_ID, quantity)
            VALUES (:oid, :mid, :qty)
        """)
        # Map the frontend id to the M_ID in Menu
        menu_item = db.session.execute(
            text("SELECT M_ID FROM Menu WHERE LOWER(REPLACE(item_name, ' ', '-')) = :slug"),
            {"slug": item['id']}
        ).fetchone()
        if menu_item:
            db.session.execute(query, {"oid": order_id, "mid": menu_item.M_ID, "qty": item['quantity']})

    db.session.commit()
    return jsonify({"success": True, "message": "Order placed successfully!"})

def open_browser():
    time.sleep(1)
    webbrowser.open_new(f'http://127.0.0.1:{PORT}/')

# --- Route to serve images ---
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

# check if database updated for Customer, Order, and OrderDetails correctly
# go to http://127.0.0.1:8000/debug/orders

@app.route('/debug/orders')
def debug_orders():
    # Join Orders with Customers and OrderDetails
    rows = db.session.execute(text("""
        SELECT 
            o.O_ID, o.amount, o.status, 
            c.C_ID, c.name, c.phone, c.address, 
            od.M_ID, od.quantity
        FROM `Order` o
        JOIN Customer c ON o.C_ID = c.C_ID
        LEFT JOIN OrderDetails od ON o.O_ID = od.O_ID
    """)).fetchall()

    # Convert each row to a dictionary
    result = [dict(r._mapping) for r in rows]

    return jsonify(result)

# --- Admin Login ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect('admin')

    if request.method == 'POST':
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        admin = db.session.execute(
            text("SELECT * FROM Admin WHERE username = :username"),
            {"username": username}
        ).fetchone()

        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            return jsonify({"success": True, "message": "Logged in successfully!"})
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

    return render_template('admin_login.html')


# --- Admin Logout ---
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')


# --- Admin Panel Page ---
@app.route('/admin')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    return render_template('admin_panel.html')


# --- Admin: Fetch All Menu Items ---
@app.route('/api/admin/menu')
def admin_get_menu():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    rows = db.session.execute(text("SELECT * FROM Menu")).fetchall()
    items = [dict(r._mapping) for r in rows]
    return jsonify(items)


# --- Admin: Add Menu Item ---
@app.route('/api/admin/add_item', methods=['POST'])
def admin_add_item():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    name = data.get("item_name")
    category = data.get("category")
    price = data.get("price")
    description = data.get("description") or ""
    image_filename = data.get("image_filename") or f"{slugify(name)}.jpg"
    availability = data.get("availability", 1)

    if not name or not category or price is None:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    db.session.execute(
        text("""
            INSERT INTO Menu (item_name, category, price, description, image_filename, availability)
            VALUES (:name, :category, :price, :description, :image_filename, :availability)
        """), {
            "name": name,
            "category": category,
            "price": price,
            "description": description,
            "image_filename": image_filename,
            "availability": availability
        }
    )
    db.session.commit()
    return jsonify({"success": True, "message": "Menu item added successfully!"})


# --- Admin: Edit Menu Item ---
@app.route('/api/admin/edit_item/<int:item_id>', methods=['POST'])
def admin_edit_item(item_id):
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json()
    db.session.execute(
        text("""
            UPDATE Menu SET
                item_name = :name,
                category = :category,
                price = :price,
                description = :description,
                image_filename = :image,
                availability = :avail
            WHERE M_ID = :id
        """), {
            "name": data.get("item_name"),
            "category": data.get("category"),
            "price": data.get("price"),
            "description": data.get("description") or "",
            "image": data.get("image_filename") or f"{slugify(data.get('item_name'))}.jpg",
            "avail": data.get("availability", 1),
            "id": item_id
        }
    )
    db.session.commit()
    return jsonify({"success": True, "message": "Menu item updated!"})


# --- Admin: Delete Menu Item ---
@app.route('/api/admin/delete_item/<int:item_id>', methods=['DELETE'])
def admin_delete_item(item_id):
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    db.session.execute(text("DELETE FROM Menu WHERE M_ID = :id"), {"id": item_id})
    db.session.commit()
    return jsonify({"success": True, "message": "Menu item deleted!"})



if __name__ == '__main__':
    PORT = 8000
    HOST = "0.0.0.0"
    print(f"--- Flask Application Started Successfully ---")
    print(f"API endpoints available at: http://127.0.0.1:{PORT}/")

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        webbrowser.open_new(f'http://127.0.0.1:{PORT}/')


    app.run(debug=True, host=HOST, port=PORT)
