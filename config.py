import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Database Configuration with secure environment variable fallbacks
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "campus_issue_system")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

# Application Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "campuspulse-ai-secure-secret-key-2025")
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

# Uploads Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# AWS Cloud Configuration (EC2, RDS, S3, SNS, CloudWatch)
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "campuspulse-issue-attachments")
AWS_SNS_TOPIC_ARN = os.getenv("AWS_SNS_TOPIC_ARN", "")
AWS_CLOUDWATCH_NAMESPACE = os.getenv("AWS_CLOUDWATCH_NAMESPACE", "CampusPulse/Infrastructure")
# Auto-enable AWS services if credentials exist or if explicitly forced
AWS_ENABLED = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))