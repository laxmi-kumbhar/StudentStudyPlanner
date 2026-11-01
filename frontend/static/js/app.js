/**
 * ==========================================================================
 * STUDYFLOW - MAIN JAVASCRIPT APP (app.js)
 * Controls View Switching, Pomodoro Engine, Kanban, Syllabus, & Charts
 * ==========================================================================
 */

let globalTimer = null;
let weeklyChartInstance = null;
let subjectChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    initNavigationTabs();
    initGlobalTimer();
    initTaskHandlers();
    initSubjectHandlers();
    initTimetableHandlers();
    initExamHandlers();
    initAnalyticsCharts();
    initTimetableDaysToggle();
    loadLiveAppState();
});

/* ================= NAVIGATION & VIEW SWITCHING ================= */
function initNavigationTabs() {
    const navItems = document.querySelectorAll('.nav-tab-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetView = item.dataset.view;
            switchView(targetView);
        });
    });

    // Check URL hash (e.g. #timer, #tasks, #subjects)
    const hash = window.location.hash.replace('#', '');
    if (hash && document.getElementById(`view-${hash}`)) {
        switchView(hash);
    }
}

window.switchView = function (viewName) {
    // Update navigation active state across sidebar and bottom navigation
    document.querySelectorAll('.nav-tab-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Update section visibility
    document.querySelectorAll('.view-section').forEach(sec => {
        sec.classList.remove('active');
    });

    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
        targetSection.classList.add('active');
        window.location.hash = viewName;
    }

    // Close mobile sidebar if open
    if (typeof window.closeMobileSidebar === 'function') {
        window.closeMobileSidebar();
    }

    // Scroll to top smoothly on mobile view change
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Refresh charts if opening analytics
    if (viewName === 'analytics') {
        setTimeout(loadAnalyticsData, 100);
    }
};

/* ================= POMODORO TIMER ENGINE ================= */
function initGlobalTimer() {
    const timeDisplay = document.getElementById('timerCountdown');
    const circleProgress = document.getElementById('timerProgressRing');
    const statusText = document.getElementById('timerStatusText');
    const circumference = 2 * Math.PI * 130; // 816.81

    if (!timeDisplay) return;

    globalTimer = new PomodoroTimer({
        onTick: (formattedTime, progressPct) => {
            if (timeDisplay) timeDisplay.textContent = formattedTime;
            if (circleProgress) {
                const offset = circumference - (progressPct / 100) * circumference;
                circleProgress.style.strokeDashoffset = offset;
            }
            document.title = `(${formattedTime}) StudyFlow Planner`;
        },
        onStateChange: (isRunning, mode) => {
            const toggleBtn = document.getElementById('timerToggleBtn');
            if (toggleBtn) {
                toggleBtn.textContent = isRunning ? 'Pause' : 'Start Focus';
                toggleBtn.className = isRunning ? 'btn btn-secondary btn-timer-primary' : 'btn btn-primary btn-timer-primary';
            }
            if (statusText) {
                statusText.textContent = isRunning ? `${mode.replace('_', ' ')} in progress` : 'Ready to Focus';
            }
        },
        onComplete: async (mode, minutes) => {
            showToast(`Focus session completed! (${minutes} mins)`, 'success');

            if (mode === 'pomodoro' || mode === 'custom') {
                const subjectSelect = document.getElementById('timerSubjectSelect');
                const subjectId = subjectSelect ? subjectSelect.value : null;
                const notesInput = document.getElementById('timerNotesInput');
                const notes = notesInput ? notesInput.value : '';

                if (subjectId) {
                    try {
                        await api.post('/api/timer/session', {
                            subject_id: parseInt(subjectId),
                            duration_minutes: minutes,
                            session_type: mode,
                            notes: notes
                        });
                        showToast(`Logged ${minutes} mins study time to SQLite!`, 'success');
                        setTimeout(() => window.location.reload(), 1200);
                    } catch (err) {
                        console.error("Failed to log session:", err);
                    }
                }
            }
        }
    });

    // Mode Buttons
    document.querySelectorAll('.timer-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (mode === 'custom') {
                if (typeof openModal === 'function') {
                    openModal('customTimerModal');
                }
                return;
            }

            document.querySelectorAll('.timer-mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            globalTimer.setMode(mode);
        });
    });

    // Custom Timer Form inside project modal
    const customTimerForm = document.getElementById('customTimerForm');
    if (customTimerForm) {
        customTimerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('customTimerMinutesInput');
            const mins = input ? parseInt(input.value) : 45;
            if (mins > 0) {
                document.querySelectorAll('.timer-mode-btn').forEach(b => b.classList.remove('active'));
                const customBtn = document.querySelector('.timer-mode-btn[data-mode="custom"]');
                if (customBtn) customBtn.classList.add('active');
                globalTimer.setMode('custom', mins);
                if (typeof closeModal === 'function') closeModal('customTimerModal');
                if (typeof showToast === 'function') showToast(`⏱️ Custom timer set to ${mins} mins`, 'success');
            }
        });
    }

    // Toggle & Reset
    const toggleBtn = document.getElementById('timerToggleBtn');
    const resetBtn = document.getElementById('timerResetBtn');
    if (toggleBtn) toggleBtn.addEventListener('click', () => globalTimer.toggle());
    if (resetBtn) resetBtn.addEventListener('click', () => globalTimer.reset());

    bindQuickSubjectCreator({
        selectId: 'timerSubjectSelect',
        quickBtnId: 'quickAddTimerSubjectBtn',
        panelId: 'quickTimerSubjectPanel',
        inputId: 'quickTimerSubjectName',
        saveBtnId: 'quickTimerSubjectSaveBtn',
        cancelBtnId: 'quickTimerSubjectCancelBtn'
    });
}

