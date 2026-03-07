const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

let history = [];

// Show empty state on load
chatMessages.innerHTML = '<div class="empty-state">Выберите модели и начните общение</div>';

// Enter to send, Shift+Enter for new line
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function getSelectedProviders() {
    const checkboxes = document.querySelectorAll('#providers input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function addUserMessage(text) {
    // Remove empty state
    const empty = chatMessages.querySelector('.empty-state');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'message user';
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingMessage(providers) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message ai';
    wrapper.id = 'loading-msg';

    const grid = document.createElement('div');
    grid.className = 'ai-responses';

    providers.forEach(p => {
        const [providerKey, model] = p.split(':');
        const card = document.createElement('div');
        card.className = 'ai-response-card';
        card.dataset.provider = p;
        card.innerHTML = `
            <div class="model-tag ${providerKey}">${model}</div>
            <div class="content">
                <div class="loading-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });

    wrapper.appendChild(grid);
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrapper;
}

function updateResponses(wrapper, results) {
    results.forEach(r => {
        const key = `${r.provider}:${r.model}`;
        const card = wrapper.querySelector(`[data-provider="${key}"]`);
        if (!card) return;

        const content = card.querySelector('.content');
        if (r.error) {
            content.innerHTML = `<div class="error">${escapeHtml(r.error)}</div>`;
        } else {
            content.textContent = r.response;
        }
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    const providers = getSelectedProviders();
    if (providers.length === 0) {
        alert('Выберите хотя бы одну модель');
        return;
    }

    addUserMessage(message);
    messageInput.value = '';
    sendBtn.disabled = true;

    const wrapper = addLoadingMessage(providers);

    try {
        const resp = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, providers, history }),
        });

        const data = await resp.json();
        updateResponses(wrapper, data.results);

        // Save to history (use first successful response)
        history.push({ role: 'user', content: message });
        const firstOk = data.results.find(r => !r.error && r.response);
        if (firstOk) {
            history.push({ role: 'assistant', content: firstOk.response });
        }
    } catch (err) {
        wrapper.innerHTML = `<div class="ai-response-card"><div class="error">Ошибка сети: ${escapeHtml(err.message)}</div></div>`;
    }

    sendBtn.disabled = false;
    messageInput.focus();
}
