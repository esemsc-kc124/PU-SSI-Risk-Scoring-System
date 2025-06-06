import requests

# --- FHIR Server Configuration ---
# FHIR 服务器的地址是核心数据逻辑的一部分
FHIR_BASE_URL = "https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

def fetch_fhir_resource(token, patient_id, resource_type):
    """
    一个辅助函数，用于获取并解析指定病人的资源列表
    """
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
        # 在核心逻辑中，打印错误日志对于调试非常重要
        print(f"Failed to fetch {resource_type} for patient {patient_id}: {e}")
        # 返回一个空列表表示获取失败，让调用者决定如何处理
        return []

def get_patient_data_bundle(provider_token, patient_id):
    """
    获取选定病人的所有详细信息，并打包成一个字典
    这个函数包含了原先在 /get_patient_data 路由中的主要逻辑。
    """
    headers = {"Authorization": f"Bearer {provider_token}", "Accept": "application/fhir+json"}
    
    # 获取核心 Patient 和 Observation 资源
    patient_res = requests.get(f"{FHIR_BASE_URL}/Patient/{patient_id}", headers=headers)
    patient_res.raise_for_status()
    
    obs_res = requests.get(f"{FHIR_BASE_URL}/Observation?patient={patient_id}&_count=100", headers=headers)
    obs_res.raise_for_status()

    # 构建最终的数据对象
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
    return data

def run_prediction(patient_data):
    """
    接收病人数据，运行预测模型并返回结果
    目前返回一个模拟结果。
    """
    # 这里是你未来集成真实机器学习模型的地方
    # patient_data 参数在这里会被使用
    print("Received data for prediction inside core logic.")
    
    # 返回一个假的预测结果
    return {"risk_score": "75.3%"}