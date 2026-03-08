// ---- Employees list page ----

let debounceTimer = null;

document.addEventListener('DOMContentLoaded', loadEmployees);

async function loadEmployees(search = '') {
    const url = search ? `/api/employees?search=${encodeURIComponent(search)}` : '/api/employees';
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        renderEmployees(data.employees);
    } catch (err) {
        console.error('Failed to load employees:', err);
    }
}

function renderEmployees(employees) {
    const list = document.getElementById('employeesList');
    const empty = document.getElementById('emptyState');

    if (employees.length === 0) {
        list.innerHTML = '';
        list.appendChild(empty);
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    list.innerHTML = employees.map(emp => {
        const initials = (emp.surname?.[0] || '') + (emp.name?.[0] || '');
        const fullName = [emp.surname, emp.name, emp.patronymic].filter(Boolean).join(' ');
        const details = [emp.position, emp.department].filter(Boolean).join(' · ');
        return `
            <div class="employee-card" onclick="openProfile(${emp.id})">
                <div class="emp-avatar">${initials.toUpperCase()}</div>
                <div class="emp-info">
                    <div class="emp-name">${fullName || 'Без имени'}</div>
                    <div class="emp-details">
                        ${details ? `<span>${details}</span>` : ''}
                        ${emp.hire_date ? `<span>с ${emp.hire_date}</span>` : ''}
                    </div>
                </div>
                <div class="emp-actions">
                    <button class="btn-icon" onclick="event.stopPropagation(); editEmployee(${emp.id})" title="Редактировать">&#9998;</button>
                    <button class="btn-icon danger" onclick="event.stopPropagation(); removeEmployee(${emp.id}, '${fullName}')" title="Удалить">&#128465;</button>
                </div>
            </div>
        `;
    }).join('');
}

function searchEmployees() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        const query = document.getElementById('searchInput').value.trim();
        loadEmployees(query);
    }, 300);
}

function openProfile(id) {
    window.location.href = `/employees/${id}`;
}

// ---- Modal ----

function showAddModal() {
    document.getElementById('modalTitle').textContent = 'Новый сотрудник';
    document.getElementById('editEmployeeId').value = '';
    document.getElementById('employeeForm').reset();
    document.getElementById('employeeModal').style.display = 'flex';
}

async function editEmployee(id) {
    try {
        const resp = await fetch(`/api/employees/${id}`);
        const emp = await resp.json();

        document.getElementById('modalTitle').textContent = 'Редактировать сотрудника';
        document.getElementById('editEmployeeId').value = id;
        document.getElementById('formSurname').value = emp.surname || '';
        document.getElementById('formName').value = emp.name || '';
        document.getElementById('formPatronymic').value = emp.patronymic || '';
        document.getElementById('formBirthDate').value = emp.birth_date || '';
        document.getElementById('formGender').value = emp.gender || '';
        document.getElementById('formPhone').value = emp.phone || '';
        document.getElementById('formEmail').value = emp.email || '';
        document.getElementById('formDepartment').value = emp.department || '';
        document.getElementById('formPosition').value = emp.position || '';
        document.getElementById('formHireDate').value = emp.hire_date || '';
        document.getElementById('formNotes').value = emp.notes || '';

        document.getElementById('employeeModal').style.display = 'flex';
    } catch (err) {
        alert('Ошибка загрузки данных: ' + err.message);
    }
}

function closeModal() {
    document.getElementById('employeeModal').style.display = 'none';
}

async function saveEmployee(event) {
    event.preventDefault();

    const id = document.getElementById('editEmployeeId').value;
    const data = {
        surname: document.getElementById('formSurname').value,
        name: document.getElementById('formName').value,
        patronymic: document.getElementById('formPatronymic').value,
        birth_date: document.getElementById('formBirthDate').value,
        gender: document.getElementById('formGender').value,
        phone: document.getElementById('formPhone').value,
        email: document.getElementById('formEmail').value,
        department: document.getElementById('formDepartment').value,
        position: document.getElementById('formPosition').value,
        hire_date: document.getElementById('formHireDate').value,
        notes: document.getElementById('formNotes').value,
    };

    try {
        if (id) {
            await fetch(`/api/employees/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
        } else {
            await fetch('/api/employees', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
        }
        closeModal();
        loadEmployees(document.getElementById('searchInput').value.trim());
    } catch (err) {
        alert('Ошибка сохранения: ' + err.message);
    }
}

async function removeEmployee(id, name) {
    if (!confirm(`Удалить сотрудника «${name}»? Все документы из дела будут удалены.`)) return;

    try {
        await fetch(`/api/employees/${id}`, { method: 'DELETE' });
        loadEmployees(document.getElementById('searchInput').value.trim());
    } catch (err) {
        alert('Ошибка удаления: ' + err.message);
    }
}

// Close modal on overlay click
document.getElementById('employeeModal')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
});
