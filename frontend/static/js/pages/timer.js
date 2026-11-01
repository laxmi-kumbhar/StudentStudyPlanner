/**
 * Focus Room & Pomodoro Page Controller
 */

let timer;

document.addEventListener('DOMContentLoaded', () => {
    initTimerEngine();
    initModeButtons();
    initControls();
});

function initTimerEngine() {
    const timeDisplay = document.getElementById('timerCountdown');
    const circleProgress = document.getElementById('timerProgressRing');
    const statusText = document.getElementById('timerStatusText');
    const circumference = 2 * Math.PI * 130; // 816.81

    timer = new PomodoroTimer({
        onTick: (formattedTime, progressPct) => {
            if (timeDisplay) timeDisplay.textContent = formattedTime;
            if (circleProgress) {
                const offset = circumference - (progressPct / 100) * circumference;
                circleProgress.style.strokeDashoffset = offset;
            }
            document.title = `(${formattedTime}) Focus Room - Student Planner`;
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
            showToast(`🎉 ${mode.replace('_', ' ')} completed!`, 'success');

            // Auto log study session if it's a focus session
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
                        console.error("Failed to log study session:", err);
                    }
                }
            }
        }
    });
}

function initModeButtons() {
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
            timer.setMode(mode);
        });
    });

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
                timer.setMode('custom', mins);
                if (typeof closeModal === 'function') closeModal('customTimerModal');
                if (typeof showToast === 'function') showToast(`⏱️ Custom timer set to ${mins} mins`, 'success');
            }
        });
    }
}

function initControls() {
    const toggleBtn = document.getElementById('timerToggleBtn');
    const resetBtn = document.getElementById('timerResetBtn');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => timer.toggle());
    }
    if (resetBtn) {
        resetBtn.addEventListener('click', () => timer.reset());
    }

    bindQuickSubjectCreator({
        selectId: 'timerSubjectSelect',
        quickBtnId: 'quickAddTimerSubjectBtn',
        panelId: 'quickTimerSubjectPanel',
        inputId: 'quickTimerSubjectName',
        saveBtnId: 'quickTimerSubjectSaveBtn',
        cancelBtnId: 'quickTimerSubjectCancelBtn'
    });
}

function bindQuickSubjectCreator({ selectId, quickBtnId, panelId, inputId, saveBtnId, cancelBtnId }) {
    const selectElem = document.getElementById(selectId);
    const quickBtn = document.getElementById(quickBtnId);
    const panel = document.getElementById(panelId);
    const input = document.getElementById(inputId);
    const saveBtn = document.getElementById(saveBtnId);
    const cancelBtn = document.getElementById(cancelBtnId);

    if (!selectElem || !panel) return;

    const showPanel = () => {
        panel.style.display = 'block';
        if (input) {
            input.value = '';
            input.focus();
        }
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

        try {
            const res = await api.post('/api/subjects', { name, color: '#6366f1' });
            if (res && res.subject_id) {
                const opt = document.createElement('option');
                opt.value = res.subject_id;
                opt.textContent = name;

                const createNewOpt = selectElem.querySelector('option[value="__create_new__"]');
                if (createNewOpt) {
                    selectElem.insertBefore(opt, createNewOpt);
                } else {
                    selectElem.appendChild(opt);
                }

                selectElem.value = res.subject_id;
                hidePanel();
                showToast(`✨ Subject "${name}" created and selected!`, 'success');
            }
        } catch (err) {
            console.error("Quick subject creation failed:", err);
        }
    };

    if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            saveSubject();
        });
    }

    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveSubject();
            } else if (e.key === 'Escape') {
                hidePanel();
            }
        });
    }
}
