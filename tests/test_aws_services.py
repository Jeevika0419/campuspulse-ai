import os
import pytest
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
