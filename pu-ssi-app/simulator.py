from flask import Flask, redirect, request, jsonify, session
from flask_cors import CORS
import requests
import secrets
import core
from urllib.parse import unquote

# --- App Setup ---
app = Flask(__name__)
# 在开发中使用一个固定的字符串作为密钥，防止服务重启导致session失效
app.secret_key = 'a-very-secret-key-that-will-not-change'
CORS(app, supports_credentials=True, origins="http://127.0.0.1:8000")


# --- FHIR Server and Auth Configuration ---
AUTH_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/personas/provider/authorize"
TOKEN_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token"
CLIENT_ID = "1c0273a7-696e-40ae-bd9a-e593b7349ced"
REDIRECT_URI = "http://127.0.0.1:5080/callback"


# --- Helper Function to process FHIR Bundle ---
def process_fhir_bundle(bundle):
    """Parses a FHIR bundle for patients and pagination links."""
    patients = []
    for entry in bundle.get('entry', []):
        res = entry.get('resource')
        if not res or res.get('resourceType') != 'Patient': continue
        name_data = res.get('name', [{}])[0]
        full_name = f"{' '.join(name_data.get('given', []))} {name_data.get('family', '')}"
        patients.append({ "id": res.get('id'), "name": full_name.strip(), "gender": res.get('gender'), "birthDate": res.get('birthDate') })
    
    links = {}
    for link in bundle.get('link', []):
        if 'relation' in link and 'url' in link:
            links[link['relation']] = link['url']
            
    return {"patients": patients, "links": links}

# --- API Endpoints ---

@app.route('/api/search-patients')
def search_patients_api():
    """Initiates a new search for patients with detailed logging."""
    print("\n--- [API] Received request for /api/search-patients ---")
    
    provider_token = session.get('provider_access_token')
    if not provider_token:
        print("[ERROR] No 'provider_access_token' found in session. Aborting with 401.")
        return jsonify({"error": "Not authenticated or session expired. Please log in again."}), 401
    print("[INFO] Access token found in session.")
    
    patient_name = request.args.get('name')
    
    if not patient_name:
        print("[INFO] No search term provided. Returning empty result.")
        return jsonify({"patients": [], "links": {}})

    print(f"[INFO] Search term provided: '{patient_name}'")

    search_url = f"{core.FHIR_BASE_URL}/Patient"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    
    params = {
        "_count": 20, 
        "name": patient_name
        # 移除了排序参数，因为服务器不支持
        # "_sort": "-birthdate"
    }
    
    print(f"[INFO] Sending request to Cerner: {search_url} with params: {params}")
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        print(f"[INFO] Received response from Cerner with status code: {response.status_code}")
        response.raise_for_status()
        
        bundle = response.json()
        processed_data = process_fhir_bundle(bundle)
        
        print(f"[INFO] Successfully processed bundle. Found {len(processed_data['patients'])} patients.")
        print(f"[INFO] Pagination links found: {list(processed_data['links'].keys())}")
        
        return jsonify(processed_data)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception during request to Cerner: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-patient-page')
def get_patient_page_api():
    """Fetches a specific page of patient results with detailed logging."""
    print("\n--- [API] Received request for /api/get-patient-page ---")

    provider_token = session.get('provider_access_token')
    if not provider_token:
        print("[ERROR] No 'provider_access_token' found in session. Aborting with 401.")
        return jsonify({"error": "Not authenticated or session expired. Please log in again."}), 401
    print("[INFO] Access token found in session.")

    page_url = request.args.get('url')
    if not page_url:
        print("[ERROR] 'url' parameter is missing.")
        return jsonify({"error": "URL parameter is missing"}), 400
    
    decoded_url = unquote(page_url)
    print(f"[INFO] Sending request to Cerner for next page: {decoded_url}")
    
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    
    try:
        response = requests.get(decoded_url, headers=headers)
        print(f"[INFO] Received response from Cerner with status code: {response.status_code}")
        response.raise_for_status()
        
        bundle = response.json()
        processed_data = process_fhir_bundle(bundle)
        
        print(f"[INFO] Successfully processed bundle. Found {len(processed_data['patients'])} patients on this page.")
        return jsonify(processed_data)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception during request to Cerner: {e}")
        return jsonify({"error": str(e)}), 500

# --- Other routes remain the same ---
@app.route('/launch')
def launch():
    state = secrets.token_urlsafe(16)
    session['state'] = state
    auth_params = { 'response_type': 'code', 'client_id': CLIENT_ID, 'redirect_uri': REDIRECT_URI, 'scope': 'openid fhirUser user/Patient.read user/Observation.read user/Condition.read user/Procedure.read user/MedicationRequest.read user/Encounter.read user/Device.read user/CarePlan.read user/AllergyIntolerance.read', 'aud': core.FHIR_BASE_URL, 'state': state }
    auth_url = f"{AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    print("\n--- [AUTH] Received request for /callback ---")
    if 'error' in request.args: 
        print(f"[ERROR] Authorization failed: {request.args.get('error')}")
        return f"Authorization failed: {request.args.get('error')}", 400
    
    auth_code = request.args.get('code')
    if not auth_code: 
        print("[ERROR] No authorization code received.")
        return "Error: No authorization code received.", 400
    
    if request.args.get('state') != session.get('state'):
        print("[ERROR] State mismatch.")
        return "Error: State mismatch.", 400
    
    session.pop('state', None)
    token_params = { 'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': REDIRECT_URI, 'client_id': CLIENT_ID }
    
    try:
        response = requests.post(TOKEN_URL, data=token_params)
        response.raise_for_status()
        session['provider_access_token'] = response.json().get('access_token')
        print("[INFO] Provider access token successfully obtained and stored in session.")
        return redirect("http://127.0.0.1:8000/search.html")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to exchange code for token: {e}")
        return "Failed to get access token.", 500

@app.route('/get_patient_data')
def get_patient_data():
    provider_token = session.get('provider_access_token')
    patient_id = request.args.get('patient')
    if not provider_token or not patient_id: return jsonify({"error": "Not authenticated or patient ID missing"}), 401
    try:
        patient_data_bundle = core.get_patient_data_bundle(provider_token, patient_id)
        return jsonify(patient_data_bundle)
    except requests.exceptions.RequestException as e: return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    patient_data = request.json
    if not patient_data: return jsonify({"error": "No data provided for prediction."}), 400
    prediction_result = core.run_prediction(patient_data)
    return jsonify(prediction_result)

if __name__ == '__main__':
    app.run(port=5080, debug=True)
