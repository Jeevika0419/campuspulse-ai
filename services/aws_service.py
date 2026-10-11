import os
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import config

logger = logging.getLogger("campuspulse.aws")
logger.setLevel(logging.INFO)

class AWSService:
    """
    Central AWS Cloud Integration Service for CampusPulse AI.
    Handles AWS S3, SNS, CloudWatch, and supports IAM execution roles
    with graceful local fallbacks for development and demonstration.
    """
    def __init__(self):
        self.region = config.AWS_REGION
        self.s3_bucket = config.AWS_S3_BUCKET
        self.sns_topic_arn = config.AWS_SNS_TOPIC_ARN
        self.cw_namespace = config.AWS_CLOUDWATCH_NAMESPACE
        self.is_enabled = config.AWS_ENABLED

        self._s3_client = None
        self._sns_client = None
        self._cw_client = None

        self._initialize_clients()

    def _initialize_clients(self):
        """Initializes Boto3 clients with credentials or EC2 instance profile."""
        try:
            client_kwargs = {"region_name": self.region}
            if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
                client_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
                client_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY

            self._s3_client = boto3.client("s3", **client_kwargs)
            self._sns_client = boto3.client("sns", **client_kwargs)
            self._cw_client = boto3.client("cloudwatch", **client_kwargs)
            logger.info(f"AWS Boto3 clients successfully initialized in region {self.region}")
        except Exception as e:
            logger.warning(f"AWS credentials not detected; running in hybrid-simulation mode: {e}")
            self.is_enabled = False

    # ─────────────────────────────────────────────────────────────
    # 1. AWS S3 — Issue Attachment Object Storage
    # ─────────────────────────────────────────────────────────────
    def upload_file_to_s3(self, local_path, s3_key, bucket=None):
        """
        Uploads an issue photo attachment to Amazon S3.
        Returns the public S3 URL or presigned URL.
        """
        target_bucket = bucket or self.s3_bucket

        if not self.is_enabled or not self._s3_client:
            logger.info(f"[SIMULATED AWS S3] Uploaded '{s3_key}' to bucket '{target_bucket}'.")
            return f"https://{target_bucket}.s3.{self.region}.amazonaws.com/{s3_key}"

        try:
            content_type = "image/jpeg"
            if s3_key.lower().endswith(".png"):
                content_type = "image/png"
            elif s3_key.lower().endswith(".webp"):
                content_type = "image/webp"

            self._s3_client.upload_file(
                Filename=local_path,
                Bucket=target_bucket,
                Key=s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {
                        "UploadedBy": "CampusPulse-AI",
                        "UploadedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            s3_url = f"https://{target_bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
            logger.info(f"Successfully uploaded {s3_key} to AWS S3: {s3_url}")
            return s3_url
        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS S3 upload error for {s3_key}: {e}. Retaining local file.")
            return None

    def get_presigned_url(self, s3_key, expiration=3600, bucket=None):
        """Generates a secure pre-signed Amazon S3 URL to view attachments."""
        target_bucket = bucket or self.s3_bucket
        if not self.is_enabled or not self._s3_client:
            return f"/static/uploads/{s3_key}"

        try:
            url = self._s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": target_bucket, "Key": s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating S3 presigned URL for {s3_key}: {e}")
            return f"/static/uploads/{s3_key}"

    # ─────────────────────────────────────────────────────────────
    # 2. AWS SNS — Push Notifications for Critical Alerts & SLA
    # ─────────────────────────────────────────────────────────────
    def publish_sns_alert(self, subject, message, attributes=None):
        """
        Publishes real-time push alert via AWS Simple Notification Service (SNS).
        Broadcasts to maintenance staff SMS, email subscribers, and mobile push.
        """
        if not self.is_enabled or not self._sns_client or not self.sns_topic_arn:
            logger.info(f"[SIMULATED AWS SNS] Subject: {subject} | Alert: {message}")
            return {
                "status": "simulated",
                "message_id": f"sim-sns-{int(datetime.now(timezone.utc).timestamp())}",
                "subject": subject
            }

        try:
            msg_attrs = attributes or {}
            response = self._sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject[:100],  # SNS Subject max 100 chars
                Message=message,
                MessageAttributes=msg_attrs
            )
            msg_id = response.get("MessageId")
            logger.info(f"AWS SNS Alert published successfully. MessageId: {msg_id}")
            return {"status": "published", "message_id": msg_id, "subject": subject}
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to publish AWS SNS notification: {e}")
            return {"status": "error", "error": str(e)}

    def send_critical_issue_alert(self, issue_id, category, location, priority):
        """Dispatches an emergency AWS SNS alert when a high/critical issue is logged."""
        subject = f"[CRITICAL INFRASTRUCTURE ALERT] #{issue_id} - {category}"
        message = (
            f"🚨 CAMPUSPULSE EMERGENCY ALERT 🚨\n"
            f"----------------------------------------\n"
            f"Issue ID: #{issue_id}\n"
            f"Category: {category}\n"
            f"Location: {location}\n"
            f"Priority: {priority}\n"
            f"Reported At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"----------------------------------------\n"
            f"Action Required: Immediate maintenance dispatch required per Campus SLA policy."
        )
        return self.publish_sns_alert(subject, message)

    def send_sla_breach_alert(self, issue_id, category, location, breach_hours):
        """Dispatches an urgent escalation via AWS SNS when SLA threshold is breached."""
        subject = f"[SLA BREACH ESCALATION] #{issue_id} - {category}"
        message = (
            f"⚠️ SLA VIOLATION WARNING ⚠️\n"
            f"----------------------------------------\n"
            f"Issue #{issue_id} ({category} at {location}) has exceeded SLA deadline by {breach_hours:.1f} hours.\n"
            f"This incident has been logged in AWS CloudWatch Metrics for compliance audit.\n"
            f"Supervisory intervention required."
        )
        return self.publish_sns_alert(subject, message)

    # ─────────────────────────────────────────────────────────────
    # 3. AWS CloudWatch — Custom Operational Metrics
    # ─────────────────────────────────────────────────────────────
    def put_metric_data(self, metric_name, value, unit="Count", dimensions=None):
        """
        Publishes custom infrastructure metrics to Amazon CloudWatch.
        Enables CloudWatch Alarms and dashboard monitoring.
        """
        dims = dimensions or [{"Name": "Environment", "Value": "Production"}]

        if not self.is_enabled or not self._cw_client:
            logger.info(f"[SIMULATED AWS CloudWatch] Metric: {metric_name} = {value} ({unit})")
            return True

        try:
            self._cw_client.put_metric_data(
                Namespace=self.cw_namespace,
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Dimensions": dims,
                        "Timestamp": datetime.now(timezone.utc),
                        "Value": float(value),
                        "Unit": unit
                    }
                ]
            )
            logger.info(f"CloudWatch metric recorded: {metric_name} = {value}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to push metric to AWS CloudWatch: {e}")
            return False

    def log_issue_reported_metric(self, category, priority):
        """Records metric for incoming reported issues in CloudWatch."""
        dims = [
            {"Name": "Category", "Value": category},
            {"Name": "Priority", "Value": priority}
        ]
        self.put_metric_data("IssuesReportedCount", 1, "Count", dims)
        if priority == "Critical":
            self.put_metric_data("CriticalIncidentsCount", 1, "Count", dims)

    def log_sla_breach_metric(self, category):
        """Increments SLA breach count in CloudWatch."""
        dims = [{"Name": "Category", "Value": category}]
        self.put_metric_data("SLABreachedCount", 1, "Count", dims)

    def get_aws_status(self):
        """Returns the current runtime AWS cloud integration state."""
        return {
            "aws_enabled": self.is_enabled,
            "region": self.region,
            "s3_bucket": self.s3_bucket,
            "sns_topic_arn": self.sns_topic_arn or "Configured via AWS_SNS_TOPIC_ARN",
            "cloudwatch_namespace": self.cw_namespace,
            "storage_provider": "Amazon S3 (with local fallback)" if self.is_enabled else "Local Disk (S3-Ready)",
            "notification_provider": "Amazon SNS (with in-app fallback)" if self.is_enabled else "In-App DB (SNS-Ready)",
            "monitoring_provider": "Amazon CloudWatch" if self.is_enabled else "Local App Logs (CloudWatch-Ready)"
        }

# Global singleton instance
aws_service = AWSService()
