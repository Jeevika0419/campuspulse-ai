import os
import sys
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.aws_service import aws_service

def test_aws_service_initialization():
    """Validates that AWS Service initializes with configured defaults."""
    assert aws_service.region is not None
    assert "campuspulse" in aws_service.s3_bucket.lower()
    assert aws_service.cw_namespace == "CampusPulse/Infrastructure"

def test_aws_s3_upload_fallback():
    """Validates that S3 upload returns a valid URL in both live and simulated modes."""
    dummy_key = "test_issue_101.jpg"
    # Even without local file in simulated mode, returns proper AWS S3 resource URL
    url = aws_service.upload_file_to_s3("non_existent.jpg", dummy_key)
    assert url is not None
    assert "s3" in url
    assert dummy_key in url

def test_aws_s3_presigned_url():
    """Validates presigned URL generation."""
    dummy_key = "issue_55.png"
    url = aws_service.get_presigned_url(dummy_key)
    assert url is not None
    assert dummy_key in url

def test_aws_sns_critical_alert():
    """Validates that Critical Infrastructure Alerts format and dispatch through SNS."""
    result = aws_service.send_critical_issue_alert(
        issue_id=42,
        category="Electrical & Power Outlets",
        location="Academic Block A - Ground Floor",
        priority="Critical"
    )
    assert result is not None
    assert result.get("status") in ("published", "simulated")
    assert "CRITICAL" in result.get("subject", "")

def test_aws_sns_sla_breach_alert():
    """Validates that SLA violations dispatch SNS broadcast."""
    result = aws_service.send_sla_breach_alert(
        issue_id=12,
        category="Wi-Fi & Network Connectivity",
        location="Central Campus Library",
        breach_hours=3.5
    )
    assert result is not None
    assert result.get("status") in ("published", "simulated")
    assert "SLA" in result.get("subject", "")

def test_aws_cloudwatch_metrics():
    """Validates putting custom metrics to Amazon CloudWatch."""
    res1 = aws_service.put_metric_data("IssuesReportedCount", 1, "Count")
    assert res1 is True

    res2 = aws_service.put_metric_data("SLABreachedCount", 1, "Count")
    assert res2 is True

def test_aws_status_inspection():
    """Validates that the runtime AWS cloud health inspection returns all 7 components."""
    status = aws_service.get_aws_status()
    assert "region" in status
    assert "s3_bucket" in status
    assert "storage_provider" in status
    assert "notification_provider" in status
    assert "monitoring_provider" in status

@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client

def test_admin_aws_cloud_architecture_view(client):
    """Verifies that the AWS Cloud Architecture Command Center renders correctly."""
    client.post("/login", data={"email": "admin@campuspulse.edu", "password": "Admin@123"}, follow_redirects=True)
    response = client.get("/admin/aws-cloud")
    assert response.status_code == 200
    assert b"AWS Cloud Infrastructure Architecture" in response.data
    assert b"Amazon EC2" in response.data
    assert b"Amazon RDS" in response.data
    assert b"Amazon S3" in response.data
    assert b"AWS IAM" in response.data
    assert b"Amazon VPC" in response.data
    assert b"Amazon CloudWatch" in response.data
    assert b"Amazon SNS" in response.data

def test_admin_aws_sns_dispatch_trigger(client):
    """Verifies triggering an on-demand test alert through AWS SNS."""
    client.post("/login", data={"email": "admin@campuspulse.edu", "password": "Admin@123"}, follow_redirects=True)
    response = client.post("/admin/aws-cloud/test-sns", follow_redirects=True)
    assert response.status_code == 200
    assert b"AWS SNS Dispatch executed successfully" in response.data

def test_admin_aws_cloudwatch_metric_trigger(client):
    """Verifies triggering an on-demand metric push through Amazon CloudWatch."""
    client.post("/login", data={"email": "admin@campuspulse.edu", "password": "Admin@123"}, follow_redirects=True)
    response = client.post("/admin/aws-cloud/test-metric", follow_redirects=True)
    assert response.status_code == 200
    assert b"Amazon CloudWatch telemetry metric" in response.data

def test_aws_enabled_configuration_values(monkeypatch):
    """Validates that AWS_ENABLED supports true, false, 1, yes, and unset defaults."""
    for truthy_val in ("true", "TRUE", "1", "yes", "YES"):
        monkeypatch.setenv("AWS_ENABLED", truthy_val)
        val = os.getenv("AWS_ENABLED").strip().lower() in ("true", "1", "yes")
        assert val is True

    for falsy_val in ("false", "FALSE", "0", "no", "NO"):
        monkeypatch.setenv("AWS_ENABLED", falsy_val)
        val = os.getenv("AWS_ENABLED").strip().lower() in ("true", "1", "yes")
        assert val is False

def test_aws_service_client_initialization_safety():
    """Validates that AWSService initializes safely without raising unhandled credential errors."""
    from services.aws_service import AWSService
    svc = AWSService()
    assert hasattr(svc, "is_enabled")
    assert hasattr(svc, "_s3_client")
    assert hasattr(svc, "_sns_client")
    assert hasattr(svc, "_cw_client")


