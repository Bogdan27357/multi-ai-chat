const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewArea = document.getElementById('previewArea');
const previewImage = document.getElementById('previewImage');
const processBtn = document.getElementById('processBtn');
const resultsSection = document.getElementById('resultsSection');
const loadingSection = document.getElementById('loadingSection');
const fieldsContainer = document.getElementById('fieldsContainer');
const ocrText = document.getElementById('ocrText');

let selectedFile = null;
let extractedFields = {};

// Click to upload
uploadArea.addEventListener('click', () => fileInput.click());

// Drag & drop
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

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, загрузите изображение (JPG, PNG)');
        return;
    }
    selectedFile = file;
    const url = URL.createObjectURL(file);
    previewImage.src = url;
    uploadArea.style.display = 'none';
    previewArea.style.display = 'block';
    processBtn.disabled = false;
    resultsSection.style.display = 'none';
}

function resetUpload() {
    selectedFile = null;
    fileInput.value = '';
    uploadArea.style.display = 'flex';
    previewArea.style.display = 'none';
    processBtn.disabled = true;
    resultsSection.style.display = 'none';
}

async function processDocument() {
    if (!selectedFile) return;

    const docType = document.getElementById('docType').value;

    processBtn.disabled = true;
    loadingSection.style.display = 'flex';
    resultsSection.style.display = 'none';

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

        displayResults(data);
    } catch (err) {
        alert('Ошибка: ' + err.message);
    } finally {
        processBtn.disabled = false;
        loadingSection.style.display = 'none';
    }
}

function displayResults(data) {
    // Show OCR text
    ocrText.textContent = data.ocr_text;

    // Show extracted fields
    fieldsContainer.innerHTML = '';
    const fields = data.fields;
    extractedFields = { ...fields };
    const labels = data.field_labels || {};

    for (const [key, value] of Object.entries(fields)) {
        if (key.startsWith('_')) continue; // skip internal keys

        const row = document.createElement('div');
        row.className = 'field-row';

        const label = document.createElement('label');
        label.textContent = labels[key] || key;
        label.setAttribute('for', `field-${key}`);

        const input = document.createElement('input');
        input.type = 'text';
        input.id = `field-${key}`;
        input.value = value || '';
        input.className = 'field-input';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn-copy';
        copyBtn.textContent = 'Копировать';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(input.value);
            copyBtn.textContent = 'Скопировано!';
            setTimeout(() => copyBtn.textContent = 'Копировать', 1500);
        };

        row.appendChild(label);
        row.appendChild(input);
        row.appendChild(copyBtn);
        fieldsContainer.appendChild(row);
    }

    // Show error if JSON parsing failed
    if (fields._error) {
        const errDiv = document.createElement('div');
        errDiv.className = 'field-error';
        errDiv.textContent = fields._error + ': ' + (fields._raw_response || '');
        fieldsContainer.appendChild(errDiv);
    }

    resultsSection.style.display = 'block';
}

function copyAllFields() {
    const inputs = fieldsContainer.querySelectorAll('.field-input');
    const lines = [];
    inputs.forEach(input => {
        const label = input.previousElementSibling?.textContent || '';
        if (input.value) {
            lines.push(`${label}: ${input.value}`);
        }
    });
    navigator.clipboard.writeText(lines.join('\n'));

    const btn = event.target;
    btn.textContent = 'Скопировано!';
    setTimeout(() => btn.textContent = 'Копировать всё', 1500);
}

function getEditedFields() {
    // Collect current values from inputs (user may have edited them)
    const fields = {};
    const inputs = fieldsContainer.querySelectorAll('.field-input');
    inputs.forEach(input => {
        const key = input.id.replace('field-', '');
        fields[key] = input.value;
    });
    return fields;
}

async function generateQuestionnaire() {
    const fields = getEditedFields();

    try {
        const resp = await fetch('/generate-questionnaire', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fields }),
        });

        if (!resp.ok) {
            alert('Ошибка генерации анкеты');
            return;
        }

        // Download the file
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `anketa_${fields.surname || 'работник'}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (err) {
        alert('Ошибка: ' + err.message);
    }
}
