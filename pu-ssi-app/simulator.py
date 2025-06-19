from flask import Flask, redirect, request, jsonify, session, send_from_directory
from flask_cors import CORS
import requests
import secrets
import core
from urllib.parse import unquote
import os # 导入os库来读取环境变量

# --- App Setup ---
app = Flask(__name__, static_folder='static') # 将 'static' 文件夹设置为静态文件目录
# 在开发中使用一个固定的字符串作为密钥，防止服务重启导致session失效
app.secret_key = 'a-very-secret-key-that-will-not-change'
# 不再限制origins，因为前端现在由同一个服务器提供
CORS(app, supports_credentials=True)


# --- FHIR Server and Auth Configuration ---
AUTH_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/personas/provider/authorize"
TOKEN_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token"
CLIENT_ID = "1c0273a7-696e-40ae-bd9a-e593b7349ced"

# --- 关键修改：智能地设置回调地址 ---
# 在云端部署时，我们会设置一个环境变量。在本地开发时，它会自动使用默认值。
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://127.0.0.1:5080/callback')


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

# --- API Endpoints (no changes needed here) ---

@app.route('/api/search-patients')
def search_patients_api():
    provider_token = session.get('provider_access_token')
    if not provider_token:
        return jsonify({"error": "Not authenticated or session expired. Please log in again."}), 401
    
    patient_name = request.args.get('name')
    if not patient_name:
        return jsonify({"patients": [], "links": {}})

    search_url = f"{core.FHIR_BASE_URL}/Patient"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    params = {"_count": 20, "name": patient_name}
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        processed_data = process_fhir_bundle(response.json())
        return jsonify(processed_data)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-patient-page')
def get_patient_page_api():
    provider_token = session.get('provider_access_token')
    if not provider_token:
        return jsonify({"error": "Not authenticated or session expired. Please log in again."}), 401
    
    page_url = request.args.get('url')
    if not page_url:
        return jsonify({"error": "URL parameter is missing"}), 400
    
    decoded_url = unquote(page_url)
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    
    try:
        response = requests.get(decoded_url, headers=headers)
        response.raise_for_status()
        processed_data = process_fhir_bundle(response.json())
        return jsonify(processed_data)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

# --- Auth Routes ---
@app.route('/launch')
def launch():
    state = secrets.token_urlsafe(16)
    session['state'] = state
    auth_params = { 'response_type': 'code', 'client_id': CLIENT_ID, 'redirect_uri': REDIRECT_URI, 'scope': 'openid fhirUser user/Patient.read user/Observation.read user/Condition.read user/Procedure.read user/MedicationRequest.read user/Encounter.read user/Device.read user/CarePlan.read user/AllergyIntolerance.read', 'aud': core.FHIR_BASE_URL, 'state': state }
    auth_url = f"{AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args: return f"Authorization failed: {request.args.get('error')}", 400
    auth_code = request.args.get('code')
    if not auth_code: return "Error: No authorization code received.", 400
    if request.args.get('state') != session.get('state'): return "Error: State mismatch.", 400
    session.pop('state', None)
    token_params = { 'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': REDIRECT_URI, 'client_id': CLIENT_ID }
    
    try:
        response = requests.post(TOKEN_URL, data=token_params)
        response.raise_for_status()
        session['provider_access_token'] = response.json().get('access_token')
        # --- 关键修改：重定向到相对路径，而不是写死的本地地址 ---
        return redirect("/search.html")
    except requests.exceptions.RequestException as e:
        return "Failed to get access token.", 500

# --- Prediction and Data Routes ---
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

# --- 新增的路由，用于提供前端HTML文件 ---
# --- NEW routes to serve frontend HTML files ---
@app.route('/')
def serve_root():
    # 当用户访问根目录时，返回 index.html
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    # 这个路由会提供所有在static文件夹里的文件，包括 search.html
    return send_from_directory('static', path)

if __name__ == '__main__':
    # 修改为监听0.0.0.0:8080以适应云端部署
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
