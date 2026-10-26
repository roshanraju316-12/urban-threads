import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-for-local-project")
app.config["DATABASE"] = os.path.join(app.instance_path, "urban_threads.db")
os.makedirs(app.instance_path, exist_ok=True)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        price REAL NOT NULL CHECK(price >= 0),
        image_url TEXT NOT NULL DEFAULT '',
        stock INTEGER NOT NULL DEFAULT 10,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Placed',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
    );
    """)
    admin = db.execute("SELECT id FROM users WHERE email = ?", ("admin@urbanthreads.local",)).fetchone()
    if not admin:
        db.execute(
            "INSERT INTO users (name, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            ("Store Admin", "admin@urbanthreads.local", generate_password_hash("Admin@123"))
        )
    count = db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
    if count == 0:
        sample_products = [
            ("Essential White Tee", "T-Shirts", "Everyday cotton T-shirt with a clean, relaxed fit.", 599, "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=85", 20),
            ("Classic Black Tee", "T-Shirts", "A versatile black tee made for daily wear.", 649, "https://images.unsplash.com/photo-1503341504253-dff4815485f1?auto=format&fit=crop&w=900&q=85", 20),
            ("Oxford Casual Shirt", "Shirts", "A crisp button-down shirt for smart casual outfits.", 1199, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=900&q=85", 12),
            ("Everyday Denim", "Jeans", "Classic denim with a comfortable modern fit.", 1499, "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=85", 10),
            ("Weekend Hoodie", "Hoodies", "Soft everyday hoodie with a minimal silhouette.", 1699, "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=900&q=85", 10),
            ("Neutral Overshirt", "Shirts", "Layer-friendly overshirt in a timeless neutral tone.", 1399, "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=900&q=85", 8),
        ]
        db.executemany(
            "INSERT INTO products (name, category, description, price, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)",
            sample_products
        )
    db.commit()

@app.before_request
def ensure_database():
    init_db()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in as admin.", "info")
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            flash("Admin access only.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def shared_template_values():
    cart = session.get("cart", {})
    return {"cart_count": sum(int(q) for q in cart.values())}

@app.route("/")
def home():
    db = get_db()
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
        params.extend([f"%{q}%"] * 3)
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"
    products = db.execute(sql, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return render_template("home.html", products=products, categories=categories, q=q, selected_category=category)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("home"))
    return render_template("product.html", product=product)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name and email, and use a password with at least 6 characters.", "error")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password))
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered. Please log in.", "error")
            return render_template("register.html")
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {user['name']}!", "success")
            target = request.args.get("next")
            if target and target.startswith("/") and not target.startswith("//"):
                return redirect(target)
            return redirect(url_for("admin_dashboard" if user["is_admin"] else "home"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

def get_cart_items():
    db = get_db()
    cart = session.get("cart", {})
    items, total = [], 0
    for product_id, quantity in cart.items():
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product:
            qty = max(1, int(quantity))
            subtotal = product["price"] * qty
            items.append({"product": product, "quantity": qty, "subtotal": subtotal})
            total += subtotal
    return items, total

@app.route("/cart")
def cart():
    items, total = get_cart_items()
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("home"))
    if product["stock"] < 1:
        flash("This product is out of stock.", "error")
        return redirect(request.referrer or url_for("home"))
    cart_data = session.get("cart", {})
    key = str(product_id)
    cart_data[key] = min(int(cart_data.get(key, 0)) + 1, product["stock"])
    session["cart"] = cart_data
    flash("Added to your cart.", "success")
    return redirect(request.referrer or url_for("home"))

@app.route("/cart/update", methods=["POST"])
def update_cart():
    cart_data = session.get("cart", {})
    db = get_db()
    for product_id in list(cart_data.keys()):
        raw = request.form.get(f"quantity_{product_id}")
        if raw is None:
            continue
        try:
            qty = int(raw)
        except ValueError:
            qty = 1
        product = db.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
        if qty <= 0 or not product:
            cart_data.pop(product_id, None)
        else:
            cart_data[product_id] = min(qty, product["stock"])
    session["cart"] = cart_data
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items, total = get_cart_items()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("home"))
    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        if not name or not phone or not address:
            flash("Please fill in all delivery details.", "error")
            return render_template("checkout.html", items=items, total=total)
        db = get_db()
        try:
            db.execute("BEGIN")
            # Re-check stock immediately before placing the order.
            for item in items:
                latest = db.execute("SELECT stock FROM products WHERE id = ?", (item["product"]["id"],)).fetchone()
                if not latest or latest["stock"] < item["quantity"]:
                    raise ValueError(f"Not enough stock for {item['product']['name']}. Please update your cart.")
            cur = db.execute(
                "INSERT INTO orders (user_id, customer_name, phone, address, total) VALUES (?, ?, ?, ?, ?)",
                (session["user_id"], name, phone, address, total)
            )
            order_id = cur.lastrowid
            for item in items:
                p = item["product"]
                db.execute(
                    "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) VALUES (?, ?, ?, ?, ?)",
                    (order_id, p["id"], p["name"], item["quantity"], p["price"])
                )
                db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["quantity"], p["id"]))
            db.commit()
        except ValueError as e:
            db.rollback()
            flash(str(e), "error")
            return redirect(url_for("cart"))
        session["cart"] = {}
        flash("Order placed successfully with Cash on Delivery.", "success")
        return redirect(url_for("order_detail", order_id=order_id))
    return render_template("checkout.html", items=items, total=total)

@app.route("/orders")
@login_required
def orders():
    rows = get_db().execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    return render_template("orders.html", orders=rows)

@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order or (order["user_id"] != session["user_id"] and not session.get("is_admin")):
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    return render_template("order_detail.html", order=order, items=items)

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = db.execute("""
        SELECT orders.*, users.email FROM orders
        JOIN users ON users.id = orders.user_id ORDER BY orders.id DESC
    """).fetchall()
    stats = {
        "products": db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"],
        "orders": db.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"],
        "customers": db.execute("SELECT COUNT(*) AS n FROM users WHERE is_admin = 0").fetchone()["n"],
        "revenue": db.execute("SELECT COALESCE(SUM(total), 0) AS n FROM orders").fetchone()["n"],
    }
    return render_template("admin.html", products=products, orders=orders, stats=stats)

@app.route("/admin/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except ValueError:
            flash("Price and stock must be numbers.", "error")
            return render_template("product_form.html", product=None)
        if not name or not category or price < 0 or stock < 0:
            flash("Enter valid product details.", "error")
            return render_template("product_form.html", product=None)
        get_db().execute(
            "INSERT INTO products (name, category, description, price, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)",
            (name, category, description, price, image_url, stock)
        )
        get_db().commit()
        flash("Product added.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("product_form.html", product=None)

@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except ValueError:
            flash("Price and stock must be numbers.", "error")
            return render_template("product_form.html", product=product)
        if not name or not category or price < 0 or stock < 0:
            flash("Enter valid product details.", "error")
            return render_template("product_form.html", product=product)
        db.execute(
            "UPDATE products SET name=?, category=?, description=?, price=?, image_url=?, stock=? WHERE id=?",
            (name, category, description, price, image_url, stock, product_id)
        )
        db.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("product_form.html", product=product)

@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("status", "")
    allowed = {"Placed", "Processing", "Shipped", "Delivered", "Cancelled"}
    if status not in allowed:
        flash("Invalid order status.", "error")
    else:
        db = get_db()
        db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        db.commit()
        flash("Order status updated.", "success")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
