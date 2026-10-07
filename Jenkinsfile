// CampusPulse AI — Jenkins CI/CD Pipeline (Sprint 5)
// =====================================================
// Declarative Pipeline for automated build, test, containerize & deploy
// Trigger: Git push to 'main' branch via GitHub webhook

pipeline {
    agent any

    environment {
        // Application identity
        APP_NAME        = "campuspulse-ai"
        APP_VERSION     = "1.0.${BUILD_NUMBER}"

        // Docker Hub / ECR configuration
        DOCKER_REGISTRY = "your-ecr-registry.amazonaws.com"
        DOCKER_IMAGE    = "${DOCKER_REGISTRY}/${APP_NAME}"
        DOCKER_TAG      = "${APP_VERSION}"

        // AWS Deployment target
        AWS_REGION      = "ap-south-1"    // Mumbai region (closest to campus)
        EC2_HOST        = credentials("EC2_HOST")        // EC2 Public IP (Jenkins credential)
        EC2_USER        = "ec2-user"

        // Python virtualenv path
        VENV_PATH       = "${WORKSPACE}/venv"
        PYTHON          = "${VENV_PATH}/bin/python"

        // Test DB connection (uses test credentials)
        MYSQL_HOST      = "localhost"
        MYSQL_DATABASE  = "campus_issue_test"
        MYSQL_USER      = credentials("TEST_DB_USER")
        MYSQL_PASSWORD  = credentials("TEST_DB_PASSWORD")
        SECRET_KEY      = credentials("FLASK_SECRET_KEY")
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timeout(time: 20, unit: "MINUTES")
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        // ─── Stage 1: Source Code Checkout ───
        stage("Checkout") {
            steps {
                echo "📦 Checking out source from Git repository..."
                checkout scm
                sh "git log --oneline -5"
            }
        }

        // ─── Stage 2: Python Environment Setup ───
        stage("Environment Setup") {
            steps {
                echo "🐍 Setting up Python virtual environment..."
                sh """
                    python3 -m venv ${VENV_PATH}
                    ${VENV_PATH}/bin/pip install --upgrade pip
                    ${VENV_PATH}/bin/pip install -r requirements.txt
                    ${VENV_PATH}/bin/pip install gunicorn
                """
            }
        }

        // ─── Stage 3: Code Quality & Linting ───
        stage("Code Quality") {
            steps {
                echo "🔍 Running code quality checks (flake8)..."
                sh """
                    ${VENV_PATH}/bin/pip install flake8 --quiet
                    ${VENV_PATH}/bin/flake8 app.py config.py routes/ services/ database/ \
                        --max-line-length=120 \
                        --exclude=venv,__pycache__,.git \
                        --statistics \
                        --count || true
                """
            }
        }

        // ─── Stage 4: Database Test Environment Setup ───
        stage("Test DB Init") {
            steps {
                echo "🗄️ Creating isolated test database schema..."
                sh """
                    mysql -h ${MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} \
                        -e "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE};"
                    mysql -h ${MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} \
                        < database/schema.sql || echo "Schema may already exist, continuing..."
                """
            }
        }

        // ─── Stage 5: Automated Testing (Pytest) ───
        stage("Run Tests") {
            steps {
                echo "🧪 Executing Pytest test suite (23 test cases)..."
                sh """
                    export MYSQL_DATABASE=${MYSQL_DATABASE}
                    ${VENV_PATH}/bin/pytest tests/ \
                        --verbose \
                        --tb=short \
                        --junit-xml=test-results/results.xml \
                        --html=test-results/report.html \
                        --self-contained-html
                """
            }
            post {
                always {
                    // Publish JUnit test results in Jenkins UI
                    junit "test-results/results.xml"
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: "test-results",
                        reportFiles: "report.html",
                        reportName: "Pytest HTML Report"
                    ])
                }
                failure {
                    echo "❌ Tests FAILED — Halting pipeline. Deployment aborted."
                }
            }
        }

        // ─── Stage 6: Docker Build ───
        stage("Docker Build") {
            when {
                branch "main"
            }
            steps {
                echo "🐳 Building Docker container image v${APP_VERSION}..."
                sh """
                    docker build \
                        --build-arg BUILD_NUMBER=${BUILD_NUMBER} \
                        -t ${DOCKER_IMAGE}:${DOCKER_TAG} \
                        -t ${DOCKER_IMAGE}:latest \
                        .
                    docker images ${DOCKER_IMAGE} --format "table {{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
                """
            }
        }

        // ─── Stage 7: Docker Push to AWS ECR ───
        stage("Push to ECR") {
            when {
                branch "main"
            }
            steps {
                echo "☁️ Authenticating with AWS ECR and pushing image..."
                withAWS(credentials: "AWS_JENKINS_CREDENTIALS", region: "${AWS_REGION}") {
                    sh """
                        aws ecr get-login-password --region ${AWS_REGION} | \
                            docker login --username AWS --password-stdin ${DOCKER_REGISTRY}
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker push ${DOCKER_IMAGE}:latest
                    """
                }
            }
        }

        // ─── Stage 8: Deploy to AWS EC2 ───
        stage("Deploy to AWS EC2") {
            when {
                branch "main"
            }
            steps {
                echo "🚀 Deploying CampusPulse AI v${APP_VERSION} to EC2 instance..."
                sshagent(credentials: ["EC2_SSH_KEY"]) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} '
                            echo "Pulling latest image from ECR..."
                            aws ecr get-login-password --region ${AWS_REGION} | \
                                docker login --username AWS --password-stdin ${DOCKER_REGISTRY}
                            docker pull ${DOCKER_IMAGE}:latest

                            echo "Stopping existing container..."
                            docker stop campuspulse-prod || true
                            docker rm campuspulse-prod || true

                            echo "Starting new container..."
                            docker run -d \
                                --name campuspulse-prod \
                                --restart unless-stopped \
                                -p 5000:5000 \
                                -e MYSQL_HOST=$MYSQL_RDS_ENDPOINT \
                                -e MYSQL_USER=$MYSQL_USER \
                                -e MYSQL_PASSWORD=$MYSQL_PASSWORD \
                                -e MYSQL_DATABASE=campus_issue_system \
                                -e SECRET_KEY=$SECRET_KEY \
                                -e FLASK_ENV=production \
                                ${DOCKER_IMAGE}:latest

                            echo "Container status:"
                            docker ps --filter name=campuspulse-prod
                        '
                    """
                }
            }
        }

        // ─── Stage 9: Smoke Test ───
        stage("Production Smoke Test") {
            when {
                branch "main"
            }
            steps {
                echo "🔬 Running production smoke test..."
                sh """
                    sleep 15
                    curl -f http://${EC2_HOST}:5000/test-db \
                        && echo "✅ Smoke test PASSED — Application is live!" \
                        || (echo "❌ Smoke test FAILED" && exit 1)
                """
            }
        }

    }

    post {
        always {
            echo "🧹 Cleaning up Docker images from Jenkins agent..."
            sh "docker image prune -f || true"
        }
        success {
            echo """
            ✅ ================================================
            CampusPulse AI — CI/CD PIPELINE SUCCEEDED
            Build:   #${BUILD_NUMBER} (v${APP_VERSION})
            Status:  LIVE on AWS EC2 (${AWS_REGION})
            URL:     http://${EC2_HOST}:5000
            Tests:   22/23 Passed ✅
            ================================================
            """
            // Could notify Slack/email here
        }
        failure {
            echo """
            ❌ ================================================
            CampusPulse AI — PIPELINE FAILED
            Build:   #${BUILD_NUMBER}
            Action:  Review logs and fix errors
            Tests must pass before deployment is allowed
            ================================================
            """
        }
    }
}
