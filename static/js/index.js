const currentUser = document.body.getAttribute('data-user') || '';
const socket = io({
    path: window.location.pathname.startsWith('/chat') ? '/chat/socket.io' : '/socket.io'
});

socket.on('connect', () => {
    if (currentUser) {
        socket.emit('join', { user_id: currentUser });
    }
});

socket.on('online_update', (data) => {
    const onlineUsers = data.users || [];
    document.querySelectorAll('.online-indicator').forEach(el => el.classList.remove('is-online'));
    onlineUsers.forEach(username => {
        const badge = document.getElementById(`online-${username}`);
        if (badge) badge.classList.add('is-online');
    });
});

socket.on('msg', (data) => {
    if (!data) return;
    if (data.sender && data.sender !== currentUser) {
        const contactEl = document.querySelector(`.contact[data-name="${data.sender}"]`);
        if (contactEl) {
            const uid = contactEl.getAttribute('data-id');
            if (uid) {
                const badge = document.getElementById(`badge-user-${uid}`);
                if (badge) {
                    let currentCount = parseInt(badge.innerText) || 0;
                    badge.innerText = currentCount + 1;
                    badge.classList.remove('hidden');
                }
            }
        }
    }
    if (data.conv_id || data.group_id) {
        const gid = data.conv_id || data.group_id;
        const badge = document.getElementById(`badge-group-${gid}`);
        if (badge) {
            let currentCount = parseInt(badge.innerText) || 0;
            badge.innerText = currentCount + 1;
            badge.classList.remove('hidden');
        }
    }
});

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('chat_theme', next);
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) btn.innerText = next === 'dark' ? '🌙' : '☀️';
}

function updateThemeBtnIcon() {
    const current = localStorage.getItem('chat_theme') || 'dark';
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) btn.innerText = current === 'dark' ? '🌙' : '☀️';
}

function openGroupModal() {
    const modal = document.getElementById('groupModal');
    if (modal) modal.classList.remove('hidden');

    const usersUrl = window.location.pathname.startsWith('/chat') ? '/chat/users_list' : '/users_list';
    fetch(usersUrl)
        .then(res => res.json())
        .then(data => {
            const listContainer = document.getElementById('membersSelectList');
            if (listContainer) {
                if (data.code === 200 && data.users && data.users.length > 0) {
                    listContainer.innerHTML = data.users.map(u => `
                        <label class="member-checkbox-item">
                            <input type="checkbox" value="${u.id}" class="group-member-checkbox">
                            <span>${u.username}</span>
                        </label>
                    `).join('');
                } else {
                    listContainer.innerHTML = '<p style="color:#aaa;">Keine anderen Benutzer gefunden.</p>';
                }
            }
        })
        .catch(() => {
            const listContainer = document.getElementById('membersSelectList');
            if (listContainer) listContainer.innerHTML = '<p style="color:red;">Fehler beim Laden.</p>';
        });
}

function closeGroupModal() {
    const modal = document.getElementById('groupModal');
    if (modal) modal.classList.add('hidden');
}

function submitCreateGroup() {
    const nameInput = document.getElementById('groupNameInput');
    if (!nameInput) return;
    const name = nameInput.value.trim();
    const checkedBoxes = document.querySelectorAll('.group-member-checkbox:checked');
    const memberIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

    if (!name) {
        alert('Bitte gib einen Gruppennamen ein!');
        return;
    }

    const createUrl = window.location.pathname.startsWith('/chat') ? '/chat/create_group' : '/create_group';
    fetch(createUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, members: memberIds })
    })
        .then(res => res.json())
        .then(data => {
            if (data.code === 201 || data.code === 200) {
                window.location.reload();
            } else {
                alert('Fehler beim Erstellen der Gruppe');
            }
        });
}

document.addEventListener('DOMContentLoaded', updateThemeBtnIcon);

// ------------------------ Global Search ------------------------
let globalSearchTimeout = null;

function handleGlobalSearch(event) {
    const query = event.target.value.trim();
    const clearBtn = document.getElementById('search-clear-btn');
    const container = document.getElementById('search-results-container');
    const list = document.getElementById('search-results-list');

    if (clearBtn) {
        if (query.length > 0) clearBtn.classList.remove('hidden');
        else clearBtn.classList.add('hidden');
    }

    if (query.length < 2) {
        if (container) container.classList.add('hidden');
        if (list) list.innerHTML = '';
        return;
    }

    clearTimeout(globalSearchTimeout);
    globalSearchTimeout = setTimeout(() => {
        const searchUrl = (window.location.pathname.startsWith('/chat') ? '/chat/search' : '/search') + `?q=${encodeURIComponent(query)}`;
        fetch(searchUrl)
            .then(res => res.json())
            .then(data => {
                if (!container || !list) return;
                list.innerHTML = '';
                const results = data.results || [];
                if (results.length === 0) {
                    list.innerHTML = '<div style="padding: 12px; font-size: 0.85rem; color: var(--text-secondary);">Keine Nachrichten gefunden.</div>';
                } else {
                    results.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'search-result-item';
                        div.onclick = () => {
                            window.location.href = `/chat/chat/${item.other_user}`;
                        };
                        div.innerHTML = `
                            <div class="search-result-top">
                                <span><i class="fa-solid fa-user"></i> ${item.other_user}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">${item.time}</span>
                            </div>
                            <div class="search-result-snippet">${item.content}</div>
                        `;
                        list.appendChild(div);
                    });
                }
                container.classList.remove('hidden');
            });
    }, 300);
}

function clearGlobalSearch() {
    const input = document.getElementById('global-search-input');
    const clearBtn = document.getElementById('search-clear-btn');
    const container = document.getElementById('search-results-container');
    const list = document.getElementById('search-results-list');

    if (input) input.value = '';
    if (clearBtn) clearBtn.classList.add('hidden');
    if (container) container.classList.add('hidden');
    if (list) list.innerHTML = '';
}