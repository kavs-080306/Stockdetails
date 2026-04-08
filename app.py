from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
from pymongo import MongoClient
import certifi
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ---------------- MONGODB SETUP ---------------- #
# 1. Replace <password> with your actual database user password
# 2. Use your actual Cluster ID instead of 'xxxx'
MONGO_URI = "mongodb+srv://kavs080306_db_user:StockAdmin123@stockdetails.jrzc143.mongodb.net/?appName=StockDetails"

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client['office_inventory']
    stocks_col = db['stocks']
    history_col = db['history']
    
    # --- STEP 1: FORCE CONNECTION TEST ---
    client.admin.command('ping')
    print("✅ STEP 1: Connected to MongoDB Cloud!")
    
    # --- STEP 2: TEST WRITE ---
    db.connection_test.insert_one({"message": "Testing Write", "time": datetime.now()})
    print("✅ STEP 2: Database Write Test Passed!")

except Exception as e:
    print("--------------------------------------------------")
    print(f"❌ DATABASE ERROR: {e}")
    print("Check: 1. Password | 2. IP Whitelist (0.0.0.0/0) | 3. Internet")
    print("--------------------------------------------------")

# ---------------- AUTH DATA ---------------- #
users = [
    {"username": "admin", "password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"},
    {"username": "user", "password": hashlib.sha256("user123".encode()).hexdigest(), "role": "user"}
]

# ---------------- ROUTES ---------------- #

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

    # --- STEP 3: DEBUG THE DATA ARRIVING ---
    data = request.json
    print(f"📥 Incoming Stock Request: {data}")

    if data.get('role') != 'admin':
        print("⛔ BLOCKED: User tried to add stock without Admin role.")
        return jsonify({'error': 'Unauthorized: Admin only'}), 403

    try:
        # Clean data to avoid errors
        item_name = str(data['name']).strip()
        item_qty = int(data['quantity'])

        # Atomic Update
        result = stocks_col.update_one(
            {"name": item_name},
            {
                "$inc": {"quantity": item_qty},
                "$set": {
                    "category": data.get('category', 'General'),
                    "updatedAt": datetime.now().isoformat()
                }
            },
            upsert=True
        )
        print(f"💾 Cloud Update Success: {item_name} added.")
        return jsonify({'message': 'Stock updated successfully'}), 201
    
    except Exception as e:
        print(f"❌ Write Failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks/remove', methods=['POST'])
def remove_stock():
    data = request.json
    print(f"📤 Outgoing Stock Request: {data}")
    
    role = data.get('role')
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Unauthorized'}), 403

    name = data['name']
    qty_to_remove = int(data['quantity'])

    item = stocks_col.find_one({"name": name})
    
    if item and item['quantity'] >= qty_to_remove:
        stocks_col.update_one(
            {"name": name},
            {"$inc": {"quantity": -qty_to_remove}}
        )

        history_col.insert_one({
            'date_time': datetime.now().isoformat(),
            'stock_name': name,
            'quantity': qty_to_remove,
            'person': data.get('person', 'Unknown'),
            'action': 'REMOVE'
        })
        print(f"✅ Removal Logged: {name} taken by {data.get('person')}")
        return jsonify({'message': 'Stock removed'})

    return jsonify({'error': 'Insufficient stock available'}), 400

@app.route('/api/history', methods=['GET'])
def get_history():
    logs = list(history_col.find({}, {'_id': 0}).sort('date_time', -1).limit(50))
    return jsonify(logs)

@app.route('/')
def home():
    return "Office Stock Cloud Backend is Running 🚀"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)