/* ================= TASKS & KANBAN ================= */
function initTaskHandlers() {
    const taskForm = document.getElementById('taskForm');
    if (taskForm) {
        taskForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(taskForm);
            const subjVal = formData.get('subject_id');
            const payload = {
                title: formData.get('title'),
                description: formData.get('description'),
                subject_id: (subjVal && subjVal !== '__create_new__') ? parseInt(subjVal) : null,
                priority: formData.get('priority'),
                due_date: formData.get('due_date'),
                estimated_minutes: parseInt(formData.get('estimated_minutes') || 30)
            };

            try {
                await api.post('/api/tasks', payload);
                showToast("Task created successfully!", "success");
                closeModal('taskModal');
                taskForm.reset();
                await loadLiveAppState();
            } catch (err) {
                console.error("Task creation failed:", err);
            }
        });
    }

    bindQuickSubjectCreator({
        selectId: 'taskSubject',
        quickBtnId: 'quickAddSubjectBtn',
        panelId: 'quickSubjectPanel',
        inputId: 'quickSubjectName',
        saveBtnId: 'quickSubjectSaveBtn',
        cancelBtnId: 'quickSubjectCancelBtn'
    });

    bindQuickTaskCheckboxes();
}

function bindQuickTaskCheckboxes() {
    document.querySelectorAll('.task-checkbox-custom').forEach(btn => {
        btn.onclick = async (e) => {
            e.stopPropagation();
            const taskId = btn.dataset.taskId;
            if (!taskId) return;
            try {
                await api.patch(`/api/tasks/${taskId}/status`, { status: 'completed' });
                btn.classList.add('completed');
                btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                const row = btn.closest('.quick-task-item');
                if (row) {
                    row.style.opacity = '0.5';
                    row.style.textDecoration = 'line-through';
                }
                showToast("✓ Task completed & logged to Study Analytics as focus session!", "success");
                setTimeout(async () => {
                    await loadLiveAppState();
                    if (typeof loadAnalyticsData === 'function') {
                        await loadAnalyticsData();
                    }
                }, 300);
            } catch (err) {
                console.error("Failed to complete task:", err);
            }
        };
    });
}

window.moveTaskStatus = async function (taskId, newStatus) {
    try {
        await api.patch(`/api/tasks/${taskId}/status`, { status: newStatus });
        if (newStatus === 'completed') {
            showToast("✓ Task completed & logged to Study Analytics as focus session!", "success");
        } else {
            showToast(`Task moved to ${newStatus.replace('_', ' ')}!`, "success");
        }
        await loadLiveAppState();
        if (typeof loadAnalyticsData === 'function') {
            await loadAnalyticsData();
        }
    } catch (err) {
        console.error("Failed to update status:", err);
    }
};

