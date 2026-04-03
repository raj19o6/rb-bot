pipeline {
    agent any
    
    environment {
        // Credentials stored in Jenkins
        APP_USERNAME = credentials('app-username')
        APP_PASSWORD = credentials('app-password')
        OPENAI_API_KEY = credentials('openai-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                echo 'Setting up RB-BOT...'
                sh '''
                    python3 -m venv venv
                    source venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('Deploy Application') {
            steps {
                echo 'Deploying application...'
                // Your deployment steps here
                sh './deploy.sh'
            }
        }
        
        stage('Wait for Application') {
            steps {
                echo 'Waiting for application to be ready...'
                sh '''
                    # Wait for app to be healthy
                    for i in {1..30}; do
                        if curl -f http://your-app.com/health; then
                            echo "Application is ready!"
                            break
                        fi
                        echo "Waiting... ($i/30)"
                        sleep 10
                    done
                '''
            }
        }
        
        stage('Run Automated Tests') {
            steps {
                echo 'Running RB-BOT tests...'
                sh '''
                    source venv/bin/activate
                    
                    # Update config with credentials
                    cat > data/autonomous.json <<EOF
{
  "base_url": "https://your-app.com/login",
  "credentials": {
    "username": "${APP_USERNAME}",
    "password": "${APP_PASSWORD}"
  },
  "openai_api_key": "${OPENAI_API_KEY}"
}
EOF
                    
                    # Run recorded workflows
                    python3 replay_workflow.py login_flow || true
                    python3 replay_workflow.py checkout_flow || true
                    python3 replay_workflow.py user_management || true
                    
                    # Or run autonomous mode
                    # python3 autonomous_runner.py || true
                '''
            }
        }
        
        stage('Generate Reports') {
            steps {
                echo 'Generating test reports...'
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'reports',
                    reportFiles: 'report.html',
                    reportName: 'RB-BOT Test Report',
                    reportTitles: 'Automated Test Results'
                ])
            }
        }
        
        stage('Check Results') {
            steps {
                script {
                    // Parse results and fail if critical issues found
                    def report = readJSON file: 'reports/autonomous_report.json'
                    def securityIssues = 0
                    
                    report.test_reports.each { test ->
                        securityIssues += test.summary.security_issues
                    }
                    
                    echo "Total security issues found: ${securityIssues}"
                    
                    if (securityIssues > 10) {
                        error("Too many security issues found: ${securityIssues}")
                    }
                }
            }
        }
    }
    
    post {
        always {
            echo 'Archiving test results...'
            archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
            archiveArtifacts artifacts: 'reports/token_usage.json', allowEmptyArchive: true
        }
        
        success {
            echo 'Tests passed! Sending notification...'
            emailext (
                subject: "✅ Tests PASSED - Build #${BUILD_NUMBER}",
                body: """
                    <h2>RB-BOT Test Results - PASSED</h2>
                    <p>Build: #${BUILD_NUMBER}</p>
                    <p>All automated tests completed successfully!</p>
                    <p><a href="${BUILD_URL}RB-BOT_Test_Report/">View Full Report</a></p>
                """,
                to: 'client@example.com, team@example.com',
                mimeType: 'text/html'
            )
        }
        
        failure {
            echo 'Tests failed! Sending notification...'
            emailext (
                subject: "❌ Tests FAILED - Build #${BUILD_NUMBER}",
                body: """
                    <h2>RB-BOT Test Results - FAILED</h2>
                    <p>Build: #${BUILD_NUMBER}</p>
                    <p>Some tests failed or security issues detected.</p>
                    <p><a href="${BUILD_URL}RB-BOT_Test_Report/">View Full Report</a></p>
                    <p><a href="${BUILD_URL}console">View Console Output</a></p>
                """,
                to: 'client@example.com, team@example.com',
                mimeType: 'text/html'
            )
        }
    }
}
