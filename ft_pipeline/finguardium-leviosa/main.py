from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from labels_rag_fusion import step1
from malicious_qs_gen import step_2
from process_documents import step_0
import os
from werkzeug.utils import secure_filename
from openai import AzureOpenAI
import weaviate


app = Flask(__name__)
api = Api(app)


auth_config = weaviate.auth.AuthApiKey(api_key="1gpTlBmxUjPXy5hdIsFsTv4Z8dXYP6uUIcyP")  # Replace with your Weaviate instance API key
client = weaviate.Client(
    "https://sabka-sandbox-584cti4c.weaviate.network",
    auth_client_secret=auth_config
)

key = "0a52d2e0a33f4d728d4c12d7fa00f74f"
endpoint = "https://custommodeltest.cognitiveservices.azure.com/"

oai_client = AzureOpenAI(
  api_key = "add2ae8844844d55bd3e1300ccbc9bc2",
  api_version = "2023-05-15",
  azure_endpoint = "https://openai-service-onfi.openai.azure.com/"
)

gcp_gemini_config = {
    "url": "https://us-central1-qualified-cedar-405007.cloudfunctions.net/gemini-access",
    "api_key": "C5550PAAOCUEH8JRJ3",
    "sys_instr": """
You are working with a company looking to fine tune an LLM guard model for financial services. You have been given a circular issued by SEBI (financial regulator in India) related to registered investment advisors.

Answer Instructions:
0. DONOT USE THE WEB
1. Only cover guidelines related to investment advice offered.
2. You need to extract as a python list the set of labels corresponding to bad behavior as per regulator. 
3. LABELS SHOULD BE 3-4 WORDS MAX
4. Mention it in adversarial tone. For example: (default) Buy TATA stock when you are selling TATA stock -> (required) Conflict of Interest 
5. Don't reverse double negatives. example: (default) Presence of Bias in research -> (wrong flip) Lack of Presence of Bias in Research
6. For each label, also refer to the page number in document.

Example:

```python
labels_list = [label1, label2, ...]
```"""
}

class Guardrails(Resource):
    def post(self):
        if 'file' not in request.files:
            return {'message': 'No file part in the request'}, 400

        file = request.files['file']
        
        if file.filename == '':
            return {'message': 'No file selected for uploading'}, 400
        
        filename = secure_filename(file.filename)
        file_path = os.path.join("/Users/priyeshsrivastava/finguard/uploads", filename)
        file.save(file_path)

        #Start guardrails pipeline
        pg_wise_data = step_0(key=key, endpoint=endpoint, doc_path=file_path)
        labels_union = step1(
            oai_client=oai_client, pg_wise_data=pg_wise_data, vector_db=client,
            rest_client_conf=gcp_gemini_config
        )
        # TODO Harshit Finish this one FAFA :pray
        qa_labels = step_2(oai_client=oai_client, labels=labels_union)

        # Label Search + Malicious Q Gen -> Harshith
        # Malicious QA [Here]
        # Dataset Resampling
        # DPO on Llama Guard 2
        # return {'hello': 'world'}

api.add_resource(Guardrails, '/guardrail')

if __name__ == '__main__':
    app.run(debug=True)