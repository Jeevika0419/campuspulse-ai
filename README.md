# 🏫 CampusPulse AI — Cloud-Based Intelligent Campus Infrastructure Issue Prediction and Resolution System

> **Academic Agile + DevOps Project**
> *"Smarter Campus. Faster Resolution. Predictive Maintenance."*

---

## 📌 Executive Overview

**CampusPulse AI** is a cloud-ready, intelligent campus infrastructure issue management platform built using modern Agile and DevOps methodologies. The system bridges **Students**, **Administrative Leadership**, and **Maintenance Engineering Teams** to streamline infrastructure issue reporting, real-time tracking, SLA compliance monitoring, and **AI-driven recurrence risk prediction**.

### Core Value Propositions
- 🔐 **Secure Role-Based Access** — Students, Admins, and Maintenance staff each have dedicated dashboards
- 📝 **Smart Issue Lifecycle** — Reporting → Assignment → In Progress → Resolved → Closed with full audit trail
- ⏱️ **SLA Engine** — Auto-computed SLA deadlines with real-time breach monitoring
- 🤖 **AI Recurrence Engine** — Feature-weighted ML prediction for infrastructure failure recurrence
- 📊 **Executive Analytics** — Interactive Chart.js dashboards with KPI metrics, hotspot clustering, and team performance
- 🐳 **DevOps Pipeline** — Docker containerization + Jenkins CI/CD for automated deployment
- ☁️ **Cloud Architecture** — AWS-ready (EC2, RDS MySQL, S3, CloudWatch)

---

## 🏗️ Sprint Progress & Agile Delivery Timeline

| Sprint | Domain | Status | Key Deliverables |
| :--- | :--- | :---: | :--- |
| **Sprint 1** | Authentication & Foundation UI | ✅ **COMPLETED** | Hashed auth (PBKDF2), RBAC (Student/Admin/Maintenance), 3 Dashboards, Dark theme UI, Notification system |
| **Sprint 2** | Issue Lifecycle & Attachments | ✅ **COMPLETED** | Issue reporting with image uploads, Status transitions, Admin team dispatch, Resolution proof, Audit history, Student reopen/feedback/ratings |
| **Sprint 3** | Admin Command & SLA Engine | ✅ **COMPLETED** | SLA countdown monitoring, Hotspot clustering engine, Team performance metrics, CSV audit export, Seed demo dataset |
| **Sprint 4** | Intelligent ML Recurrence Engine | ✅ **COMPLETED** | Feature-weighted prediction model (simulates Random Forest), Real-time API endpoint, Auto-risk update on resolution, Explainable AI panel |
| **Sprint 5** | Containerization & CI/CD DevOps | ✅ **COMPLETED** | Dockerfile (multi-stage), Docker Compose, Jenkinsfile (9-stage pipeline), Automated testing integration |
| **Sprint 6** | AWS Cloud Architecture | 📋 **DOCUMENTED** | EC2, RDS MySQL, S3 uploads, CloudWatch monitoring, SNS alerts (architecture documented, ready for deployment) |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python** 3.10+ installed
- **MySQL Server** 8.0+ running on `localhost:3306`
- **Database**: Create `campus_issue_system` database before first run

### 2. Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd campus-issue-system

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` → `.env` and set your database credentials:
```ini
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=campus_issue_system
MYSQL_PORT=3306
SECRET_KEY=campuspulse-ai-secret-key-prod-ready-secure
```

### 4. Run the Application
```bash
python app.py
```
Access: **http://127.0.0.1:5000**

> The database schema and seed data are automatically initialized on first startup.

---

## 🔑 Demo Accounts (Presentation / Viva)

| Role | Email | Password | Dashboard |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@campuspulse.edu` | `Admin@123` | Executive Analytics & Dispatch (`/admin/dashboard`) |
| **Maintenance Staff** | `staff@campuspulse.edu` | `Staff@123` | Ops Dispatch & Work Queue (`/maintenance/dashboard`) |
| **Student** | `student@campuspulse.edu` | `Student@123` | Issue Hub & Tracking (`/student/dashboard`) |

