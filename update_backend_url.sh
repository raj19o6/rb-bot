#!/bin/bash
# Update backend to use dev tunnel URL

echo "Updating backend configuration..."

# Backend .env should have:
cat > backend_env_example.txt << 'EOF'
# Add these to your backend .env file:

API_BASE_URL=https://8nh48kbv-8000.inc1.devtunnels.ms
JENKINS_URL=https://jenkins.btacode.com
JENKINS_USER=your-jenkins-username
JENKINS_TOKEN=your-jenkins-api-token
JENKINS_JOB=rb-bot-runner
OPENAI_API_KEY=sk-proj-xxxxx
VERIFY_SSL=false
EOF

echo "✅ Created backend_env_example.txt"
echo ""
echo "📝 Update your backend signal handler to use:"
echo "   API_BASE_URL = 'https://8nh48kbv-8000.inc1.devtunnels.ms'"
echo ""
echo "🔄 Then restart your backend server"
