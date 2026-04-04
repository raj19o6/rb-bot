# test_jenkins.py
import os
from api.run_job import trigger_jenkins_job

JENKINS_URL = "https://jenkins.btacode.com"
JENKINS_USER = "admin"
JENKINS_TOKEN = "11b3055ae791242c922e9fa74345b30bd4"

job_url = f"{JENKINS_URL}/job/rb-bot-runner"
params = {
    'WORKFLOW_ID': '4ae9d907-cc9d-4d9d-9f03-02d311ec0700',
    'WORKFLOW_JSON_URL': 'http://172.17.84.253:8000/api/v1/workflows/4ae9d907-cc9d-4d9d-9f03-02d311ec0700/download/',
    'CALLBACK_URL': 'http://172.17.84.253:8000/api/v1/workflows/4ae9d907-cc9d-4d9d-9f03-02d311ec0700/report/',
    'OPENAI_API_KEY': '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'
}
auth = (JENKINS_USER, JENKINS_TOKEN)

result = trigger_jenkins_job(job_url, params=params, auth=auth)
print(result)

# Expected output:
# {'success': True, 'status_code': 201, 'error': None}
