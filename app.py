from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import time
import os
import json

app = Flask(__name__)

# Initialize Firebase safely using Render Environment Variables or local JSON
try:
    firebase_json = os.environ.get("FIREBASE_CONFIG_JSON")
    if firebase_json:
        # Load credentials from Render environment variable
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    elif os.path.exists('serviceAccountKey.json'):
        # Fallback for local testing if file exists
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    else:
        print("⚠️ [WARNING] No Firebase credentials found!")
        
    db = firestore.client() if firebase_admin._apps else None
    print("🔥 [FIREBASE] Initialized successfully!")
except Exception as e:
    print(f"❌ [FIREBASE ERROR]: {e}")
    db = None

# ---------------------------------------------------------
# ROUTE 1: Receive Telemetry from Roblox Servers (POST)
# ---------------------------------------------------------
@app.route('/report', methods=['POST'])
def report_server():
    if not db:
        return jsonify({"error": "Database not initialized"}), 500
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    job_id = data.get('jobId')
    place_id = data.get('placeId')
    egg_type = data.get('eggType', 'Unknown Egg')
    rarity_score = data.get('rarityScore', 0)
    player_count = data.get('playerCount', 0)
    
    if not job_id or not place_id:
        return jsonify({"error": "Missing jobId or placeId"}), 400
        
    print(f"📥 [REPORT] Game: {place_id} | Server: {job_id} | Egg: {egg_type}")
        
    doc_ref = db.collection('active_servers').document(str(job_id))
    doc_ref.set({
        'placeId': place_id,
        'jobId': job_id,
        'eggType': egg_type,
        'rarityScore': rarity_score,
        'playerCount': player_count,
        'lastSeen': time.time()
    })
    
    return jsonify({"status": "success"}), 200

# ---------------------------------------------------------
# ROUTE 2: Get Active Servers for a Specific Game (GET)
# ---------------------------------------------------------
@app.route('/servers/<int:place_id>', methods=['GET'])
def get_servers(place_id):
    if not db:
        return jsonify({"error": "Database not initialized"}), 500
        
    docs = db.collection('active_servers').where('placeId', '==', place_id).stream()
    
    server_list = []
    current_time = time.time()
    
    for doc in docs:
        server_data = doc.to_dict()
        # Only include servers updated within the last 90 seconds
        if current_time - server_data.get('lastSeen', 0) < 90:
            server_list.append(server_data)
            
    server_list.sort(key=lambda x: x.get('rarityScore', 0), reverse=True)
    
    print(f"📤 [GET SERVERS] Returning {len(server_list)} server(s) for Game {place_id}")
    return jsonify({"servers": server_list}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
