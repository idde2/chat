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

    const createUrl = window.location.pathname.startsWith('/chat') ? '/chat/api/groups/create' : '/api/groups/create';
    fetch(createUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, members: memberIds })
    })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                window.location.reload();
            } else {
                alert('Fehler beim Erstellen der Gruppe');
            }
        });
}