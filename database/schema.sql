-- ==========================================================
-- CampusPulse AI - Database Schema
-- Academic Agile & DevOps Project
-- Database: campus_issue_system
-- ==========================================================

CREATE DATABASE IF NOT EXISTS campus_issue_system;
USE campus_issue_system;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'student', 'admin', 'maintenance'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. Maintenance Teams Table
CREATE TABLE IF NOT EXISTS maintenance_teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,
    team_description VARCHAR(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. Issues Table
CREATE TABLE IF NOT EXISTS issues (
    issue_id INT AUTO_INCREMENT PRIMARY KEY,
    reported_by INT NOT NULL,
    issue_type VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'Low', 'Medium', 'High', 'Critical'
    priority VARCHAR(20) DEFAULT 'Medium', -- 'Low', 'Medium', 'High', 'Critical'
    status VARCHAR(30) DEFAULT 'Reported', -- 'Reported', 'Under Review', 'Assigned', 'In Progress', 'On Hold', 'Resolved', 'Closed', 'Reopened'
    assigned_team INT DEFAULT NULL,
    image_path VARCHAR(255) DEFAULT NULL,
    resolution_image VARCHAR(255) DEFAULT NULL,
    recurrence_risk VARCHAR(20) DEFAULT 'Low', -- 'Low', 'Medium', 'High'
    sla_deadline DATETIME DEFAULT NULL,
    feedback_rating INT DEFAULT NULL,
    feedback_comment TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL DEFAULT NULL,
    KEY idx_reported_by (reported_by),
    KEY idx_assigned_team (assigned_team),
    CONSTRAINT fk_issues_user FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_issues_team FOREIGN KEY (assigned_team) REFERENCES maintenance_teams(team_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4. Issue History / Audit Log Table
CREATE TABLE IF NOT EXISTS issue_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    old_status VARCHAR(30) DEFAULT NULL,
    new_status VARCHAR(30) DEFAULT NULL,
    changed_by INT DEFAULT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(255) DEFAULT NULL,
    KEY idx_issue_id (issue_id),
    KEY idx_changed_by (changed_by),
    CONSTRAINT fk_history_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id) ON DELETE CASCADE,
    CONSTRAINT fk_history_user FOREIGN KEY (changed_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    issue_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
