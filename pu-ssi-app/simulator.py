from flask import Flask, redirect, request, jsonify, session
from flask_cors import CORS
import requests
import secrets
import core  # <--- 导入新的核心逻辑模块

# --- App Setup ---
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app, supports_credentials=True) # 允许跨源请求传递凭证(cookies)

# --- FHIR Server and Auth Configuration ---
# 授权相关的URL和客户端ID仍然属于Web应用的一部分
AUTH_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/personas/provider/authorize"
TOKEN_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token"
CLIENT_ID = "1c0273a7-696e-40ae-bd9a-e593b7349ced"
REDIRECT_URI = "http://127.0.0.1:5080/callback"


# --- 1. Authorization Launch & 2. Callback Routes ---
# 这部分路由完全属于Web认证流程，保持不变
@app.route('/launch')
def launch():
    """启动授权流程，将用户重定向到Cerner登录页面。"""
    # ... 代码不变 ...
    state = secrets.token_urlsafe(16)
    session['state'] = state
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'openid fhirUser user/Patient.read user/Observation.read user/Condition.read user/Procedure.read user/MedicationRequest.read user/Encounter.read user/Device.read user/CarePlan.read user/AllergyIntolerance.read',
        'aud': core.FHIR_BASE_URL, # 使用从 core 模块导入的 FHIR_BASE_URL
        'state': state
    }
    auth_url = f"{AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """处理从Cerner返回的请求，交换code获取token，然后重定向到搜索页面。"""
    # ... 代码不变 ...
    if 'error' in request.args: return f"Authorization failed: {request.args.get('error')}", 400
    auth_code = request.args.get('code')
    if not auth_code: return "Error: No authorization code received.", 400
    if request.args.get('state') != session.get('state'): return "Error: State mismatch.", 400
    session.pop('state', None)
    token_params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID
    }
    response = requests.post(TOKEN_URL, data=token_params)
    response.raise_for_status()
    session['provider_access_token'] = response.json().get('access_token')
    print("Provider access token successfully obtained and stored.")
    return redirect("http://127.0.0.1:8000/search.html")


# --- 3. Patient Search API ---
# 这部分也属于Web应用的功能，保持不变
def parse_patient_bundle(bundle):
    """从Patient搜索结果(Bundle)中解析出病人列表"""
    # ... 代码不变 ...
    patients = []
    for entry in bundle.get('entry', []):
        res = entry.get('resource')
        if not res or res.get('resourceType') != 'Patient': continue
        name_data = res.get('name', [{}])[0]
        full_name = f"{' '.join(name_data.get('given', []))} {name_data.get('family', '')}"
        patients.append({ "id": res.get('id'), "name": full_name.strip(), "gender": res.get('gender'), "birthDate": res.get('birthDate') })
    return patients

@app.route('/api/search-patients')
def search_patients():
    """处理前端的病人搜索请求"""
    # ... 代码不变 ...
    provider_token = session.get('provider_access_token')
    patient_name = request.args.get('name')
    if not provider_token: return jsonify({"error": "Not authenticated"}), 401
    search_url = f"{core.FHIR_BASE_URL}/Patient"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    params = {"name": patient_name, "_count": 20}
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    patients = parse_patient_bundle(response.json())
    print(f"Found {len(patients)} patients for search term '{patient_name}'.")
    return jsonify(patients)


# --- 4. Get All Patient Data API (Refactored) ---
@app.route('/get_patient_data')
def get_patient_data():
    """
    获取选定病人的所有详细信息。
    此路由现在调用核心逻辑来完成工作。
    """
    provider_token = session.get('provider_access_token')
    patient_id = request.args.get('patient')
    if not provider_token or not patient_id:
        return jsonify({"error": "Not authenticated or patient ID missing"}), 401
    
    try:
        # 调用 core 模块中的函数来获取数据
        patient_data_bundle = core.get_patient_data_bundle(provider_token, patient_id)
        return jsonify(patient_data_bundle)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception fetching patient details: {e}")
        return jsonify({"error": "Failed to fetch patient details."}), 500


# --- 5. Prediction API (Refactored) ---
@app.route('/predict', methods=['POST'])
def predict():
    """
    处理预测请求。
    此路由现在调用核心逻辑来完成工作。
    """
    patient_data = request.json
    if not patient_data:
        return jsonify({"error": "No data provided for prediction."}), 400
        
    # 调用 core 模块中的函数来运行预测
    prediction_result = core.run_prediction(patient_data)
    
    return jsonify(prediction_result)


# --- Main Execution ---
if __name__ == '__main__':
    app.run(port=5080, debug=True)