window.deleteTask = async function (taskId) {
    if (!confirm("Are you sure you want to delete this task?")) return;
    try {
        await api.delete(`/api/tasks/${taskId}`);
        showToast("Task deleted!", "success");
        await loadLiveAppState();
    } catch (err) {
        console.error("Failed to delete task:", err);
    }
};

/* ================= LIVE DATA SYNCHRONIZATION (HYDRATION) ================= */
async function loadLiveAppState() {
    try {
        const [taskRes, subjRes, statsRes] = await Promise.all([
            api.get('/api/tasks?grouped=true').catch(() => null),
            api.get('/api/subjects').catch(() => null),
            api.get('/api/analytics/overview').catch(() => null)
        ]);

        if (subjRes && subjRes.subjects) {
            populateSubjectSelects(subjRes.subjects);
            renderLiveCourses(subjRes.subjects);
        }

        if (taskRes && taskRes.tasks) {
            renderLiveKanban(taskRes.tasks);
            renderLiveDashboardTasks(taskRes.tasks);
        }

        if (statsRes && statsRes.stats) {
            renderLiveStats(statsRes.stats);
        }

        if (typeof loadAnalyticsData === 'function') {
            loadAnalyticsData();
        }
    } catch (err) {
        console.warn("Live app state sync:", err);
    }
}

function renderLiveDashboardTasks(grouped) {
    const list = document.querySelector('.quick-task-list');
    if (!list) return;

    const pending = [...(grouped.todo || []), ...(grouped.in_progress || [])];
    if (pending.length === 0) {
        list.innerHTML = `<div style="text-align: center; padding: 24px; color: var(--text-muted); font-size: 0.88rem;">✨ No pending tasks! All caught up.</div>`;
        return;
    }

    list.innerHTML = pending.slice(0, 6).map(t => {
        const color = t.subject_color || '#6366f1';
        const subjName = t.subject_name || 'General';
        const dueText = t.relative_due_date ? `Due ${t.relative_due_date}` : (t.due_date ? `Due ${t.due_date}` : 'No due date');
        const priorityClass = `priority-${t.priority || 'medium'}`;
        const priorityLabel = (t.priority || 'medium').toUpperCase();

        return `
            <div class="quick-task-item" data-task-id="${t.id}">
                <div class="quick-task-main">
                    <button class="task-checkbox-custom" data-task-id="${t.id}" title="Mark completed"></button>
                    <div>
                        <div class="quick-task-title">${escapeHtml(t.title)}</div>
                        <div class="quick-task-due"><span style="color: ${color}; font-weight: 600;">${escapeHtml(subjName)}</span> &bull; ${escapeHtml(dueText)}</div>
                    </div>
                </div>
                <span class="badge ${priorityClass}">${priorityLabel}</span>
            </div>
        `;
    }).join('');

    bindQuickTaskCheckboxes();
}

