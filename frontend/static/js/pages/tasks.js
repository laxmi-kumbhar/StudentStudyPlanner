/**
 * Tasks & Kanban Board Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initTaskForm();
    initFilterSelects();
});

function initTaskForm() {
    const form = document.getElementById('taskForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const subjVal = formData.get('subject_id');
        const data = {
            title: formData.get('title'),
            description: formData.get('description'),
            subject_id: (subjVal && subjVal !== '__create_new__') ? parseInt(subjVal) : null,
            priority: formData.get('priority'),
            due_date: formData.get('due_date'),
            estimated_minutes: parseInt(formData.get('estimated_minutes') || 30)
        };

        try {
            await api.post('/api/tasks', data);
            showToast("Task created successfully!", "success");
            closeModal('taskModal');
            window.location.reload();
        } catch (err) {
            console.error("Failed to create task:", err);
        }
    });

    initQuickSubjectCreator();
}

function initQuickSubjectCreator() {
    const taskSubject = document.getElementById('taskSubject');
    const quickBtn = document.getElementById('quickAddSubjectBtn');
    const panel = document.getElementById('quickSubjectPanel');
    const input = document.getElementById('quickSubjectName');
    const saveBtn = document.getElementById('quickSubjectSaveBtn');
    const cancelBtn = document.getElementById('quickSubjectCancelBtn');

    if (!taskSubject || !panel) return;

    const showPanel = () => {
        panel.style.display = 'block';
        if (input) {
            input.value = '';
            input.focus();
        }
    };

    const hidePanel = () => {
        panel.style.display = 'none';
        if (taskSubject.value === '__create_new__') {
            taskSubject.value = '';
        }
    };

    if (quickBtn) {
        quickBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showPanel();
        });
    }

    taskSubject.addEventListener('change', () => {
        if (taskSubject.value === '__create_new__') {
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
            showToast("Please enter a subject / course name", "error");
            return;
        }

        try {
            const res = await api.post('/api/subjects', { name, color: '#6366f1' });
            if (res && res.subject_id) {
                const opt = document.createElement('option');
                opt.value = res.subject_id;
                opt.textContent = name;

                const createNewOpt = taskSubject.querySelector('option[value="__create_new__"]');
                if (createNewOpt) {
                    taskSubject.insertBefore(opt, createNewOpt);
                } else {
                    taskSubject.appendChild(opt);
                }

                taskSubject.value = res.subject_id;
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

function initFilterSelects() {
    const filterSubject = document.getElementById('filterSubject');
    if (filterSubject) {
        filterSubject.addEventListener('change', () => {
            const val = filterSubject.value;
            const url = new URL(window.location);
            if (val) {
                url.searchParams.set('subject_id', val);
            } else {
                url.searchParams.delete('subject_id');
            }
            window.location.href = url.toString();
        });
    }
}

window.moveTaskStatus = async function(taskId, newStatus) {
    try {
        await api.patch(`/api/tasks/${taskId}/status`, { status: newStatus });
        if (newStatus === 'completed') {
            showToast("✓ Task completed & logged to Study Analytics as focus session!", "success");
        } else {
            showToast(`Moved to ${newStatus.replace('_', ' ')}!`, "success");
        }
        window.location.reload();
    } catch (err) {
        console.error("Failed to move task:", err);
    }
};

window.deleteTask = async function(taskId) {
    if (!confirm("Are you sure you want to delete this task?")) return;
    try {
        await api.delete(`/api/tasks/${taskId}`);
        showToast("Task removed!", "success");
        window.location.reload();
    } catch (err) {
        console.error("Failed to delete task:", err);
    }
};
