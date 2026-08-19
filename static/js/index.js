// Group creation modal logic
document.getElementById('open-group-modal').addEventListener('click', async () => {
    const modal = document.getElementById('group-modal');
    modal.style.display = 'flex';

    const list = document.getElementById('group-members-list');
    list.innerHTML = '';
    try {
        const res = await fetch('/chat/users_list');
        const data = await res.json();
        if (data.code === 200) {
            data.users.forEach(u => {
                const label = document.createElement('label');
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = u.id;
                label.appendChild(cb);
                const span = document.createElement('span');
                span.textContent = ' ' + u.username;
                label.appendChild(span);
                list.appendChild(label);
            });
        }
    } catch (e) {
        console.error('Failed to load users', e);
    }
});

document.getElementById('cancel-group').addEventListener('click', () => {
    document.getElementById('group-modal').style.display = 'none';
});

document.getElementById('create-group').addEventListener('click', async () => {
    const name = document.getElementById('group-name').value.trim();
    const boxes = Array.from(document.querySelectorAll('#group-members-list input[type=checkbox]:checked'));
    const members = boxes.map(b => parseInt(b.value));
    if (!name) { alert('Bitte Namen eingeben'); return; }

    try {
        const resp = await fetch('/chat/create_group', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, members: members })
        });
        const j = await resp.json();
        if (j.code === 201 || resp.status === 201) {
            window.location.href = '/chat/group/' + j.group.id;
        } else {
            alert('Fehler: ' + (j.error || JSON.stringify(j)));
        }
    } catch (e) {
        console.error(e);
        alert('Fehler beim Erstellen der Gruppe');
    }
});