// ---- Employee Profile page ----

let selectedFile = null;
let pendingFields = null;
let pendingOcrText = '';
let pendingDocType = '';

document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
    initUpload();
});

// ---- Upload handling ----

function initUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });
}

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, загрузите изображение (JPG, PNG)');
        return;
    }
    selectedFile = file;
    const url = URL.createObjectURL(file);
    document.getElementById('previewImage').src = url;
    document.getElementById('uploadArea').style.display = 'none';
    document.getElementById('previewArea').style.display = 'block';
    document.getElementById('processBtn').disabled = false;
    document.getElementById('ocrPreview').style.display = 'none';
}

function resetUpload() {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadArea').style.display = 'flex';
    document.getElementById('previewArea').style.display = 'none';
    document.getElementById('processBtn').disabled = true;
    document.getElementById('ocrPreview').style.display = 'none';
}

// ---- OCR + Save flow ----

async function processAndSave() {
    if (!selectedFile) return;

    const docType = document.getElementById('docType').value;
    const processBtn = document.getElementById('processBtn');
    const loading = document.getElementById('loadingSection');

    processBtn.disabled = true;
    loading.style.display = 'flex';

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('doc_type', docType);

    try {
        const resp = await fetch('/process-document', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        // Show extracted fields for review
        pendingFields = data.fields;
        pendingOcrText = data.ocr_text;
        pendingDocType = data.doc_type;
        showOcrPreview(data);
    } catch (err) {
        alert('Ошибка: ' + err.message);
    } finally {
        processBtn.disabled = false;
        loading.style.display = 'none';
    }
}

function showOcrPreview(data) {
    const container = document.getElementById('fieldsContainer');
    container.innerHTML = '';

    const fields = data.fields;
    const labels = data.field_labels || {};

    for (const [key, value] of Object.entries(fields)) {
        if (key.startsWith('_')) continue;

        const row = document.createElement('div');
        row.className = 'field-row';

        const label = document.createElement('label');
        label.textContent = labels[key] || key;

        const input = document.createElement('input');
        input.type = 'text';
        input.id = `field-${key}`;
        input.value = value || '';
        input.className = 'field-input';

        row.appendChild(label);
        row.appendChild(input);
        container.appendChild(row);
    }

    if (fields._error) {
        const errDiv = document.createElement('div');
        errDiv.className = 'field-error';
        errDiv.textContent = fields._error;
        container.appendChild(errDiv);
    }

    document.getElementById('ocrPreview').style.display = 'block';
}

async function confirmSave() {
    // Collect edited fields
    const fields = {};
    const inputs = document.getElementById('fieldsContainer').querySelectorAll('.field-input');
    inputs.forEach(input => {
        const key = input.id.replace('field-', '');
        fields[key] = input.value;
    });

    try {
        await fetch(`/api/employees/${EMPLOYEE_ID}/documents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doc_type: pendingDocType,
                fields: fields,
                ocr_text: pendingOcrText,
            }),
        });

        resetUpload();
        document.getElementById('ocrPreview').style.display = 'none';
        loadDocuments();
        // Reload page to update employee info
        location.reload();
    } catch (err) {
        alert('Ошибка сохранения: ' + err.message);
    }
}

function cancelSave() {
    document.getElementById('ocrPreview').style.display = 'none';
    pendingFields = null;
}

// ---- Documents list ----

const DOC_TYPE_NAMES = {
    passport: 'Паспорт РФ',
    snils: 'СНИЛС',
    inn: 'ИНН',
    diploma: 'Диплом',
    auto: 'Документ',
};

async function loadDocuments() {
    try {
        const resp = await fetch(`/api/employees/${EMPLOYEE_ID}/documents`);
        const data = await resp.json();
        renderDocuments(data.documents);
    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

function renderDocuments(docs) {
    const list = document.getElementById('documentsList');

    if (docs.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>Нет документов. Загрузите скан документа выше.</p></div>';
        return;
    }

    list.innerHTML = docs.map(doc => {
        const typeName = DOC_TYPE_NAMES[doc.doc_type] || doc.doc_type;
        const date = doc.created_at ? new Date(doc.created_at).toLocaleDateString('ru-RU') : '';

        const fieldsHtml = Object.entries(doc.fields)
            .filter(([k]) => !k.startsWith('_'))
            .slice(0, 6)
            .map(([k, v]) => `
                <div class="doc-field">
                    <span class="doc-field-label">${k}:</span>
                    <span class="doc-field-value">${v || '—'}</span>
                </div>
            `).join('');

        const moreCount = Object.keys(doc.fields).filter(k => !k.startsWith('_')).length - 6;

        return `
            <div class="doc-item">
                <div class="doc-item-header">
                    <span class="doc-type-badge">${typeName}</span>
                    <span class="doc-date">${date}</span>
                </div>
                <div class="doc-fields">
                    ${fieldsHtml}
                </div>
                ${moreCount > 0 ? `<div style="font-size:12px;color:#666;margin-top:4px">и ещё ${moreCount} полей</div>` : ''}
                <div class="doc-item-actions">
                    <button class="btn-icon danger" onclick="removeDocument(${doc.id})" title="Удалить">&#128465; Удалить</button>
                </div>
            </div>
        `;
    }).join('');
}

async function removeDocument(docId) {
    if (!confirm('Удалить этот документ из дела?')) return;

    try {
        await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
        loadDocuments();
    } catch (err) {
        alert('Ошибка: ' + err.message);
    }
}

// ---- Edit employee info ----

function editInfo() {
    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

async function saveInfo(event) {
    event.preventDefault();

    const data = {
        surname: document.getElementById('editSurname').value,
        name: document.getElementById('editName').value,
        patronymic: document.getElementById('editPatronymic').value,
        birth_date: document.getElementById('editBirthDate').value,
        birth_place: document.getElementById('editBirthPlace').value,
        gender: document.getElementById('editGender').value,
        phone: document.getElementById('editPhone').value,
        email: document.getElementById('editEmail').value,
        department: document.getElementById('editDepartment').value,
        position: document.getElementById('editPosition').value,
        hire_date: document.getElementById('editHireDate').value,
        notes: document.getElementById('editNotes').value,
    };

    try {
        await fetch(`/api/employees/${EMPLOYEE_ID}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        location.reload();
    } catch (err) {
        alert('Ошибка: ' + err.message);
    }
}

// ---- Generate questionnaire ----

async function generateQuestionnaire() {
    try {
        const resp = await fetch(`/api/employees/${EMPLOYEE_ID}/questionnaire`, {
            method: 'POST',
        });

        if (!resp.ok) {
            alert('Ошибка генерации анкеты');
            return;
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `anketa_${EMPLOYEE_ID}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (err) {
        alert('Ошибка: ' + err.message);
    }
}

// Close modal on overlay click
document.getElementById('editModal')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeEditModal();
});
