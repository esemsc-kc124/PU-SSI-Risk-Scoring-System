import requests
import json
import concurrent.futures
import datetime

# --- FHIR Server Configuration ---
FHIR_BASE_URL = "https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

def _fetch_recent_for_resource(token, patient_id, resource_type):
    """
    一个私有的辅助函数，其唯一职责是获取指定资源的最新记录（最多100条）。
    A private helper function whose only responsibility is to fetch the most recent records (up to 100) for a given resource type.
    """
    # 通过 _sort=-date 参数请求服务器按日期降序排列，这样第一页就是最新的数据
    # Request the server to sort by date descending using _sort=-date, so the first page contains the latest data.
    url = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}&_count=100&_sort=-date"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [Thread: {resource_type}] Fetching a single page of most recent data. ---")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        bundle = response.json()
        print(f"--- [Thread: {resource_type}] Finished. Found {len(bundle.get('entry', []))} entries.")
        return bundle
    except requests.exceptions.RequestException as e:
        # 如果服务器不支持排序，它可能会报错。我们捕获这个错误并尝试不带排序参数的请求。
        # If the server doesn't support sorting, it might error. We catch this and try a request without sorting.
        if "sort" in str(e).lower():
            print(f"[WARN] Sorting by date not supported for {resource_type}. Fetching without sorting.")
            try:
                url_no_sort = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}&_count=100"
                response = requests.get(url_no_sort, headers=headers)
                response.raise_for_status()
                bundle = response.json()
                print(f"--- [Thread: {resource_type}] Finished (no sort). Found {len(bundle.get('entry', []))} entries.")
                return bundle
            except requests.exceptions.RequestException as e2:
                print(f"[ERROR in Thread: {resource_type}] Failed to fetch data even without sorting: {e2}")
        else:
            print(f"[ERROR in Thread: {resource_type}] Failed to fetch data: {e}")

        # 如果任何请求失败，都返回一个标准的空Bundle结构
        # If any request fails, return a standard empty Bundle structure.
        return {"resourceType": "Bundle", "entry": [], "total": 0}

def get_procedure_display_text(resource):
    """一个更健壮的函数，用于从Procedure资源中提取可读的描述。"""
    if not resource: return "Invalid Procedure resource"
    if resource.get("code", {}).get("text"): return resource["code"]["text"]
    if resource.get("code", {}).get("coding") and len(resource["code"]["coding"]) > 0:
        return resource["code"]["coding"][0].get("display", "Procedure without text display")
    return "Procedure with no description"

def get_patient_data_bundle(provider_token, patient_id):
    """并行获取选定病人的所有详细信息。"""
    patient_url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    patient_res = requests.get(patient_url, headers=headers)
    patient_res.raise_for_status()
    
    all_resources = ["Observation", "Condition", "Procedure", "Encounter", "CarePlan", "Device", "AllergyIntolerance"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(all_resources)) as executor:
        future_to_resource = {
            executor.submit(_fetch_recent_for_resource, provider_token, patient_id, resource): resource 
            for resource in all_resources
        }
        
        results = {}
        for future in concurrent.futures.as_completed(future_to_resource):
            resource_type = future_to_resource[future]
            try:
                results[resource_type] = future.result()
            except Exception as exc:
                print(f"[ERROR] {resource_type} generated an exception: {exc}")
                results[resource_type] = {"entry": []}

    data = {
        "patient": patient_res.json(),
        "observations": results.get("Observation"),
        "conditions": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in results.get("Condition", {}).get('entry', [])],
        "procedures": [get_procedure_display_text(e.get('resource')) for e in results.get("Procedure", {}).get('entry', [])],
        "encounters": [e.get('resource', {}).get('type', [{}])[0].get('text', 'N/A') for e in results.get("Encounter", {}).get('entry', [])],
        "careplans": [e.get('resource', {}).get('description', 'N/A') for e in results.get("CarePlan", {}).get('entry', [])],
        "devices": [e.get('resource', {}).get('type', {}).get('text', 'N/A') for e in results.get("Device", {}).get('entry', [])],
        "allergies": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in results.get("AllergyIntolerance", {}).get('entry', [])],
    }
    return data

def run_prediction(patient_data):
    """接收病人数据，运行预测模型并返回结果"""
    print("Received data for prediction inside core logic.")

    # 假设预测结果
    risk_score = "75.3%"
    shap_values = [0.1, -0.05, 0.2]
    shap_features = ["Age", "BMI", "BP"]

    # 构造 Observation 资源
    now = datetime.datetime.utcnow().isoformat() + "Z"
    new_observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "99999-9",  # 你可以自定义一个code
                "display": "PU-SSI Risk Score and SHAP"
            }],
            "text": "PU-SSI Risk Score and SHAP"
        },
        "subject": patient_data.get("patient", {}).get("id", "Unknown"),
        "effectiveDateTime": now,
        "issued": now,
        "valueString": f"Risk Score: {risk_score}; SHAP: {dict(zip(
            shap_features, shap_values))}"
    }

    return {"risk_score": risk_score,
            "shap_values": shap_values,
            "shap_features": shap_features,
            "raw_observation_update": new_observation}
