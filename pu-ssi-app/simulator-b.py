from flask import Flask, redirect, request, jsonify, session
from flask_cors import CORS
import requests
import secrets

# --- App Setup ---
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
# 允许跨源请求传递凭证(cookies)
CORS(app, supports_credentials=True)

# --- FHIR Server Configuration ---
# 使用我们最终确定的 Provider (医护人员) 流程地址
FHIR_BASE_URL = "https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
AUTH_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/personas/provider/authorize"
TOKEN_URL = "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token"
CLIENT_ID = "1c0273a7-696e-40ae-bd9a-e593b7349ced"
REDIRECT_URI = "http://127.0.0.1:5080/callback"


# --- 1. Authorization Launch Route ---
@app.route('/launch')
def launch():
    """
    启动授权流程，将用户重定向到Cerner登录页面。
    """
    state = secrets.token_urlsafe(16)
    session['state'] = state
    
    # 这是最终正确的参数字典：不使用launch, 使用openid和fhirUser来识别医护人员
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        # 使用'user/'前缀请求医护人员级别的权限
        'scope': 'openid fhirUser user/Patient.read user/Observation.read user/Condition.read user/Procedure.read user/MedicationRequest.read user/Encounter.read user/Device.read user/CarePlan.read user/AllergyIntolerance.read',
        'aud': FHIR_BASE_URL,
        'state': state
    }
    
    auth_url = f"{AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    return redirect(auth_url)


# --- 2. Callback Route ---
@app.route('/callback')
def callback():
    """
    处理从Cerner返回的请求，交换code获取token，然后重定向到搜索页面。
    """
    if 'error' in request.args:
        return f"Authorization failed: {request.args.get('error')}", 400

    auth_code = request.args.get('code')
    if not auth_code:
        return "Error: No authorization code received.", 400
        
    if request.args.get('state') != session.get('state'):
        return "Error: State mismatch.", 400
    session.pop('state', None)

    token_params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID
    }
    
    response = requests.post(TOKEN_URL, data=token_params)
    response.raise_for_status() # 如果交换失败，将直接抛出异常

    # 成功获取医护人员的访问令牌，并存入session
    session['provider_access_token'] = response.json().get('access_token')
    print("Provider access token successfully obtained and stored.")

    # 重定向到我们自己开发的病人搜索页面
    return redirect("http://127.0.0.1:8000/search.html")


# --- 3. Patient Search API ---
def parse_patient_bundle(bundle):
    """从Patient搜索结果(Bundle)中解析出病人列表"""
    patients = []
    for entry in bundle.get('entry', []):
        res = entry.get('resource')
        if not res or res.get('resourceType') != 'Patient':
            continue
        
        name_data = res.get('name', [{}])[0]
        full_name = f"{' '.join(name_data.get('given', []))} {name_data.get('family', '')}"
        
        patients.append({
            "id": res.get('id'),
            "name": full_name.strip(),
            "gender": res.get('gender'),
            "birthDate": res.get('birthDate')
        })
    return patients

@app.route('/api/search-patients')
def search_patients():
    """处理前端的病人搜索请求"""
    provider_token = session.get('provider_access_token')
    patient_name = request.args.get('name')
    if not provider_token: return jsonify({"error": "Not authenticated"}), 401
    
    search_url = f"{FHIR_BASE_URL}/Patient"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    params = {"name": patient_name, "_count": 20} # _count 限制返回最多20条结果
    
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status() # 确保请求成功
    
    patients = parse_patient_bundle(response.json())
    print(f"Found {len(patients)} patients for search term '{patient_name}'.")
    return jsonify(patients)


# --- 4. Get All Patient Data API ---
def fetch_fhir_resource(token, patient_id, resource_type):
    """一个辅助函数，用于获取并解析指定病人的资源列表"""
    url = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        bundle = response.json()
        # 从Bundle中提取可读的描述文本，如果text不存在则返回'No Description'
        items = [
            entry.get('resource', {}).get('code', {}).get('text', 'No Description') 
            for entry in bundle.get('entry', [])
        ]
        return items
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {resource_type} for patient {patient_id}: {e}")
        return []

@app.route('/get_patient_data')
def get_patient_data():
    """获取选定病人的所有详细信息"""
    provider_token = session.get('provider_access_token')
    patient_id = request.args.get('patient')
    if not provider_token or not patient_id:
        return jsonify({"error": "Not authenticated or patient ID missing"}), 401
    
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    
    try:
        # 获取核心 Patient 和 Observation 资源
        patient_res = requests.get(f"{FHIR_BASE_URL}/Patient/{patient_id}", headers=headers)
        patient_res.raise_for_status()
        
        obs_res = requests.get(f"{FHIR_BASE_URL}/Observation?patient={patient_id}&_count=100", headers=headers)
        obs_res.raise_for_status()

        # 构建最终返回给前端的JSON对象
        data = {
            "patient": patient_res.json(),
            "observations": obs_res.json(),
            "conditions": fetch_fhir_resource(provider_token, patient_id, "Condition"),
            "procedures": fetch_fhir_resource(provider_token, patient_id, "Procedure"),
            "encounters": fetch_fhir_resource(provider_token, patient_id, "Encounter"),
            "careplans": fetch_fhir_resource(provider_token, patient_id, "CarePlan"),
            "devices": fetch_fhir_resource(provider_token, patient_id, "Device"),
            "allergies": fetch_fhir_resource(provider_token, patient_id, "AllergyIntolerance"),
        }
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception fetching patient details: {e}")
        return jsonify({"error": "Failed to fetch patient details."}), 500

# --- 5. Prediction API (Placeholder) ---
@app.route('/predict', methods=['POST'])
def predict():
    """处理预测请求的占位符"""
    # 在这里，你可以接收前端发来的 globalPatientData,
    # 然后调用你的机器学习模型进行计算。
    # data = request.json
    print("Received data for prediction.")
    
    # 返回一个假的预测结果
    return jsonify({"risk_score": "75.3%"})


# --- Main Execution ---
if __name__ == '__main__':
    app.run(port=5080, debug=True)