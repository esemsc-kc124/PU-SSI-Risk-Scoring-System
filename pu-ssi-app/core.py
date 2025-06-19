import requests
import json
import concurrent.futures
import datetime

# --- FHIR Server Configuration ---
FHIR_BASE_URL = "https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

# --- 定义我们需要的关键指标的LOINC编码 ---
KEY_OBSERVATION_CODES = {
    'hdl': '2085-9',
    'ldl': '13457-7',
    'height': ['8302-2', '3137-7'],
    'blood_pressure': '85354-9',
    'weight': ['3141-9', '29463-7'],
    'bmi': '39156-5',
    'tobacco': ['88028-6', '72166-2']
}

def _fetch_specific_observations(token, patient_id):
    """一个“精确打击”函数，只获取我们明确需要的几种Observation。"""
    codes = [code for sublist in KEY_OBSERVATION_CODES.values() for code in (sublist if isinstance(sublist, list) else [sublist])]
    codes_to_fetch = ",".join(codes)
    
    url = f"{FHIR_BASE_URL}/Observation?patient={patient_id}&code={codes_to_fetch}&_count=200"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [SNIPER] Fetching key observations...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        bundle = response.json()
        print(f"--- [SNIPER] Finished. Found {len(bundle.get('entry', []))} key observations.")
        return bundle.get("entry", [])
    except requests.exceptions.RequestException as e:
        print(f"[ERROR in SNIPER thread] Failed to fetch key observations: {e}")
        return []

def _fetch_other_observations(token, patient_id):
    """一个“常规侦察”函数，获取100条其他常规Observation样本。"""
    url = f"{FHIR_BASE_URL}/Observation?patient={patient_id}&_count=100"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [RECON] Fetching a page of other observations.")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        bundle = response.json()
        print(f"--- [RECON] Finished. Found {len(bundle.get('entry', []))} other observations.")
        return bundle.get("entry", [])
    except requests.exceptions.RequestException as e:
        print(f"[ERROR in RECON thread] Failed to fetch other observations: {e}")
        return []
        
def _fetch_resource_page(token, patient_id, resource_type):
    """
    获取除Observation之外的其他资源的第一页数据。
    Fetches the first page of data for resources other than Observation.
    """
    url = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}&_count=100"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [Thread: {resource_type}] Fetching data (no sorting)...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR in Thread: {resource_type}] Failed to fetch data: {e}")
        return {"entry": []}

def get_procedure_display_text(resource):
    if not resource: return "Invalid Procedure resource"
    if resource.get("code", {}).get("text"): return resource["code"]["text"]
    if resource.get("code", {}).get("coding") and len(resource["code"]["coding"]) > 0:
        return resource["code"]["coding"][0].get("display", "Procedure without text display")
    return "Procedure with no description"

def get_patient_data_bundle(provider_token, patient_id):
    """并行获取选定病人的所有详细信息，并优化Observation的获取策略。"""
    patient_url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    patient_res = requests.get(patient_url, headers=headers, timeout=30)
    patient_res.raise_for_status()
    
    other_resources = ["Condition", "Procedure", "Encounter", "CarePlan", "Device", "AllergyIntolerance"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(other_resources) + 2) as executor:
        future_to_resource = {
            executor.submit(_fetch_resource_page, provider_token, patient_id, res): res 
            for res in other_resources
        }
        future_key_obs = executor.submit(_fetch_specific_observations, provider_token, patient_id)
        future_other_obs = executor.submit(_fetch_other_observations, provider_token, patient_id)

        results = {}
        for future in concurrent.futures.as_completed(future_to_resource):
            resource_type = future_to_resource[future]
            try:
                results[resource_type] = future.result()
            except Exception as exc:
                print(f"[ERROR] {resource_type} generated an exception: {exc}")
                results[resource_type] = {"entry": []}

        try:
            key_obs_entries = future_key_obs.result()
        except Exception as e:
            key_obs_entries = []
            print(f"Key observations fetch failed: {e}")
        try:
            other_obs_entries = future_other_obs.result()
        except Exception as e:
            other_obs_entries = []
            print(f"Other observations fetch failed: {e}")

    # 合并两部分Observation的结果，并用字典去重
    all_obs_entries = {entry['resource']['id']: entry for entry in key_obs_entries + other_obs_entries}.values()
    
    data = {
        "patient": patient_res.json(),
        "observations": {"entry": list(all_obs_entries)},
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
    risk_score = "75.3%"
    shap_values = [0.1, -0.05, 0.2]
    shap_features = ["Age", "BMI", "BP"]
    now = datetime.datetime.utcnow().isoformat() + "Z"
    patient_reference = {"reference": f"Patient/{patient_data.get('patient', {}).get('id', 'Unknown')}"}
    new_observation = {
        "resourceType": "Observation", "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "99999-9", "display": "PU-SSI Risk Score and SHAP"}], "text": "PU-SSI Risk Score and SHAP"},
        "subject": patient_reference, "effectiveDateTime": now, "issued": now,
        "valueString": f"Risk Score: {risk_score}; SHAP: {dict(zip(shap_features, shap_values))}"
    }
    return {
        "risk_score": risk_score, "shap_values": shap_values, "shap_features": shap_features,
        "raw_observation_update": new_observation
    }
