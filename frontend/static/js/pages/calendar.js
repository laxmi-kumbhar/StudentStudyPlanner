/**
 * Calendar & Timetable Page Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initCalendarTabs();
    initTimetableForm();
    initExamForm();
    initTimetableDaysToggle();
});

function initCalendarTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');

            btn.classList.add('active');
            const targetId = btn.dataset.target;
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.style.display = 'block';
            }
        });
    });
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
            if (typeof showToast === 'function') showToast("Please enter a course / subject name", "error");
            return;
        }

        const code = codeInput ? codeInput.value.trim() : '';
        const color = colorInput ? colorInput.value : '#6366f1';

        try {
            const res = await api.post('/api/subjects', { name, code, color });
            if (res && res.subject_id) {
                const allSubjectSelects = document.querySelectorAll('#ttSubject, #examSubject');
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
                if (typeof showToast === 'function') showToast(`✨ Course "${name}" created and selected!`, 'success');
            }
        } catch (err) {
            console.error("Quick subject creation failed:", err);
            if (typeof showToast === 'function') showToast("Failed to create course", "error");
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

function initTimetableForm() {
    const form = document.getElementById('timetableForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const slotId = formData.get('slot_id');
            const subjVal = formData.get('subject_id');

            if (!subjVal || subjVal === '__create_new__') {
                if (typeof showToast === 'function') showToast("Please choose or add a course / subject first", "error");
                return;
            }

            const data = {
                subject_id: parseInt(subjVal),
                day_of_week: parseInt(formData.get('day_of_week')),
                start_time: formData.get('start_time'),
                end_time: formData.get('end_time'),
                location: formData.get('location') || ''
            };

            try {
                if (slotId) {
                    await api.put(`/api/timetable/${slotId}`, data);
                    if (typeof showToast === 'function') showToast("Class schedule updated!", "success");
                } else {
                    await api.post('/api/timetable', data);
                    if (typeof showToast === 'function') showToast("Class added to timetable!", "success");
                }
                closeModal('timetableModal');
                window.location.reload();
            } catch (err) {
                console.error("Failed to save class:", err);
                if (typeof showToast === 'function') showToast("Failed to save class: " + (err.error || err.message || "Unknown error"), "error");
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

function initExamForm() {
    const form = document.getElementById('examForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const examId = formData.get('exam_id');
            const subjVal = formData.get('subject_id');

            if (!subjVal || subjVal === '__create_new__') {
                if (typeof showToast === 'function') showToast("Please choose or add a course / subject first", "error");
                return;
            }

            const data = {
                subject_id: parseInt(subjVal),
                title: formData.get('title'),
                exam_date: formData.get('exam_date'),
                room_or_link: formData.get('room_or_link') || '',
                notes: formData.get('notes') || '',
                weight_percentage: parseFloat(formData.get('weight_percentage') || 0)
            };

            try {
                if (examId) {
                    await api.put(`/api/exams/${examId}`, data);
                    if (typeof showToast === 'function') showToast("Exam updated successfully!", "success");
                } else {
                    await api.post('/api/exams', data);
                    if (typeof showToast === 'function') showToast("Exam scheduled!", "success");
                }
                closeModal('examModal');
                window.location.reload();
            } catch (err) {
                console.error("Failed to save exam:", err);
                if (typeof showToast === 'function') showToast("Failed to save exam: " + (err.error || err.message || "Unknown error"), "error");
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

window.deleteTimetableSlot = async function(slotId) {
    if (!confirm("Remove this class slot?")) return;
    try {
        await api.delete(`/api/timetable/${slotId}`);
        if (typeof showToast === 'function') showToast("Class removed!", "success");
        window.location.reload();
    } catch (err) {
        console.error("Failed to remove slot:", err);
    }
};

window.deleteExam = async function(examId) {
    if (!confirm("Remove this exam?")) return;
    try {
        await api.delete(`/api/exams/${examId}`);
        if (typeof showToast === 'function') showToast("Exam removed!", "success");
        window.location.reload();
    } catch (err) {
        console.error("Failed to remove exam:", err);
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
