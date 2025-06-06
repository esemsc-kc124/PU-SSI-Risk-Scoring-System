import sys
import json
import core  # Import the core logic module

def main():
    """
    A simple command-line tool to test the core data fetching and prediction logic.
    """
    # ============================ IMPORTANT ============================
    # The CLI tool cannot perform the browser-based OAuth2 login flow.
    # You MUST get a valid access token by running the web application
    # first, and then paste it here.
    # This token has a limited lifetime and will need to be updated
    # periodically.
    # =================================================================
    PROVIDER_TOKEN = "eyJraWQiOiIyMDI1LTA2LTA2VDAyOjAxOjE1LjEyMS5lYy5lczI1NiIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2In0.eyJzdWIiOiJwb3J0YWwiLCJ1cm46Y29tOmNlcm5lcjphdXRob3JpemF0aW9uOmNsYWltcyI6eyJ2ZXIiOiIxLjAiLCJ0bnQiOiJlYzI0NThmMi0xZTI0LTQxYzgtYjcxYi0wZTcwMWFmNzU4M2QiLCJhenMiOiJmaGlyVXNlciBvcGVuaWQgdXNlci9BbGxlcmd5SW50b2xlcmFuY2UucmVhZCB1c2VyL0NhcmVQbGFuLnJlYWQgdXNlci9Db25kaXRpb24ucmVhZCB1c2VyL0RldmljZS5yZWFkIHVzZXIvRW5jb3VudGVyLnJlYWQgdXNlci9NZWRpY2F0aW9uUmVxdWVzdC5yZWFkIHVzZXIvT2JzZXJ2YXRpb24ucmVhZCB1c2VyL1BhdGllbnQucmVhZCB1c2VyL1Byb2NlZHVyZS5yZWFkIn0sImF6cCI6IjFjMDI3M2E3LTY5NmUtNDBhZS1iZDlhLWU1OTNiNzM0OWNlZCIsImlzcyI6Imh0dHBzOi8vYXV0aG9yaXphdGlvbi5jZXJuZXIuY29tLyIsImV4cCI6MTc0OTIwMjE3MSwiaWF0IjoxNzQ5MjAxNTcxLCJqdGkiOiI2ZDViYzRkMi1kOGRiLTRlNzItODIyNC0wNTBjOTAyMTgxYzEiLCJ1cm46Y2VybmVyOmF1dGhvcml6YXRpb246Y2xhaW1zOnZlcnNpb246MSI6eyJ2ZXIiOiIxLjAiLCJwcm9maWxlcyI6eyJzbWFydC12MSI6eyJhenMiOiJmaGlyVXNlciBvcGVuaWQgdXNlci9BbGxlcmd5SW50b2xlcmFuY2UucmVhZCB1c2VyL0NhcmVQbGFuLnJlYWQgdXNlci9Db25kaXRpb24ucmVhZCB1c2VyL0RldmljZS5yZWFkIHVzZXIvRW5jb3VudGVyLnJlYWQgdXNlci9NZWRpY2F0aW9uUmVxdWVzdC5yZWFkIHVzZXIvT2JzZXJ2YXRpb24ucmVhZCB1c2VyL1BhdGllbnQucmVhZCB1c2VyL1Byb2NlZHVyZS5yZWFkIiwiZmhpclVzZXIiOiJQcmFjdGl0aW9uZXIvMTI3NDIwNjkifX0sImNsaWVudCI6eyJuYW1lIjoiUHJhY3RpY2FsIFBVL1NTSSBSaXNrIFNjb3JpbmcgU3lzdGVtIiwiaWQiOiIxYzAyNzNhNy02OTZlLTQwYWUtYmQ5YS1lNTkzYjczNDljZWQifSwidXNlciI6eyJwcmluY2lwYWwiOiJwb3J0YWwiLCJwZXJzb25hIjoicHJvdmlkZXIiLCJpZHNwIjoiZWMyNDU4ZjItMWUyNC00MWM4LWI3MWItMGU3MDFhZjc1ODNkIiwic2Vzc2lvbklkIjoiNmVlZWMxNjUtZWQ0Yy00OTlkLWExY2EtOTExYjVhMTE5Y2I3IiwicHJpbmNpcGFsVHlwZSI6InVzZXJuYW1lIiwicHJpbmNpcGFsVXJpIjoiaHR0cHM6Ly9taWxsZW5uaWEuY2VybmVyLmNvbS9pbnN0YW5jZS9lYzI0NThmMi0xZTI0LTQxYzgtYjcxYi0wZTcwMWFmNzU4M2QvcHJpbmNpcGFsLzAwMDAuMDAwMC4wMEMyLjZEQjUiLCJpZHNwVXJpIjoiaHR0cHM6Ly9taWxsZW5uaWEuY2VybmVyLmNvbS9hY2NvdW50cy9jMTk0MS5jZXJuX2FiY24uY2VybmVyYXNwLmNvbS9lYzI0NThmMi0xZTI0LTQxYzgtYjcxYi0wZTcwMWFmNzU4M2QvbG9naW4ifSwidGVuYW50IjoiZWMyNDU4ZjItMWUyNC00MWM4LWI3MWItMGU3MDFhZjc1ODNkIn19.1USOdFbR8TwMGmqTfQmM0uqXdVbDc8FYaRYM1BJfIyV8S7DNvgBeqiHEoL51RzLnlFZLLLIj1HXA9p1R6mPcWA"

    # Check if the placeholder token has been replaced
    if "PASTE" in PROVIDER_TOKEN:
        print("Error: Please edit predict_cli.py and replace 'PASTE YOUR BEARER TOKEN HERE' with a valid token.")
        return

    # Check for the patient ID in the command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python predict_cli.py <patient_id>")
        print("Example: python predict_cli.py 12742399")
        return

    patient_id = sys.argv[1]
    print(f"--- Starting prediction for Patient ID: {patient_id} ---")

    try:
        # Step 1: Call the core function to get all patient data
        print("Fetching patient data from FHIR server...")
        patient_data = core.get_patient_data_bundle(PROVIDER_TOKEN, patient_id)
        
        # Check if patient data was successfully fetched
        if not patient_data or not patient_data.get("patient"):
             print(f"Could not fetch data for patient {patient_id}. Please check the ID and your token.")
             return
             
        print(f"Successfully fetched data for: {patient_data['patient'].get('name', [{}])[0].get('text', 'N/A')}")

        # Step 2: Call the core function to run the prediction
        print("Running prediction model...")
        prediction_result = core.run_prediction(patient_data)

        # Step 3: Print the final result in a readable format
        print("\n--- Prediction Result ---")
        print(json.dumps(prediction_result, indent=2))
        print("-----------------------")

    except Exception as e:
        print(f"\nAn error occurred during the process: {e}")
        print("Please check if the patient ID is correct and if your access token is still valid.")

if __name__ == '__main__':
    main()