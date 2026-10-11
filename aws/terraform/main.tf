# CampusPulse AI — Terraform Infrastructure as Code (IaC)
# Provisions AWS VPC, EC2, RDS MySQL, S3, SNS, IAM, and CloudWatch

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default     = "ap-south-1"
  description = "AWS region for deployment"
}

variable "environment" {
  default = "production"
}

# 1. AWS VPC & Networking
resource "aws_vpc" "campus_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "campuspulse-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.campus_vpc.id
  tags   = { Name = "campuspulse-igw" }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.campus_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags                    = { Name = "campuspulse-public-subnet" }
}

resource "aws_subnet" "private_subnet_a" {
  vpc_id            = aws_vpc.campus_vpc.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"
  tags              = { Name = "campuspulse-private-db-a" }
}

resource "aws_subnet" "private_subnet_b" {
  vpc_id            = aws_vpc.campus_vpc.id
  cidr_block        = "10.0.20.0/24"
  availability_zone = "${var.aws_region}b"
  tags              = { Name = "campuspulse-private-db-b" }
}

# 2. AWS S3 Bucket
resource "aws_s3_bucket" "attachments" {
  bucket_prefix = "campuspulse-attachments-"
}

resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket                  = aws_s3_bucket.attachments.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 3. AWS SNS Topic
resource "aws_sns_topic" "infrastructure_alerts" {
  name = "campuspulse-infrastructure-alerts"
}

# 4. AWS RDS Subnet Group & Database
resource "aws_db_subnet_group" "rds_subnet" {
  name       = "campuspulse-rds-subnets"
  subnet_ids = [aws_subnet.private_subnet_a.id, aws_subnet.private_subnet_b.id]
}

resource "aws_security_group" "rds_sg" {
  name        = "campuspulse-rds-sg"
  description = "Allow MySQL traffic from EC2"
  vpc_id      = aws_vpc.campus_vpc.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }
}

resource "aws_db_instance" "mysql_db" {
  identifier             = "campuspulse-mysql"
  allocated_storage      = 20
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  db_name                = "campus_issue_system"
  username               = "admin"
  password               = "CampusPulse@2025"
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true
}

# 5. AWS EC2 Instance Security Group & Compute Node
resource "aws_security_group" "ec2_sg" {
  name        = "campuspulse-ec2-sg"
  description = "Allow HTTP and SSH traffic"
  vpc_id      = aws_vpc.campus_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "app_server" {
  ami           = "ami-03f4878e83d3e318f"
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "campuspulse-ec2-node"
  }
}

# 6. AWS CloudWatch SLA Alarm
resource "aws_cloudwatch_metric_alarm" "sla_breach_alarm" {
  alarm_name          = "campuspulse-high-sla-breaches"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "SLABreachedCount"
  namespace           = "CampusPulse/Infrastructure"
  period              = 300
  statistic           = "Sum"
  threshold           = 2
  alarm_actions       = [aws_sns_topic.infrastructure_alerts.arn]
}