function renderLiveKanban(grouped) {
    const columns = document.querySelectorAll('.kanban-column');
    if (!columns || columns.length < 3) return;

    const colsData = [
        { status: 'todo', tasks: grouped.todo || [] },
        { status: 'in_progress', tasks: grouped.in_progress || [] },
        { status: 'completed', tasks: grouped.completed || [] }
    ];

    columns.forEach((col, idx) => {
        const container = col.querySelector('.kanban-cards-container');
        if (!container) return;

        const { status, tasks } = colsData[idx];
        const countSpan = col.querySelector('.kanban-count');
        if (countSpan) countSpan.textContent = tasks.length;

        if (tasks.length === 0) {
            container.innerHTML = `<div class="kanban-empty-state" style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 0.82rem;">No tasks here</div>`;
            return;
        }

        container.innerHTML = tasks.map(t => {
            const color = t.subject_color || '#6366f1';
            const subjName = t.subject_name || 'General';
            const dueText = t.relative_due_date ? `Due ${t.relative_due_date}` : (t.due_date ? `Due ${t.due_date}` : '');
            const isDone = status === 'completed';
            const borderStyle = isDone ? 'border-left: 3px solid #10b981; opacity: 0.85;' : (status === 'in_progress' ? 'border-left: 3px solid #f59e0b;' : '');
            const titleStyle = isDone ? 'text-decoration: line-through;' : '';

            return `
                <div class="task-card" style="${borderStyle}" data-task-id="${t.id}">
                    <div class="task-header">
                        <span class="task-subject-tag" style="--subj-tag-color: ${color}; background-color: ${color}; color: #ffffff;" title="Course: ${escapeHtml(subjName)}">${escapeHtml(subjName)}</span>
                        <div style="display: flex; gap: 4px; align-items: center;">
                            <span class="badge priority-${t.priority || 'medium'}">${(t.priority || 'medium').toUpperCase()}</span>
                            <button class="btn-icon btn-sm" onclick="deleteTask(${t.id})" title="Delete Task" style="background: none; border: none; cursor: pointer; color: var(--text-muted); padding: 2px;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                            </button>
                        </div>
                    </div>
                    <h4 class="task-title" style="${titleStyle}">${escapeHtml(t.title)}</h4>
                    ${t.description ? `<p style="font-size: 0.8rem; color: var(--text-muted); margin: 4px 0 8px;">${escapeHtml(t.description)}</p>` : ''}
                    <div class="task-footer">
                        <div class="task-due"><span>${escapeHtml(dueText)}</span></div>
                        <div class="task-actions" style="display: flex; gap: 4px;">
                            ${status !== 'todo' ? `<button class="btn btn-secondary btn-sm" onclick="moveTaskStatus(${t.id}, 'todo')" title="Move to To Do" style="padding: 2px 6px; font-size: 0.72rem;">⬅ To Do</button>` : ''}
                            ${status !== 'in_progress' ? `<button class="btn btn-secondary btn-sm" onclick="moveTaskStatus(${t.id}, 'in_progress')" title="Move to In Progress" style="padding: 2px 6px; font-size: 0.72rem;">⚡ Progress</button>` : ''}
                            ${status !== 'completed' ? `<button class="btn btn-primary btn-sm" onclick="moveTaskStatus(${t.id}, 'completed')" title="Mark Completed" style="padding: 2px 6px; font-size: 0.72rem;">✓ Done</button>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    });
}

function populateSubjectSelects(subjects) {
    const allSubjectSelects = document.querySelectorAll('#taskSubject, #timerSubjectSelect, #ttSubject, #examSubject');
    allSubjectSelects.forEach(sel => {
        const currentVal = sel.value;
        const defaultText = (sel.id === 'taskSubject')
            ? '-- General / No Subject --'
            : '-- Select Course / Subject --';

        sel.innerHTML = `<option value="">${defaultText}</option>`;
        const seenIds = new Set();
        (subjects || []).forEach(s => {
            if (!s || !s.id || seenIds.has(s.id)) return;
            seenIds.add(s.id);
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.code ? `${s.name} (${s.code})` : s.name;
            sel.appendChild(opt);
        });

        const createOpt = document.createElement('option');
        createOpt.value = '__create_new__';
        createOpt.style.color = '#818cf8';
        createOpt.style.fontWeight = '600';
        createOpt.textContent = '➕ + Add Custom Course / Subject...';
        sel.appendChild(createOpt);

        if (currentVal && currentVal !== '__create_new__' && seenIds.has(parseInt(currentVal))) {
            sel.value = currentVal;
        }
    });
}

function renderLiveCourses(subjects) {
    const grid = document.getElementById('coursesGridContainer') || document.querySelector('.subjects-grid');
    if (!grid) return;

    if (subjects.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">No courses added yet. Click "+ Add New Course" above!</div>`;
        return;
    }

    grid.innerHTML = subjects.map(s => {
        const color = s.color || '#6366f1';
        const codeBadge = s.code ? `<span class="subject-badge-pill">${escapeHtml(s.code)}</span>` : '';
        const totalHrs = s.total_study_hours || 0;
        const targetHrs = s.target_hours_per_week || 5.0;
        const pct = s.progress_pct || 0;
        const completedTopics = s.completed_topics || 0;
        const totalTopics = s.total_topics || 0;

        return `
            <div class="subject-card" style="--subj-color: ${color}; border-top: 4px solid ${color};">
                <div class="subject-header-row">
                    <div>
                        ${codeBadge}
                        <h3 class="subject-title">${escapeHtml(s.name)}</h3>
                    </div>
                    <button class="btn-icon btn-outline btn-sm" onclick="deleteSubject(${s.id})" title="Delete Course" style="background: none; border: none; cursor: pointer; color: var(--text-muted);">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
                <div class="subject-meta-stats">
                    <div class="subject-stat-item"><span class="subject-stat-label">Total Studied</span><span class="subject-stat-val">${totalHrs}h</span></div>
                    <div class="subject-stat-item"><span class="subject-stat-label">Weekly Target</span><span class="subject-stat-val">${targetHrs}h / wk</span></div>
                </div>
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600;">
                        <span style="color: var(--text-secondary);">Syllabus Progress</span>
                        <span style="color: ${color};">${pct}% (${completedTopics}/${totalTopics})</span>
                    </div>
                    <div class="progress-container"><div class="progress-fill" style="width: ${pct}%; background: ${color};"></div></div>
                </div>
            </div>
        `;
    }).join('');
}

function renderLiveStats(stats) {
    const elTotalHours = document.getElementById('statTotalHours');
    const elCompletionRate = document.getElementById('statCompletionRate');
    const elStreak = document.getElementById('statStreak');
    const elCoursesCount = document.getElementById('statCoursesCount');

    if (elTotalHours) elTotalHours.textContent = `${stats.total_hours || 0}h`;
    if (elCompletionRate) elCompletionRate.textContent = `${stats.completion_rate || 0}%`;
    if (elStreak) elStreak.textContent = `${stats.streak_days || 0} Days`;
    if (elCoursesCount) elCoursesCount.textContent = stats.total_courses || 0;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function bindQuickSubjectCreator({ selectId, quickBtnId, panelId, inputId, codeInputId, colorInputId, saveBtnId, cancelBtnId }) {
    const selectElem = document.getElementById(selectId);
    const quickBtn = document.getElementById(quickBtnId);
    const panel = document.getElementById(panelId);
    const input = document.getElementById(inputId);
    const codeInput = codeInputId ? document.getElementById(codeInputId) : null;
    const colorInput = colorInputId ? document.getElementById(colorInputId) : null;
    const saveBtn = document.getElementById(saveBtnId);
    const cancelBtn = document.getElementById(cancelBtnId);

    if (!selectElem || !panel) return;

    const showPanel = () => {
        panel.style.display = 'block';
        if (input) {
            input.value = '';
            input.focus();
        }
        if (codeInput) codeInput.value = '';
        if (colorInput) colorInput.value = '#6366f1';
    };

    const hidePanel = () => {
        panel.style.display = 'none';
        if (selectElem.value === '__create_new__') {
            selectElem.value = '';
        }
    };

    if (quickBtn) {
        quickBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showPanel();
        });
    }

    selectElem.addEventListener('change', () => {
        if (selectElem.value === '__create_new__') {
            showPanel();
        } else {
            panel.style.display = 'none';
        }
    });

    if (cancelBtn) {
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            hidePanel();
        });
    }

    const saveSubject = async () => {
        const name = input ? input.value.trim() : '';
        if (!name) {
            showToast("Please enter a course / subject name", "error");
            return;
        }

        const code = codeInput ? codeInput.value.trim() : '';
        const color = colorInput ? colorInput.value : '#6366f1';

        try {
            const res = await api.post('/api/subjects', { name, code, color });
            if (res && res.subject_id) {
                // Add new option to all course select dropdowns
                const allSubjectSelects = document.querySelectorAll('#taskSubject, #timerSubjectSelect, #ttSubject, #examSubject');
                allSubjectSelects.forEach(sel => {
                    const opt = document.createElement('option');
                    opt.value = res.subject_id;
                    opt.textContent = code ? `${name} (${code})` : name;

                    const createNewOpt = sel.querySelector('option[value="__create_new__"]');
                    if (createNewOpt) {
                        sel.insertBefore(opt, createNewOpt);
                    } else {
                        sel.appendChild(opt);
                    }
                });

                selectElem.value = res.subject_id;
                hidePanel();
                showToast(`✨ Course "${name}" created and selected!`, 'success');
                if (typeof loadLiveAppState === 'function') {
                    loadLiveAppState();
                }
            }
        } catch (err) {
            console.error("Quick subject creation failed:", err);
            showToast("Failed to create course", "error");
        }
    };

    if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            saveSubject();
        });
    }

    const handleKey = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveSubject();
        } else if (e.key === 'Escape') {
            hidePanel();
        }
    };

    if (input) input.addEventListener('keydown', handleKey);
    if (codeInput) codeInput.addEventListener('keydown', handleKey);
}