> 💡 Click **"⚡ Seed Demo Dataset"** on the Admin Dashboard to populate 21 realistic campus issues for a rich demonstration.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CampusPulse AI Architecture                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────────┐    │
│  │   Student    │   │    Admin     │   │   Maintenance Staff      │    │
│  │  Dashboard   │   │  Analytics   │   │   Ops Dispatch           │    │
│  └──────┬──────┘   └──────┬───────┘   └───────────┬──────────────┘    │
│         │                 │                        │                    │
│         └─────────────────┼────────────────────────┘                   │
│                           │                                             │
│                  ┌────────▼────────┐                                    │
│                  │   Flask Server   │  ← Gunicorn (Production)         │
│                  │   (app.py)       │                                    │
│                  └────────┬────────┘                                    │
│                           │                                             │
│         ┌─────────────────┼─────────────────┐                          │
│         │                 │                 │                            │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────────┐               │
│  │ Auth Routes  │  │Issue Routes │  │ Admin/Maint/API  │               │
│  │ (Blueprint)  │  │ (Blueprint) │  │   (Blueprints)   │               │
│  └──────┬──────┘  └──────┬──────┘  └───────┬──────────┘               │
│         └─────────────────┼─────────────────┘                          │
│                           │                                             │
│    ┌──────────────────────┼──────────────────────┐                     │
│    │                      │                      │                      │
│  ┌─▼────────────┐  ┌─────▼──────────┐  ┌────────▼──────────┐         │
│  │ ML Service   │  │ SLA Service    │  │ Notification      │         │
│  │ (Prediction) │  │ (Compliance)   │  │ Service           │         │
│  └──────────────┘  └────────────────┘  └───────────────────┘         │
│                           │                                             │
│                  ┌────────▼────────┐                                    │
│                  │   MySQL 8.0     │  ← AWS RDS (Production)           │
│                  │  (5 Tables)     │                                    │
│                  └─────────────────┘                                    │
│                                                                         │
│  DevOps Pipeline: Git → Jenkins → Docker → AWS ECR → EC2              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
campus-issue-system/
├── app.py                          # Flask application entry point
├── config.py                       # Environment variable configuration
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Multi-stage production Docker image
├── docker-compose.yml              # Full-stack local dev environment
├── Jenkinsfile                     # 9-stage CI/CD pipeline
├── .env / .env.example             # Environment configuration
├── .gitignore / .dockerignore      # Ignore rules
│
├── database/
│   ├── db.py                       # DB connection + schema init
│   ├── schema.sql                  # MySQL schema DDL
│   └── seed_demo_data.py           # Realistic demo issue seeder
│
├── routes/
│   ├── auth_routes.py              # Login, Register, Logout, RBAC decorators, Notification APIs
│   ├── student_routes.py           # Student dashboard + KPI
│   ├── admin_routes.py             # Admin analytics, SLA monitor, CSV export, team management
│   ├── maintenance_routes.py       # Ops dispatch queue
│   └── issue_routes.py             # Full issue lifecycle + ML prediction API
│
├── services/
│   ├── analytics_service.py        # KPI metrics, chart data, hotspot clustering, team performance
│   ├── ml_service.py               # 🤖 AI Recurrence Prediction Engine (Sprint 4)
│   ├── notification_service.py     # In-app notification system
│   ├── priority_service.py         # Smart priority escalation calculator
│   ├── sla_service.py              # SLA deadline + breach detection
│   └── upload_service.py           # Secure image upload handler
│
├── templates/
│   ├── base.html                   # Master layout (sidebar, topbar, notifications)
│   ├── auth/                       # Login & Register pages
│   ├── admin/                      # Dashboard, SLA Monitor, Teams
│   ├── student/                    # Student Dashboard
│   ├── maintenance/                # Ops Dispatch Dashboard
│   ├── issues/                     # Report, List, Detail (with AI panel)
│   └── errors/                     # 403, 404, 500 error pages
│
├── static/
│   ├── css/style.css               # Complete dark-theme design system
│   └── js/main.js                  # Notification polling + UI interactions
│
├── tests/
│   ├── test_auth.py                # Authentication & RBAC tests (11 tests)
│   ├── test_issues.py              # Issue lifecycle tests (6 tests)
│   ├── test_analytics.py           # Analytics & admin tests (6 tests)
│   └── test_ml_prediction.py       # ML prediction engine tests (7 tests)
│
└── uploads/                        # User-uploaded evidence images
```

---

## 🤖 AI Recurrence Prediction Engine (Sprint 4)

### How It Works
The ML service (`services/ml_service.py`) uses a **feature-weighted scoring system** that simulates a trained Random Forest classifier. It evaluates 6 engineered features:

| Feature | Weight | Description |
| :--- | :---: | :--- |
| **Location Hotspot** | 28% | Is this location a known problem cluster? |
| **Category Prone** | 22% | Does this category historically recur? (Wi-Fi, AC, Plumbing) |
| **Prior Issues** | 20% | How many similar past issues at this location? |
| **Severity Level** | 15% | Higher severity → higher recurrence probability |
| **Resolution Time** | 10% | Slow resolutions suggest incomplete fixes |
| **Reopen History** | 5% | Were similar issues reopened before? |

### Risk Level Classification
- **High** (≥70% score) → Systemic fix strongly recommended
- **Medium** (40–70%) → Schedule preventive inspection within 30 days
- **Low** (<40%) → Standard resolution sufficient

### Explainable AI
Every prediction includes human-readable **feature explanations** showing exactly why the risk was assessed at that level — suitable for academic presentation and viva demonstration.

### API Endpoint
```http
POST /api/issues/predict-recurrence
Content-Type: application/json

