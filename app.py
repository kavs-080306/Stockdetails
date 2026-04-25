from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
from pymongo import MongoClient
import certifi
from datetime import datetime
import pytz
import os
from twilio.rest import Client

app = Flask(__name__)
CORS(app)

# ---------------- CONFIGURATION ---------------- #
MONGO_URI = "mongodb+srv://kavs080306_db_user:StockAdmin123@stockdetails.jrzc143.mongodb.net/?appName=StockDetails"
IST = pytz.timezone('Asia/Kolkata')

# Twilio Credentials (Retrieved from Vercel Environment Variables)
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
ADMIN_WHATSAPP = "whatsapp:+919843060966"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

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

# ---------------- HELPERS ---------------- #

def send_whatsapp_alert(item_name, remaining_qty, category="General", person="Unknown"):
    """Sends a professionally formatted, customized WhatsApp alert."""
    if not TWILIO_SID or not TWILIO_AUTH_TOKEN:
        print("⚠️ Twilio credentials missing. Alert skipped.")
        return
    
    try:
        twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        
        # --- CUSTOMIZED MESSAGE BODY ---
        body_text = (
            f"🚨 *STOCK DEPLETION NOTICE*\n"
            f"----------------------------------\n"
            f"📦 *Product:* {item_name.title()}\n"
            f"🏷️ *Category:* {category}\n"
            f"🔢 *Available Now:* {remaining_qty}\n"
            f"👤 *Removed By:* {person}\n"
            f"⏰ *Time:* {datetime.now(IST).strftime('%I:%M %p, %d %b')}\n"
            f"----------------------------------\n"
            f"⚠️ *The inventory is critically low.* "
            f"Please arrange for a restock."
        )
        
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=body_text,
            to=ADMIN_WHATSAPP
        )
        print(f"✅ Customized WhatsApp alert sent for {item_name}")
    except Exception as e:
        print(f"❌ Twilio Error: {e}")

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
        timestamp = data.get('custom_date') or datetime.now(IST).isoformat()

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
    if data.get('role') not in ['admin', 'user']:
        return jsonify({'error': 'Unauthorized'}), 403

    name = str(data['name']).strip().lower()
    qty_to_remove = int(data['quantity'])
    item = stocks_col.find_one({"name": name})
    
    if item and item['quantity'] >= qty_to_remove:
        timestamp = data.get('custom_date') or datetime.now(IST).isoformat()

        stocks_col.update_one(
            {"name": name},
            {"$inc": {"quantity": -qty_to_remove}}
        )

        history_col.insert_one({
            'date_time': timestamp,
            'stock_name': name,
            'quantity': qty_to_remove,
            'person': data.get('person', 'Unknown'),
            'action': 'REMOVE'
        })

        # --- LOW STOCK ALERT CHECK ---
        updated_item = stocks_col.find_one({"name": name})
        if updated_item and updated_item['quantity'] < 3:
            send_whatsapp_alert(
                item_name=name, 
                remaining_qty=updated_item['quantity'],
                category=updated_item.get('category', 'General'),
                person=data.get('person', 'Unknown')
            )

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