/* ================= COURSES & SYLLABUS ================= */
function initSubjectHandlers() {
    const subjForm = document.getElementById('newSubjectForm');
    if (subjForm) {
        subjForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(subjForm);
            const payload = {
                name: formData.get('name'),
                code: formData.get('code'),
                color: formData.get('color') || '#6366f1',
                target_hours_per_week: parseFloat(formData.get('target_hours_per_week') || 5.0)
            };

            try {
                await api.post('/api/subjects', payload);
                showToast("Course added successfully!", "success");
                closeModal('newSubjectModal');
                subjForm.reset();
                await loadLiveAppState();
            } catch (err) {
                console.error("Subject creation failed:", err);
            }
        });
    }

    // Toggle Syllabus Topic Checkbox
    document.querySelectorAll('.topic-toggle-checkbox').forEach(chk => {
        chk.addEventListener('change', async () => {
            const topicId = chk.dataset.topicId;
            try {
                const res = await api.put(`/api/subjects/topics/${topicId}/toggle`);
                const topicRow = chk.closest('.topic-item');
                if (topicRow) {
                    topicRow.classList.toggle('completed', res.is_completed === 1);
                }
                showToast(res.is_completed === 1 ? "Module completed!" : "Module marked pending", "success");
            } catch (err) {
                console.error("Topic toggle failed:", err);
            }
        });
    });

    // Add Topic to Syllabus Form
    document.querySelectorAll('.add-topic-form').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const subjectId = form.dataset.subjectId;
            const input = form.querySelector('input[name="title"]');
            const title = input.value.trim();
            if (!title) return;

            try {
                await api.post(`/api/subjects/${subjectId}/topics`, { title });
                showToast("Module added to syllabus!", "success");
                await loadLiveAppState();
            } catch (err) {
                console.error("Topic add failed:", err);
            }
        });
    });
}

