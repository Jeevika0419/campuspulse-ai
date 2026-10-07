/* CampusPulse AI - Main Interactive Script */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Mobile Sidebar Toggle
    const mobileMenuBtn = document.getElementById("mobileMenuBtn");
    const sidebar = document.querySelector(".sidebar");
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });
    }

    // 2. Auto Dismiss Flash Alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-10px)";
            alert.style.transition = "all 0.3s ease";
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // 3. Notification Drawer Functionality
    const notifBtn = document.getElementById("notifToggleBtn");
    const notifModal = document.getElementById("notificationModal");
    const notifList = document.getElementById("notificationList");
    const notifBadge = document.getElementById("notifBadge");
    const markAllReadBtn = document.getElementById("markAllReadBtn");

    if (notifBtn && notifModal) {
        notifBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = notifModal.style.display === "block";
            if (isOpen) {
                notifModal.style.display = "none";
            } else {
                notifModal.style.display = "block";
                loadNotifications();
            }
        });

        // Close on click outside
        document.addEventListener("click", (e) => {
            if (notifModal && !notifModal.contains(e.target) && e.target !== notifBtn) {
                notifModal.style.display = "none";
            }
        });
    }

    function loadNotifications() {
        if (!notifList) return;
        fetch("/api/notifications")
            .then(res => res.json())
            .then(data => {
                if (!data.notifications || data.notifications.length === 0) {
                    notifList.innerHTML = `
                        <div style="padding: 24px; text-align: center; color: var(--text-dim); font-size: 0.85rem;">
                            No new notifications
                        </div>
                    `;
                    return;
                }

                notifList.innerHTML = data.notifications.map(n => `
                    <div class="notification-item ${n.is_read ? '' : 'unread'}" data-id="${n.notification_id}">
                        <div class="notif-body">
                            <h5>${escapeHtml(n.title)}</h5>
                            <p>${escapeHtml(n.message)}</p>
                            <div class="notif-time">${formatDate(n.created_at)}</div>
                        </div>
                    </div>
                `).join("");

                // Add click listener to mark read
                document.querySelectorAll(".notification-item.unread").forEach(item => {
                    item.addEventListener("click", () => {
                        const notifId = item.getAttribute("data-id");
                        fetch(`/api/notifications/${notifId}/read`, { method: "POST" })
                            .then(() => {
                                item.classList.remove("unread");
                                updateUnreadCount();
                            });
                    });
                });
            })
            .catch(err => console.error("Error loading notifications:", err));
    }

    function updateUnreadCount() {
        fetch("/api/notifications/unread-count")
            .then(res => res.json())
            .then(data => {
                if (notifBadge) {
                    if (data.unread_count > 0) {
                        notifBadge.textContent = data.unread_count;
                        notifBadge.style.display = "flex";
                    } else {
                        notifBadge.style.display = "none";
                    }
                }
            });
    }

    if (markAllReadBtn) {
        markAllReadBtn.addEventListener("click", () => {
            fetch("/api/notifications/mark-all-read", { method: "POST" })
                .then(() => {
                    loadNotifications();
                    if (notifBadge) notifBadge.style.display = "none";
                });
        });
    }
});

// Helper functions
function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
        const d = new Date(dateStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' · ' + d.toLocaleDateString();
    } catch {
        return dateStr;
    }
}

// 1-Click Demo Login credentials filler
function fillDemoLogin(email, password) {
    const emailField = document.getElementById("email");
    const passField = document.getElementById("password");
    if (emailField && passField) {
        emailField.value = email;
        passField.value = password;
        // Visual indicator
        emailField.style.borderColor = "var(--accent-cyan)";
        passField.style.borderColor = "var(--accent-cyan)";
    }
}
