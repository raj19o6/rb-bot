pipeline {
    agent any
    
    parameters {
        string(name: 'WORKFLOW_ID', defaultValue: '', description: 'Workflow ID from database')
        string(name: 'WORKFLOW_JSON_URL', defaultValue: '', description: 'URL to download workflow JSON')
        string(name: 'CALLBACK_URL', defaultValue: '', description: 'API endpoint to send results back')
        password(name: 'OPENAI_API_KEY', defaultValue: '', description: 'OpenAI API Key for AI test generation')
    }
    
    environment {
        OPENAI_API_KEY = "${params.OPENAI_API_KEY}"
        WORKFLOW_ID = "${params.WORKFLOW_ID}"
        CALLBACK_URL = "${params.CALLBACK_URL}"
        BROWSER = 'chromium'
        HEADLESS = 'true'
        TIMEOUT = '10000'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code from repository...'
                checkout scm
            }
        }
        
        stage('Install Dependencies') {
            steps {
                echo 'Installing Python dependencies...'
                sh '''
                    # Check if pip is installed, if not install it
                    if ! python3 -m pip --version > /dev/null 2>&1; then
                        echo "pip not found, installing..."
                        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
                        python3 get-pip.py --user
                        rm get-pip.py
                    fi
                    
                    python3 -m pip install --upgrade pip --user
                    python3 -m pip install -r requirements.txt --user
                    python3 -m playwright install chromium
                '''
            }
        }
        
        stage('Download Workflow') {
            steps {
                echo "Downloading workflow from ${params.WORKFLOW_JSON_URL}"
                sh '''
                    echo "Testing connection to backend..."
                    curl -I "${WORKFLOW_JSON_URL}" --connect-timeout 10 --max-time 30 || {
                        echo "ERROR: Cannot reach backend API at ${WORKFLOW_JSON_URL}"
                        echo "Please ensure:"
                        echo "1. Backend is running"
                        echo "2. Jenkins can access the backend URL"
                        echo "3. Firewall allows Jenkins -> Backend communication"
                        exit 1
                    }
                    
                    echo "Downloading workflow JSON..."
                    curl -f -o workflow.json "${WORKFLOW_JSON_URL}" --connect-timeout 10 --max-time 30 || {
                        echo "ERROR: Failed to download workflow JSON"
                        exit 1
                    }
                    
                    echo "Workflow downloaded successfully"
                    echo "Workflow content:"
                    cat workflow.json | head -20
                '''
            }
        }
        
        stage('Setup Environment') {
            steps {
                echo 'Setting up environment variables...'
                sh '''
                    echo "OPENAI_API_KEY=${OPENAI_API_KEY}" > .env
                    echo "BROWSER=chromium" >> .env
                    echo "HEADLESS=true" >> .env
                    echo "TIMEOUT=10000" >> .env
                    echo "Environment configured"
                '''
            }
        }
        
        stage('Execute Bot') {
            steps {
                echo 'Executing RB-BOT with workflow...'
                sh '''
                    python3 chrome_recording_runner.py workflow.json "${CALLBACK_URL}"
                '''
            }
        }
        
        stage('Upload Results') {
            steps {
                echo "Uploading results to ${params.CALLBACK_URL}"
                sh '''
                    RESULT_FILE=$(ls reports/*_results.json 2>/dev/null | head -1)
                    
                    if [ -f "$RESULT_FILE" ]; then
                        echo "Found result file: $RESULT_FILE"
                        
                        # Add workflow_id to the report
                        jq --arg wid "${WORKFLOW_ID}" '. + {workflow_id: $wid}' "$RESULT_FILE" > /tmp/report_with_id.json
                        
                        # Send to callback URL
                        curl -X POST "${CALLBACK_URL}" \
                             -H "Content-Type: application/json" \
                             -d @/tmp/report_with_id.json \
                             -w "\\nHTTP Status: %{http_code}\\n"
                        
                        echo "Results uploaded successfully"
                    else
                        echo "ERROR: No results file found in reports/"
                        ls -la reports/ || echo "Reports directory not found"
                        exit 1
                    fi
                '''
            }
        }
    }
    
    post {
        always {
            echo 'Archiving artifacts...'
            archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
            
            echo 'Cleaning workspace...'
            cleanWs()
        }
        success {
            echo '✅ Bot execution completed successfully!'
        }
        failure {
            echo '❌ Bot execution failed!'
        }
    }
}
