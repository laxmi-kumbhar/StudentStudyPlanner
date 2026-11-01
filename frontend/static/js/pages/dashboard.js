/**
 * Dashboard Page Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initQuickTasks();
});

function initQuickTasks() {
    document.querySelectorAll('.task-checkbox-custom').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const taskId = btn.dataset.taskId;
            if (!taskId) return;

            try {
                await api.patch(`/api/tasks/${taskId}/status`, { status: 'completed' });
                btn.classList.add('completed');
                btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                
                const taskRow = btn.closest('.quick-task-item');
                if (taskRow) {
                    taskRow.style.opacity = '0.5';
                    taskRow.style.textDecoration = 'line-through';
                }
                
                showToast("Task marked as completed!", "success");
            } catch (err) {
                console.error("Failed to complete task:", err);
            }
        });
    });
}
