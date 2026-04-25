from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
from pymongo import MongoClient
import certifi
from datetime import datetime
import pytz  # Handles timezone conversion

app = Flask(__name__)
CORS(app)

# ---------------- CONFIGURATION ---------------- #
MONGO_URI = "mongodb+srv://kavs080306_db_user:StockAdmin123@stockdetails.jrzc143.mongodb.net/?appName=StockDetails"
IST = pytz.timezone('Asia/Kolkata')  # Define India Standard Time

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['office_inventory']
    stocks_col = db['stocks']
    history_col = db['history']
    client.admin.command('ping')
    print("✅ Connected to MongoDB Cloud (IST Mode)!")
except Exception as e:
    print(f"❌ DATABASE ERROR: {e}")

# ---------------- AUTH DATA ---------------- #
users = [
    {"username": "Ganesh", "password": hashlib.sha256("gane333".encode()).hexdigest(), "role": "admin"},
    {"username": "Silver", "password": hashlib.sha256("sss1371".encode()).hexdigest(), "role": "user"}
]

# ---------------- ROUTES ---------------- #

@app.route('/')
def home():
    return "Office Stock Cloud Backend (IST) is Running 🚀"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = hashlib.sha256(data.get('password').encode()).hexdigest()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return jsonify({"message": "Login successful", "role": user['role']})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/stocks', methods=['GET', 'POST'])
def handle_stocks():
    if request.method == 'GET':
        all_stocks = list(stocks_col.find({}, {'_id': 0}))
        return jsonify({'stocks': all_stocks})

    data = request.json
    if data.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        item_name = str(data['name']).strip().lower()
        item_qty = int(data['quantity'])
        
        # Capture current time in IST or use custom date if provided
        if data.get('custom_date'):
            timestamp = data['custom_date']
        else:
            timestamp = datetime.now(IST).isoformat()

        # 1. Update/Add the stock count
        stocks_col.update_one(
            {"name": item_name},
            {
                "$inc": {"quantity": item_qty},
                "$set": {
                    "category": data.get('category', 'General'),
                    "updatedAt": timestamp
                }
            },
            upsert=True
        )

        # 2. LOG THE ADDITION TO HISTORY
        history_col.insert_one({
            'date_time': timestamp,
            'stock_name': item_name,
            'quantity': item_qty,
            'person': 'Admin (Refill)', 
            'action': 'ADD'
        })

        return jsonify({'message': 'Stock updated and logged'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks/remove', methods=['POST'])
def remove_stock():
    data = request.json
    role = data.get('role')
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Unauthorized'}), 403

    name = str(data['name']).strip().lower()
    qty_to_remove = int(data['quantity'])
    item = stocks_col.find_one({"name": name})
    
    if item and item['quantity'] >= qty_to_remove:
        # Use custom date if provided, else use current IST time
        if data.get('custom_date'):
            timestamp = data['custom_date']
        else:
            timestamp = datetime.now(IST).isoformat()

        stocks_col.update_one(
            {"name": name},
            {"$inc": {"quantity": -qty_to_remove}}
        )

        # LOG THE REMOVAL TO HISTORY
        history_col.insert_one({
            'date_time': timestamp,
            'stock_name': name,
            'quantity': qty_to_remove,
            'person': data.get('person', 'Unknown'),
            'action': 'REMOVE'
        })
        return jsonify({'message': 'Stock removed'})

    return jsonify({'error': 'Insufficient stock'}), 400


@app.route('/api/history', methods=['GET'])
def get_history():
    logs = list(history_col.find({}, {'_id': 0}).sort('date_time', -1).limit(50))
    return jsonify(logs)

@app.route('/api/admin/clear', methods=['POST'])
def clear_database():
    data = request.json
    if not data or data.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    try:
        stocks_col.delete_many({})
        history_col.delete_many({})
        return jsonify({"message": "Database cleared"}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel app object
app = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
