/**
 * Analytics & Insights Chart.js Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
});

async function initCharts() {
    try {
        // Fetch Trend Data
        const trendRes = await api.get('/api/analytics/weekly-trend');
        if (trendRes.success && trendRes.data) {
            renderWeeklyChart(trendRes.data);
        }

        // Fetch Distribution Data
        const distRes = await api.get('/api/analytics/subject-distribution');
        if (distRes.success && distRes.data) {
            renderDistributionChart(distRes.data);
        }

        // Fetch Recent Focus Sessions (including completed tasks)
        const sessionsRes = await api.get('/api/timer/history?limit=30');
        if (sessionsRes.success && sessionsRes.sessions) {
            renderLiveFocusSessions(sessionsRes.sessions);
        }
    } catch (err) {
        console.error("Error loading analytics data:", err);
    }
}

function renderLiveFocusSessions(sessions) {
    const tbody = document.getElementById('analyticsSessionsTableBody');
    const emptyMsg = document.getElementById('analyticsEmptySessionsMsg');
    if (!tbody) return;

    if (!sessions || sessions.length === 0) {
        tbody.innerHTML = '';
        if (emptyMsg) emptyMsg.style.display = 'block';
        return;
    }

    if (emptyMsg) emptyMsg.style.display = 'none';

    const escapeHtml = (str) => {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    };

    tbody.innerHTML = sessions.map(sess => {
        const dateStr = sess.created_at ? sess.created_at.substring(0, 16) : '';
        const subjName = escapeHtml(sess.subject_name || 'General');
        const subjColor = sess.subject_color || '#6366f1';
        const mins = sess.duration_minutes || 0;
        const notes = escapeHtml(sess.notes || (sess.task_title ? `Task: ${sess.task_title}` : '-'));

        let badgeHtml = '';
        if (sess.task_id || (sess.notes && sess.notes.startsWith('Completed Task'))) {
            badgeHtml = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.75rem; font-weight: 600;">✓ Task Focus</span>`;
        } else if (sess.session_type === 'pomodoro') {
            badgeHtml = `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); font-size: 0.75rem;">⏱️ Pomodoro</span>`;
        } else if (sess.session_type === 'stopwatch') {
            badgeHtml = `<span class="badge" style="background: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); font-size: 0.75rem;">⏱️ Stopwatch</span>`;
        } else {
            badgeHtml = `<span class="badge" style="background: rgba(255,255,255,0.06); font-size: 0.75rem;">${escapeHtml(sess.session_type || 'custom')}</span>`;
        }

        return `
            <tr>
                <td style="font-family: var(--font-mono); color: var(--text-secondary);">${dateStr}</td>
                <td><span style="font-weight: 600; color: ${subjColor};">${subjName}</span></td>
                <td>${badgeHtml}</td>
                <td style="font-weight: 700; font-family: var(--font-mono); color: var(--text-primary);">${mins} mins</td>
                <td style="color: var(--text-secondary); font-size: 0.85rem;">${notes}</td>
            </tr>
        `;
    }).join('');
}

function renderWeeklyChart(data) {
    const ctx = document.getElementById('weeklyStudyChart');
    if (!ctx || typeof Chart === 'undefined') return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Study Hours',
                data: data.hours,
                backgroundColor: 'rgba(99, 102, 241, 0.65)',
                borderColor: '#6366f1',
                borderWidth: 2,
                borderRadius: 8,
                hoverBackgroundColor: 'rgba(99, 102, 241, 0.9)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f8fafc',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: (context) => `${context.parsed.y} Hours studied`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

function renderDistributionChart(data) {
    const ctx = document.getElementById('subjectDistChart');
    if (!ctx || typeof Chart === 'undefined') return;

    if (!data.labels || data.labels.length === 0) {
        ctx.parentElement.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:0.85rem;">No study sessions logged yet</div>`;
        return;
    }

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.hours,
                backgroundColor: data.colors,
                borderWidth: 2,
                borderColor: '#111827'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', boxWidth: 12, padding: 16 }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f8fafc',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: (context) => `${context.label}: ${context.parsed} hrs`
                    }
                }
            }
        }
    });
}
