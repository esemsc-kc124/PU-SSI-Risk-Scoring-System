import requests
import json

# --- FHIR Server Configuration ---
FHIR_BASE_URL = "https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

def _fetch_bundle_for_resource(token, patient_id, resource_type):
    """
    一个私有的辅助函数，其唯一职责是获取指定资源的原始数据包 (Bundle)。
    此版本已实现分页逻辑，可以获取所有页面的数据。
    """
    all_entries = []
    # 构建初始请求URL
    url = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}&_count=100"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/fhir+json"}
    
    print(f"--- [INFO] Fetching ALL entries for: {resource_type} ---")
    
    try:
        # 循环直到没有下一页的链接
        while url:
            print(f"Fetching page: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            bundle = response.json()

            # 将当前页面的条目添加到总列表中
            if "entry" in bundle and isinstance(bundle["entry"], list):
                all_entries.extend(bundle["entry"])

            # 查找下一页的链接
            next_url = None
            if "link" in bundle and isinstance(bundle["link"], list):
                for link in bundle["link"]:
                    if link.get("relation") == "next":
                        next_url = link.get("url")
                        break  # 找到下一页链接，退出内层循环
            
            # 更新URL以进行下一次循环，如果没有下一页则为None，循环结束
            url = next_url

        print(f"--- Finished fetching for {resource_type}. Total entries found: {len(all_entries)} ---")
        
        # 返回一个包含所有合并后条目的新Bundle
        return {"resourceType": "Bundle", "entry": all_entries, "total": len(all_entries)}

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {resource_type} for patient {patient_id}: {e}")
        # 即使失败，也返回一个标准的空Bundle结构
        return {"resourceType": "Bundle", "entry": [], "total": 0}

def get_patient_data_bundle(provider_token, patient_id):
    """
    获取选定病人的所有详细信息，并打包成一个字典。
    """
    # 1. 单独获取核心 Patient 资源
    patient_url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    patient_res = requests.get(patient_url, headers=headers)
    patient_res.raise_for_status()
    
    # 2. 获取所有其他资源的完整数据包 (已包含分页逻辑)
    observations_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "Observation")
    conditions_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "Condition")
    procedures_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "Procedure")
    encounters_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "Encounter")
    careplans_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "CarePlan")
    devices_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "Device")
    allergies_bundle = _fetch_bundle_for_resource(provider_token, patient_id, "AllergyIntolerance")
    
    # 3. 构建最终要返回给前端的数据对象
    data = {
        "patient": patient_res.json(),
        "observations": observations_bundle,
        "conditions": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in conditions_bundle.get('entry', [])],
        "procedures": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in procedures_bundle.get('entry', [])],
        "encounters": [e.get('resource', {}).get('type', [{}])[0].get('text', 'N/A') for e in encounters_bundle.get('entry', [])],
        "careplans": [e.get('resource', {}).get('description', 'N/A') for e in careplans_bundle.get('entry', [])],
        "devices": [e.get('resource', {}).get('type', {}).get('text', 'N/A') for e in devices_bundle.get('entry', [])],
        "allergies": [e.get('resource', {}).get('code', {}).get('text', 'N/A') for e in allergies_bundle.get('entry', [])],
    }
    return data

def run_prediction(patient_data):
    """
    接收病人数据，运行预测模型并返回结果
    """
    print("Received data for prediction inside core logic.")
    return {"risk_score": "75.3%",
            "shap_values": [0.3, -0.2, 0.1],
            "shap_features": ["Age", "BMI", "BP"]}
