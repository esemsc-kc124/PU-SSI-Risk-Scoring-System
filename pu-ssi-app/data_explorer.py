# 导入我们需要的库
# Import the libraries we need
import pandas as pd
from google.cloud import bigquery
import os

# --- 0. 先决条件 (Prerequisites) ---
# --- 0. Prerequisites (One-time Setup) ---

# a. 安装必需的Python库
#    在您的终端里运行 / In your terminal, run:
#    pip install google-cloud-bigquery pandas google-auth

# b. 完成Google Cloud认证
#    在您的终端里运行 / In your terminal, run:
#    gcloud auth application-default login

# c. 创建并设置您自己的Google Cloud项目 (关键步骤！)
#    要查询公共数据集，您需要用自己的项目来承担计算配额。
#    To query public datasets, you need to use your own project for billing and quota.
#    1. 访问 https://console.cloud.google.com/projectcreate
#    2. 创建一个新项目，例如 "my-mimic-iv-project"。
#    3. 创建后，请将下方 `your_project_id` 变量的值，替换为您刚刚创建的那个新项目的ID。


# --- 1. 初始化 BigQuery 客户端 ---
# --- 1. Initialize the BigQuery client ---
try:
    # --- 关键修改：在这里填入您自己的项目ID ---
    # --- KEY CHANGE: Fill in your own project ID here ---
    your_project_id = "infinite-facet-462714-g7"
    
    if your_project_id == "your-gcp-project-id-goes-here":
        print("错误：请在脚本的第30行，将 'your-gcp-project-id-goes-here' 替换为您自己的Google Cloud项目ID。")
        print("Error: Please replace 'your-gcp-project-id-goes-here' with your own Google Cloud Project ID on line 30 of the script.")
        exit()

    client = bigquery.Client(project=your_project_id)
    print(f"BigQuery客户端初始化成功，将使用项目'{your_project_id}'来运行查询。")
    print(f"BigQuery client initialized successfully, using project '{your_project_id}' to run queries.")

except Exception as e:
    print(f"初始化失败，请确保您已完成认证，并提供了正确的项目ID: {e}")
    print("Initialization failed, please ensure you have completed authentication and provided a correct project ID.")
    exit()

# --- 2. 编写您的SQL查询语句 ---
# --- 2. Write your SQL query ---
# 请注意：查询语句中引用的数据表，依然是 `physionet-data` 项目下的。
# Note: The tables referenced in the query are still under the `physionet-data` project.
sql_query = """
SELECT
    p.subject_id,
    p.gender,
    p.anchor_age,
    COUNT(adm.hadm_id) AS number_of_admissions
FROM
    `physionet-data.mimiciv_3_1_hosp.patients` AS p
JOIN
    `physionet-data.mimiciv_3_1_hosp.admissions` AS adm
ON
    p.subject_id = adm.subject_id
GROUP BY
    p.subject_id, p.gender, p.anchor_age
ORDER BY
    number_of_admissions DESC
LIMIT 20;
"""

print(f"\n即将执行查询 / Executing query:\n")
print(sql_query)

# --- 3. 执行查询并获取结果 ---
# --- 3. Execute the query and get the results ---
try:
    df = client.query(sql_query).to_dataframe()

    # --- 4. 查看并使用您的数据 ---
    # --- 4. View and use your data ---
    print("\n查询成功！已将数据加载到DataFrame中。/ Query successful! Data loaded into DataFrame.")
    print("\n查询结果 / Query Results:")
    print(df)

    print(f"\n成功获取了 {len(df)} 条记录。/ Successfully fetched {len(df)} records.")
    
except Exception as e:
    print(f"\n查询失败 / Query failed: {e}")