{
  "issue_type": "Wi-Fi & Network Connectivity",
  "location": "Academic Block A - 3rd Floor",
  "severity": "High",
  "issue_id": 5
}
```

---

## 🧪 Automated Testing

Run the full test suite (30 test cases):
```bash
.\venv\Scripts\pytest -v tests/
```

| Test Module | Tests | Coverage |
| :--- | :---: | :--- |
| `test_auth.py` | 11 | Login, Register, Logout, RBAC enforcement, Session management |
| `test_issues.py` | 6 | Report, Assign, Status transitions, Feedback, Reopen, Authorization |
| `test_analytics.py` | 6 | KPI metrics, Charts, SLA monitoring, CSV export, Team management |
| `test_ml_prediction.py` | 7 | Risk prediction, Feature scoring, DB persistence, API endpoint |

---

## 🐳 Docker & DevOps (Sprint 5)

### Run with Docker Compose
```bash
# Build and start the entire stack (Flask + MySQL)
docker-compose up --build

# Access the app
http://localhost:5000
```

### Jenkins CI/CD Pipeline (9 Stages)
```
Checkout → Environment Setup → Code Quality (flake8) → Test DB Init
→ Automated Testing (Pytest) → Docker Build → Push to AWS ECR
→ Deploy to EC2 → Production Smoke Test
```

See [`Jenkinsfile`](Jenkinsfile) for the complete declarative pipeline configuration.

---

## ☁️ AWS Cloud Architecture (Sprint 6)

| Service | Purpose |
| :--- | :--- |
| **EC2** (t2.micro) | Flask application host with Docker container |
| **RDS MySQL** (db.t3.micro) | Managed database with automated backups |
| **S3 Bucket** | Static asset and upload image storage |
| **CloudWatch** | Application monitoring and log aggregation |
| **SNS** | Email/SMS alerts for SLA breaches and critical issues |
| **ECR** | Docker image registry for container versioning |

---

## 📊 Key Features Demonstrated

### For Viva / Academic Presentation
1. ✅ **Secure Authentication** — Hashed passwords (PBKDF2), session management, RBAC
2. ✅ **Three Role-Based Dashboards** — Student, Admin, Maintenance with distinct UIs
3. ✅ **Complete Issue Lifecycle** — Report → Assign → Progress → Resolve → Close → Reopen
4. ✅ **SLA Compliance Engine** — Auto-calculated deadlines, breach detection, countdown timers
5. ✅ **Image Upload & Evidence** — Report photos + Resolution proof attachments
6. ✅ **AI/ML Prediction** — Recurrence risk scoring with explainable feature analysis
7. ✅ **Interactive Charts** — Chart.js doughnut, bar, and line trend visualizations
8. ✅ **Campus Hotspot Detection** — Location-based problem clustering with critical markers
9. ✅ **In-App Notifications** — Real-time notification bell with unread count and polling
10. ✅ **Audit Trail** — Immutable status change history with actor and timestamp tracking
11. ✅ **Student Feedback** — 1-5 star rating system with resolution comments
12. ✅ **CSV Data Export** — Audit-ready campus issue export for administration
13. ✅ **Docker Containerization** — Production-ready Dockerfile with Gunicorn WSGI
14. ✅ **CI/CD Pipeline** — Jenkins declarative pipeline with 9 automated stages
15. ✅ **Comprehensive Testing** — 30 Pytest test cases covering auth, issues, analytics, ML
16. ✅ **Dark Theme UI** — Premium glassmorphic dark design with Outfit + Plus Jakarta Sans fonts

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.12, Flask 3.0, Jinja2 Templates |
| **Database** | MySQL 8.0, mysql-connector-python |
| **Security** | Werkzeug password hashing, Session-based auth, RBAC decorators |
| **AI/ML** | Feature-weighted scoring (simulates scikit-learn Random Forest) |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Chart.js 4.x |
| **Typography** | Google Fonts (Outfit, Plus Jakarta Sans) |
| **Testing** | Pytest 9.x (30 automated test cases) |
| **Container** | Docker, Docker Compose |
| **CI/CD** | Jenkins Declarative Pipeline |
| **Cloud** | AWS (EC2, RDS, S3, CloudWatch, SNS, ECR) |
| **Version Control** | Git, GitHub |

---

## 📄 License

This project is developed as an academic submission for the course project on **Cloud-Based Intelligent Campus Infrastructure Issue Prediction and Resolution System using Agile and DevOps**.

---

*Built with ❤️ by CampusPulse AI Team*
