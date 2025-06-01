# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow requests from any origin (for dev)

@app.route('/')
def home():
    return 'PU/SSI Risk Scoring Flask Backend is Running'

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        print("[INFO] Received data:", data)

        # --- MOCK prediction logic ---
        # In the real app, replace this with ML model inference
        risk_score = 0.78

        return jsonify({
            "risk_score": risk_score,
            "status": "success"
        })
    except Exception as e:
        print("[ERROR] Prediction failed:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5050)
