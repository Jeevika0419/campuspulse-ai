# CampusPulse AI — Cloud-Based Intelligent Campus Infrastructure Issue Prediction and Resolution System

> **Academic Agile + DevOps Project**  
> *"Smarter Campus. Faster Resolution. Predictive Maintenance."*

---

## 📌 Executive Overview
CampusPulse AI is an enterprise-grade academic platform built with Flask, MySQL, Machine Learning, Docker, Jenkins CI/CD, and AWS Cloud Architecture. The platform bridges students, administrative leadership, and field engineering maintenance teams to streamline issue reporting, track SLAs, visualize campus problem hotspots, and proactively prevent recurring infrastructure breakdowns using machine learning.

---

## 🏗️ Sprint Progress & Architecture Status

| Sprint | Domain | Status | Key Deliverables |
| :--- | :--- | :---: | :--- |
| **Sprint 1** | **Authentication & Foundation UI** | **COMPLETED** | Hashed auth, Role RBAC (Student, Admin, Maintenance), 3 Dedicated Dashboards, Notification system foundation, Dark Theme UI, Pytest Suite |
| **Sprint 2** | Issue Lifecycle & Attachments | Upcoming | Issue reporting form, Image upload, Status transitions, History audit logging |
| **Sprint 3** | Admin Command & SLA Engine | Upcoming | Dynamic SLA countdown timers, Hotspot clustering, Team dispatch, CSV reporting |
| **Sprint 4** | Intelligent ML Recurrence Engine | Upcoming | Feature extraction, Scikit-learn Random Forest model, Recurrence risk explanation |
| **Sprint 5** | Containerization & DevOps | Upcoming | Docker container, Jenkinsfile CI/CD pipeline, Automated testing |
| **Sprint 6** | AWS Cloud Architecture | Upcoming | EC2, RDS MySQL, S3 attachments, CloudWatch, SNS alerts |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.0+ running on `localhost:3306`
- Database: `campus_issue_system`

### 2. Environment Configuration
Copy `.env.example` to `.env` and verify database credentials:
```bash
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=campus_issue_system
MYSQL_PORT=3306
SECRET_KEY=campuspulse-ai-secret-key-prod-ready-secure
```

### 3. Run the Application
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Start the Flask development server
python app.py
```
Access the application at: `http://127.0.0.1:5000`

---

## 🧪 Automated Testing
Run the comprehensive test suite with `pytest`:
```bash
.\venv\Scripts\pytest -v tests/
```

---

## 🔑 Default Seeded Demo Accounts (for Viva / Presentation)

| Role | Email | Password | Primary Console |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@campuspulse.edu` | `Admin@123` | Executive Analytics & Hotspot Hub (`/admin/dashboard`) |
| **Maintenance Staff** | `staff@campuspulse.edu` | `Staff@123` | Field Ops Dispatch & Work Orders (`/maintenance/dashboard`) |
| **Student** | `student@campuspulse.edu` | `Student@123` | Student Issue Hub & Tracking (`/student/dashboard`) |

*Self-registration is also supported at `/register` with instantaneous password hashing (PBKDF2/Argon2).*