window.deleteSubject = async function (subjectId) {
    if (!confirm("Are you sure you want to delete this course and its syllabus?")) return;
    try {
        await api.delete(`/api/subjects/${subjectId}`);
        showToast("Course removed!", "success");
        await loadLiveAppState();
    } catch (err) {
        console.error("Failed to delete subject:", err);
    }
};

/* ================= TIMETABLE & EXAMS ================= */
function initTimetableHandlers() {
    const form = document.getElementById('timetableForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const slotId = formData.get('slot_id');
            const subjVal = formData.get('subject_id');

            if (!subjVal || subjVal === '__create_new__') {
                showToast("Please choose or add a course / subject first", "error");
                return;
            }

            const payload = {
                subject_id: parseInt(subjVal),
                day_of_week: parseInt(formData.get('day_of_week')),
                start_time: formData.get('start_time'),
                end_time: formData.get('end_time'),
                location: formData.get('location') || ''
            };

            try {
                if (slotId) {
                    await api.put(`/api/timetable/${slotId}`, payload);
                    showToast("Class schedule updated!", "success");
                } else {
                    await api.post('/api/timetable', payload);
                    showToast("Class added to schedule!", "success");
                }
                closeModal('timetableModal');
                window.location.reload();
            } catch (err) {
                console.error("Timetable save failed:", err);
                showToast("Failed to save class: " + (err.error || err.message || "Unknown error"), "error");
            }
        });
    }

    bindQuickSubjectCreator({
        selectId: 'ttSubject',
        quickBtnId: 'quickAddTtSubjectBtn',
        panelId: 'quickTtSubjectPanel',
        inputId: 'quickTtSubjectName',
        codeInputId: 'quickTtSubjectCode',
        colorInputId: 'quickTtSubjectColor',
        saveBtnId: 'quickTtSubjectSaveBtn',
        cancelBtnId: 'quickTtSubjectCancelBtn'
    });
}

