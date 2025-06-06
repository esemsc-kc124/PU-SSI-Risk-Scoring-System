# PU/SSI Risk Scoring System

[cite_start]This project is an implementation of a machine learning scoring system designed to predict the risk of pressure ulcers (PUs) and surgical-site infections (SSIs)[cite: 2]. [cite_start]The system is designed to be integrated with EHR systems like Cerner, utilizing the SMART on FHIR API standard to fetch patient data and provide clinical decision support[cite: 4, 10, 17].

The current version features a prototype web application that can authenticate with the Cerner sandbox, fetch patient data, and call a mock prediction endpoint.

## Architecture Overview

The system is composed of three main parts:

* **Backend (`simulator.py`)**: A Python Flask application that serves as the backend server. It handles the OAuth2 authentication flow with Cerner, provides an API for searching patients, and exposes an endpoint to fetch detailed patient data.
* **Core Logic (`core.py`)**: A decoupled Python module that contains the main business logic. It is responsible for the actual data fetching from the FHIR server and will contain the machine learning model inference logic. This allows the core prediction pipeline to be used independently of the web application.
* **Frontend (`index.html`, `search.html`)**: A client-side application built with HTML, JavaScript, and jQuery. It provides the user interface for authenticating, searching for a patient, viewing their data, and triggering a risk score prediction.

## Prerequisites

* Python 3.x
* Required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

To run the full web application, you need to start both the backend and frontend servers in separate terminals.

### 1. Start the Backend Server

In your first terminal, navigate to the project directory and run the Flask application:
```bash
cd pu-ssi-app
python simulator.py
```
This will start the backend server on `http://127.0.0.1:5080`.

### 2. Start the Frontend Server

In a second terminal, navigate to the directory containing the frontend files (`index.html`, `search.html`, etc.) and start a simple Python web server:
```bash
cd pu-ssi-app
python -m http.server 8000
```
This will serve the frontend on `http://127.0.0.1:8000`.

### 3. Use the Web Application
This section details the step-by-step user workflow from login to prediction.

1.  **Initial Login**
    * Navigate to `http://127.0.0.1:8000/index.html` in your web browser.
    * Click the **"Login with FHIR"** button to begin.

2.  **Cerner Authentication**
    * You will be redirected to the Cerner Sandbox authorization page.
    * Log in using the provided provider credentials (e.g., portal(portal)). This simulates a healthcare provider accessing the system.

3.  **Search for a Patient**
    * After a successful login, the Cerner server will redirect you back to the application's patient search page (`search.html`).
    * In the search box, enter a patient's name (e.g., "Smart", "Brad") and click the "Search" button.

4.  **Select a Patient from Results**
    * The application will display a table with patients matching your search query.
    * Find the patient you wish to evaluate and click the **"Select"** button in their corresponding row.

5.  **View Patient's Clinical Data**
    * After selecting a patient, you will be redirected back to the main page (`index.html`).
    * The page will now automatically fetch and display a comprehensive set of the selected patient's clinical data from the FHIR server. This includes demographics, observations (like blood pressure and height), conditions, procedures, and more.

6.  **Run Risk Prediction**
    * Once all the patient data has finished loading, scroll to the bottom of the page.
    * Click the **"Run Prediction"** button.
    * The application will send the patient's data to the backend's `/predict` endpoint and display the returned risk score on the page. Note: The prediction logic is currently a mock and will always return the same score.
## Running the Command-Line (CLI) Tool

To test the core data fetching and prediction logic without the web interface, you can create and use a `predict_cli.py` script.

1.  **Get a Bearer Token**: Run the web application once to authenticate and obtain a valid provider access token. Paste this token into the script.
2.  **Execute the script** from your terminal, passing a patient ID as an argument:
    ```bash
    cd pu-ssi-app
    python predict_cli.py 12742399
    ```

## What To Do Next

Based on the project plan and meeting logs, the following are the key priorities for future work:
* **Write Patient's Risk Score Back to Cerner**:
    * Load Patient's data as a json file and write the risk score inside Observation/Condition.
    * Send it back to FHIR server.

* **Develop the Prediction Model**:
    * [cite_start]Extract and preprocess training data from the MIMIC-IV dataset[cite: 3, 12, 26].
    * [cite_start]Perform feature engineering (e.g., calculating BMI, lab risk scores)[cite: 14].
    * [cite_start]Train baseline (Logistic Regression) and advanced (XGBoost) models for risk prediction[cite: 9, 11].

* **Integrate the Real Model**:
    * Replace the mock prediction logic in `core.py` with the trained machine learning model.
    * The `/predict` API should return a real risk score based on model inference.

* **Implement Explainability**:
    * [cite_start]Integrate SHAP to provide explanations for individual risk predictions[cite: 11].
    * [cite_start]The model API should be able to return both the risk score and the SHAP output[cite: 21].

* **Enhance the Frontend/Dashboard**:
    * [cite_start]Develop a dashboard (e.g., using Streamlit) to visualize risk scores and SHAP explanations[cite: 28].
    * Improve the current web application to display the prediction results and explanations returned from the backend, potentially using a Javascript charting library on an HTML Canvas element.

* **Finalize and Test**:
    * [cite_start]Conduct final testing of the complete pipeline, from EHR data fetching to risk score presentation[cite: 30].
    * Complete project documentation and prepare for the final presentation.