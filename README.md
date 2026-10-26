# URBAN THREADS — Clothing E-commerce College Project

A beginner-friendly local e-commerce demo built with Python, Flask, HTML/CSS/JavaScript and SQLite.

## Features
- Product catalogue, search and category filtering
- Registration and login with hashed passwords
- Session-based shopping cart and quantity updates
- Checkout with Cash on Delivery (demo; no payment gateway)
- Customer order history and order details
- Admin dashboard for product CRUD and order status management
- SQLite database created automatically on first run with sample products

## Requirements
- Windows 10/11
- Python 3.10 or newer
- VS Code (recommended)

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `urban_threads` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:
   ```powershell
   python -m venv .venv
   ```
5. Activate it:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, you can run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and then `.\.venv\Scripts\python.exe app.py` instead.
6. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
7. Start the website:
   ```powershell
   python app.py
   ```
8. Open http://127.0.0.1:5000 in your browser.

## Demo admin login
- Email: `admin@urbanthreads.local`
- Password: `Admin@123`

Change the demo admin password and `SECRET_KEY` before any real deployment. This starter project is for local learning and college demonstration only.

## Database
SQLite is included with standard Python builds. The database file is created automatically at `instance/urban_threads.db`. You do not need to download MySQL for this version.

## Project structure
```text
urban_threads/
├── app.py
├── requirements.txt
├── README.md
├── instance/             # SQLite database is created here at runtime
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── home.html
    ├── product.html
    ├── login.html
    ├── register.html
    ├── cart.html
    ├── checkout.html
    ├── orders.html
    ├── order_detail.html
    ├── admin.html
    └── product_form.html
```
