/**
 * Subjects & Syllabus Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initSubjectForm();
    initTopicToggles();
    initTopicAddForms();
});

// Subject Creation Form
function initSubjectForm() {
    const form = document.getElementById('newSubjectForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const data = {
            name: formData.get('name'),
            code: formData.get('code'),
            color: formData.get('color'),
            target_hours_per_week: parseFloat(formData.get('target_hours_per_week') || 5.0)
        };

        try {
            await api.post('/api/subjects', data);
            showToast("Subject added successfully!", "success");
            closeModal('newSubjectModal');
            window.location.reload();
        } catch (err) {
            console.error("Failed to add subject:", err);
        }
    });
}

// Topic Checkbox Toggles
function initTopicToggles() {
    document.querySelectorAll('.topic-toggle-checkbox').forEach(chk => {
        chk.addEventListener('change', async (e) => {
            const topicId = chk.dataset.topicId;
            try {
                const res = await api.put(`/api/subjects/topics/${topicId}/toggle`);
                const topicRow = chk.closest('.topic-item');
                if (topicRow) {
                    topicRow.classList.toggle('completed', res.is_completed === 1);
                }
                showToast(res.is_completed === 1 ? "Topic completed!" : "Topic marked pending", "success");
            } catch (err) {
                console.error("Failed to toggle topic:", err);
            }
        });
    });
}

// Quick Topic Add Form inside subject cards
function initTopicAddForms() {
    document.querySelectorAll('.add-topic-form').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const subjectId = form.dataset.subjectId;
            const input = form.querySelector('input[name="title"]');
            const title = input.value.trim();
            if (!title) return;

            try {
                await api.post(`/api/subjects/${subjectId}/topics`, { title });
                showToast("Topic added to syllabus!", "success");
                window.location.reload();
            } catch (err) {
                console.error("Failed to add topic:", err);
            }
        });
    });
}

window.deleteSubject = async function(subjectId) {
    if (!confirm("Are you sure you want to delete this subject and its syllabus?")) return;
    try {
        await api.delete(`/api/subjects/${subjectId}`);
        showToast("Subject deleted!", "success");
        window.location.reload();
    } catch (err) {
        console.error("Failed to delete subject:", err);
    }
};