function initExamHandlers() {
    const form = document.getElementById('examForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const examId = formData.get('exam_id');
            const subjVal = formData.get('subject_id');

            if (!subjVal || subjVal === '__create_new__') {
                showToast("Please choose or add a course / subject first", "error");
                return;
            }

            const payload = {
                subject_id: parseInt(subjVal),
                title: formData.get('title'),
                exam_date: formData.get('exam_date'),
                room_or_link: formData.get('room_or_link') || '',
                notes: formData.get('notes') || '',
                weight_percentage: parseFloat(formData.get('weight_percentage') || 0)
            };

            try {
                if (examId) {
                    await api.put(`/api/exams/${examId}`, payload);
                    showToast("Exam updated successfully!", "success");
                } else {
                    await api.post('/api/exams', payload);
                    showToast("Exam scheduled successfully!", "success");
                }
                closeModal('examModal');
                window.location.reload();
            } catch (err) {
                console.error("Exam save failed:", err);
                showToast("Failed to save exam: " + (err.error || err.message || "Unknown error"), "error");
            }
        });
    }

    bindQuickSubjectCreator({
        selectId: 'examSubject',
        quickBtnId: 'quickAddExamSubjectBtn',
        panelId: 'quickExamSubjectPanel',
        inputId: 'quickExamSubjectName',
        codeInputId: 'quickExamSubjectCode',
        colorInputId: 'quickExamSubjectColor',
        saveBtnId: 'quickExamSubjectSaveBtn',
        cancelBtnId: 'quickExamSubjectCancelBtn'
    });
}

window.openAddTimetableModal = function () {
    const form = document.getElementById('timetableForm');
    if (form) {
        form.reset();
        const slotIdInput = document.getElementById('ttSlotId');
        if (slotIdInput) slotIdInput.value = '';
    }
    const title = document.getElementById('timetableModalTitle');
    if (title) title.textContent = 'Add Class to Timetable';
    const submitBtn = document.getElementById('ttSubmitBtn');
    if (submitBtn) submitBtn.textContent = 'Add to Schedule';
    const panel = document.getElementById('quickTtSubjectPanel');
    if (panel) panel.style.display = 'none';
    openModal('timetableModal');
};

window.editTimetableSlot = function (id, subjectId, dayOfWeek, startTime, endTime, location) {
    const slotIdInput = document.getElementById('ttSlotId');
    const subjSelect = document.getElementById('ttSubject');
    const daySelect = document.getElementById('ttDay');
    const startInput = document.getElementById('ttStart');
    const endInput = document.getElementById('ttEnd');
    const locInput = document.getElementById('ttLocation');
    const title = document.getElementById('timetableModalTitle');
    const submitBtn = document.getElementById('ttSubmitBtn');
    const panel = document.getElementById('quickTtSubjectPanel');
    if (panel) panel.style.display = 'none';

    if (slotIdInput) slotIdInput.value = id;
    if (subjSelect) subjSelect.value = subjectId;
    if (daySelect) daySelect.value = dayOfWeek;
    if (startInput) startInput.value = startTime;
    if (endInput) endInput.value = endTime;
    if (locInput) locInput.value = location || '';
    if (title) title.textContent = '✏️ Edit Class Schedule';
    if (submitBtn) submitBtn.textContent = 'Save Changes';

    openModal('timetableModal');
};

window.openAddExamModal = function () {
    const form = document.getElementById('examForm');
    if (form) {
        form.reset();
        const examIdInput = document.getElementById('examId');
        if (examIdInput) examIdInput.value = '';
    }
    const title = document.getElementById('examModalTitle');
    if (title) title.textContent = 'Schedule New Exam';
    const submitBtn = document.getElementById('examSubmitBtn');
    if (submitBtn) submitBtn.textContent = 'Schedule Exam';
    const panel = document.getElementById('quickExamSubjectPanel');
    if (panel) panel.style.display = 'none';
    openModal('examModal');
};

window.editExam = function (id, subjectId, titleText, examDate, roomOrLink, notes, weight) {
    const examIdInput = document.getElementById('examId');
    const subjSelect = document.getElementById('examSubject');
    const titleInput = document.getElementById('examTitle');
    const dateInput = document.getElementById('examDate');
    const roomInput = document.getElementById('examRoom');
    const notesInput = document.getElementById('examNotes');
    const weightInput = document.getElementById('examWeight');
    const modalTitle = document.getElementById('examModalTitle');
    const submitBtn = document.getElementById('examSubmitBtn');
    const panel = document.getElementById('quickExamSubjectPanel');
    if (panel) panel.style.display = 'none';

    if (examIdInput) examIdInput.value = id;
    if (subjSelect) subjSelect.value = subjectId;
    if (titleInput) titleInput.value = titleText;
    if (dateInput && examDate) {
        try {
            const d = new Date(examDate);
            const pad = n => String(n).padStart(2, '0');
            dateInput.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        } catch {
            dateInput.value = examDate.substring(0, 16);
        }
    }
    if (roomInput) roomInput.value = roomOrLink || '';
    if (notesInput) notesInput.value = notes || '';
    if (weightInput) weightInput.value = weight || 0;
    if (modalTitle) modalTitle.textContent = '✏️ Edit Exam';
    if (submitBtn) submitBtn.textContent = 'Save Changes';

    openModal('examModal');
};

