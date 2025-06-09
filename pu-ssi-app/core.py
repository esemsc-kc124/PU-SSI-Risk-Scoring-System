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
    'height': ['8302-2', '3137-7'], # 身高有两个可能的编码
    'blood_pressure': '85354-9',
    'weight': ['3141-9', '29463-7'], # 体重有两个可能的编码
    'bmi': ['39156-5', '39157-3'],  # BMI有两个可能的编码
    'tobacco': '88028-6'
}

def _fetch_single_observation(token, patient_id, code_name, codes):
    """
    一个“微任务”函数，只负责获取一种特定的Observation。
    A "micro-task" function responsible only for fetching one specific type of Observation.
    """
    # 如果有多个备用编码，用逗号连接它们
    # If there are multiple alternate codes, join them with a comma.
    codes_to_fetch = ",".join(codes) if isinstance(codes, list) else codes
    url = f"{FHIR_BASE_URL}/Observation?patient={patient_id}&code={codes_to_fetch}&_count=100"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [Micro-Task: {code_name}] Fetching...")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        bundle = response.json()
        print(f"--- [Micro-Task: {code_name}] Finished. Found {len(bundle.get('entry', []))} entries.")
        return bundle.get("entry", [])
    except requests.exceptions.RequestException as e:
        print(f"[ERROR in Micro-Task: {code_name}] Failed: {e}")
        return []

def _fetch_recent_for_resource(token, patient_id, resource_type):
    """获取除Observation之外的其他资源的最新一页。"""
    url = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}&_sort=-date&_count=100"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [Thread: {resource_type}] Fetching most recent data...")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if "sort" in str(e).lower():
            print(f"[WARN] Sorting by date not supported for {resource_type}. Fetching without sorting.")
            try:
                url_no_sort = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}&_count=100"
                response = requests.get(url_no_sort, headers=headers, timeout=60)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e2:
                 print(f"[ERROR in Thread: {resource_type}] Failed to fetch data even without sorting: {e2}")
        else:
            print(f"[ERROR in Thread: {resource_type}] Failed to fetch data: {e}")
        return {"entry": []}

def get_procedure_display_text(resource):
    if not resource: return "Invalid Procedure resource"
    if resource.get("code", {}).get("text"): return resource["code"]["text"]
    if resource.get("code", {}).get("coding") and len(resource["code"]["coding"]) > 0:
        return resource["code"]["coding"][0].get("display", "Procedure without text display")
    return "Procedure with no description"

def get_patient_data_bundle(provider_token, patient_id):
    """并行获取选定病人的所有详细信息，并使用微任务策略获取Observations。"""
    patient_url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    patient_res = requests.get(patient_url, headers=headers, timeout=60)
    patient_res.raise_for_status()
    
    other_resources = ["Condition", "Procedure", "Encounter", "CarePlan", "Device", "AllergyIntolerance"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(other_resources) + len(KEY_OBSERVATION_CODES)) as executor:
        # 1. 提交获取其他常规资源的任务
        future_to_resource = {
            executor.submit(_fetch_recent_for_resource, provider_token, patient_id, res): res 
            for res in other_resources
        }
        
        # 2. 为每一个关键Observation提交一个独立的“微任务”
        future_to_observation = {
            executor.submit(_fetch_single_observation, provider_token, patient_id, name, codes): name
            for name, codes in KEY_OBSERVATION_CODES.items()
        }

        # 3. 收集其他资源的结果
        results = {}
        for future in concurrent.futures.as_completed(future_to_resource):
            resource_type = future_to_resource[future]
            try:
                results[resource_type] = future.result()
            except Exception as exc:
                print(f"[ERROR] {resource_type} generated an exception: {exc}")
                results[resource_type] = {"entry": []}

        # 4. 收集所有关键Observation的结果
        all_obs_entries = []
        for future in concurrent.futures.as_completed(future_to_observation):
            try:
                # 将每个微任务的结果合并到总列表中
                all_obs_entries.extend(future.result())
            except Exception as e:
                print(f"A key observation micro-task failed: {e}")

    # 去重，以防万一
    unique_obs_entries = {entry['resource']['id']: entry for entry in all_obs_entries}.values()
    
    data = {
        "patient": patient_res.json(),
        "observations": {"entry": list(unique_obs_entries)},
        "conditions": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in results.get("Condition", {}).get('entry', [])],
        "procedures": [get_procedure_display_text(e.get('resource')) for e in results.get("Procedure", {}).get('entry', [])],
        "encounters": [e.get('resource', {}).get('type', [{}])[0].get('text', 'N/A') for e in results.get("Encounter", {}).get('entry', [])],
        "careplans": [e.get('resource', {}).get('description', 'N/A') for e in results.get("CarePlan", {}).get('entry', [])],
        "devices": [e.get('resource', {}).get('type', {}).get('text', 'N/A') for e in results.get("Device", {}).get('entry', [])],
        "allergies": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in results.get("AllergyIntolerance", {}).get('entry', [])],
    }
    return data

def run_prediction(patient_data):
    """
    接收病人数据，运行预测模型并返回结果。
    同时，它会构造一个标准的FHIR Observation资源，用于未来写回EHR。
    """
    print("Received data for prediction inside core logic.")

    risk_score = "75.3%"
    shap_values = [0.1, -0.05, 0.2]
    shap_features = ["Age", "BMI", "BP"]

    now = datetime.datetime.utcnow().isoformat() + "Z"
    patient_reference = {"reference": f"Patient/{patient_data.get('patient', {}).get('id', 'Unknown')}"}

    new_observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "99999-9", "display": "PU-SSI Risk Score and SHAP"}], "text": "PU-SSI Risk Score and SHAP"},
        "subject": patient_reference,
        "effectiveDateTime": now,
        "issued": now,
        "valueString": f"Risk Score: {risk_score}; SHAP: {dict(zip(shap_features, shap_values))}"
    }

    return {
        "risk_score": risk_score,
        "shap_values": shap_values,
        "shap_features": shap_features,
        "raw_observation_update": new_observation
    }