window.deleteTimetableSlot = async function (slotId) {
    if (!confirm("Remove this class slot?")) return;
    try {
        await api.delete(`/api/timetable/${slotId}`);
        showToast("Class slot removed!", "success");
        window.location.reload();
    } catch (err) {
        console.error("Failed to delete slot:", err);
    }
};

window.deleteExam = async function (examId) {
    if (!confirm("Remove this exam?")) return;
    try {
        await api.delete(`/api/exams/${examId}`);
        showToast("Exam removed!", "success");
        window.location.reload();
    } catch (err) {
        console.error("Failed to delete exam:", err);
    }
};

window.setTimetableDays = function (numDays) {
    const grid = document.querySelector('.timetable-grid');
    const btn5 = document.getElementById('btnDays5');
    const btn7 = document.getElementById('btnDays7');

    if (!grid) return;

    if (numDays === 7) {
        grid.classList.add('days-7');
        if (btn7) {
            btn7.classList.add('active');
            btn7.style.background = 'var(--primary)';
            btn7.style.color = 'white';
        }
        if (btn5) {
            btn5.classList.remove('active');
            btn5.style.background = 'transparent';
            btn5.style.color = 'var(--text-secondary)';
        }
        localStorage.setItem('studyflow_timetable_days', '7');
    } else {
        grid.classList.remove('days-7');
        if (btn5) {
            btn5.classList.add('active');
            btn5.style.background = 'var(--primary)';
            btn5.style.color = 'white';
        }
        if (btn7) {
            btn7.classList.remove('active');
            btn7.style.background = 'transparent';
            btn7.style.color = 'var(--text-secondary)';
        }
        localStorage.setItem('studyflow_timetable_days', '5');
    }
};

window.initTimetableDaysToggle = function () {
    const saved = localStorage.getItem('studyflow_timetable_days');
    const hasWeekendSlots = document.querySelector('.weekend-column .class-slot-card') !== null;
    if (saved === '7' || (saved === null && hasWeekendSlots)) {
        setTimetableDays(7);
    } else {
        setTimetableDays(5);
    }
};

/* ================= ANALYTICS & CHART.JS ================= */
function initAnalyticsCharts() {
    loadAnalyticsData();
}

async function loadAnalyticsData() {
    try {
        const [trendRes, distRes, sessionsRes] = await Promise.all([
            api.get('/api/analytics/weekly-trend').catch(() => null),
            api.get('/api/analytics/subject-distribution').catch(() => null),
            api.get('/api/timer/history?limit=30').catch(() => null)
        ]);

        if (trendRes && trendRes.success && trendRes.data) {
            renderWeeklyChart(trendRes.data);
        }

        if (distRes && distRes.success && distRes.data) {
            renderDistributionChart(distRes.data);
        }

        if (sessionsRes && sessionsRes.success && sessionsRes.sessions) {
            renderLiveFocusSessions(sessionsRes.sessions);
        }
    } catch (err) {
        console.error("Analytics chart fetch error:", err);
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

    if (weeklyChartInstance) {
        weeklyChartInstance.destroy();
    }

    weeklyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Study Hours',
                data: data.hours,
                backgroundColor: 'rgba(99, 102, 241, 0.7)',
                borderColor: '#6366f1',
                borderWidth: 2,
                borderRadius: 8,
                hoverBackgroundColor: 'rgba(99, 102, 241, 0.95)'
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
                    padding: 10,
                    callbacks: {
                        label: (c) => `${c.parsed.y} Hours studied`
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

    if (subjectChartInstance) {
        subjectChartInstance.destroy();
    }

    if (!data.labels || data.labels.length === 0) {
        ctx.parentElement.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:0.85rem;">No study sessions logged yet</div>`;
        return;
    }

    subjectChartInstance = new Chart(ctx, {
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
                    labels: { color: '#94a3b8', boxWidth: 12, padding: 14 }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f8fafc',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: (c) => `${c.label}: ${c.parsed} hrs`
                    }
                }
            }
        }
    });
}
