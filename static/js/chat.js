const socket = io({
    path: '/chat/socket.io'
});

function formatTime(element) {
    const raw = element.getAttribute('data-time');
    if (!raw) return;
    const date = new Date(raw);
    element.innerHTML = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

document.querySelectorAll('.time').forEach((e) => { formatTime(e) });

const receiver = document.body.getAttribute('data-receiver');
const myId = document.body.getAttribute('data-user');

socket.emit('join', { receiver: receiver });

// Sende mark_read beim Laden der Seite
if (myId && receiver) {
    socket.emit('mark_read', { user_id: myId, sender_id: receiver });
}

// ------------------------ E2E Web Crypto API Helper ------------------------
let e2eKey = null;
async function initE2E() {
    try {
        if (window.crypto && window.crypto.subtle) {
            // Web Crypto API verfügbar
            const keyMaterial = await window.crypto.subtle.digest(
                'SHA-256',
                new TextEncoder().encode(`eddi_chat_secret_${myId}_${receiver}`)
            );
            e2eKey = await window.crypto.subtle.importKey(
                'raw',
                keyMaterial,
                { name: 'AES-GCM' },
                false,
                ['encrypt', 'decrypt']
            );
        }
    } catch (e) {
        console.warn("E2E Crypto initialization fallback active", e);
    }
}
initE2E();

// ------------------------ File Upload Handler ------------------------
async function uploadFile(inputElement) {
    const file = inputElement.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
        alert("Datei ist zu groß! Maximal 10 MB erlaubt.");
        inputElement.value = '';
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("receiver_id", receiver);

    try {
        const response = await fetch("/chat/upload", {
            method: "POST",
            body: formData
        });
        const result = await response.json();
        if (result.code === 200) {
            console.log("Datei erfolgreich hochgeladen:", result);
            inputElement.value = '';
        } else {
            alert("Fehler beim Upload: " + (result.error || "Unbekannter Fehler"));
        }
    } catch (err) {
        console.error("Upload Fehler:", err);
        alert("Upload fehlgeschlagen.");
    }
}

// ------------------------ Socket Events ------------------------
socket.on('msg', (data) => {
    const container = document.querySelector('.container');
    const div = document.createElement('div');

    const isMe = (String(data.sender_id) === String(myId));
    div.className = `message-wrapper ${isMe ? 'du' : 'fremd'}`;

    let mediaHtml = '';
    if (data.file_url) {
        if (data.file_type === 'image') {
            mediaHtml = `<img src="${data.file_url}" alt="Bild" style="max-width: 250px; border-radius: 8px; display: block; margin-bottom: 5px;">`;
        } else if (data.file_type === 'audio') {
            mediaHtml = `<audio controls src="${data.file_url}" style="max-width: 220px; display: block; margin-bottom: 5px;"></audio>`;
        } else {
            mediaHtml = `<a href="${data.file_url}" target="_blank" style="color: #4fc3f7; text-decoration: underline; display: block; margin-bottom: 5px;"><i class="fa-solid fa-file"></i> ${data.content}</a>`;
        }
    }

    const statusHtml = isMe ? `<span class="read-status sent" style="font-size: 12px; font-weight: bold; margin-left: 4px;">✓</span>` : '';

    div.innerHTML = `${mediaHtml}<p>${data.content}</p><div style="display: flex; align-items: center; justify-content: flex-end; gap: 4px;"><p data-time="${new Date().toISOString()}" class="time"></p>${statusHtml}</div>`;

    container.insertBefore(div, container.lastElementChild);
    container.scrollTop = container.scrollHeight;

    const time = div.querySelector('.time');
    formatTime(time);

    // Wenn fremde Nachricht empfangen wird und wir im Chat sind -> mark_read senden
    if (!isMe) {
        socket.emit('mark_read', { user_id: myId, sender_id: receiver });
    }
});

// Update der Haken bei Lesebestätigung
socket.on('messages_read', (data) => {
    if (String(data.reader_id) === String(receiver)) {
        document.querySelectorAll('.message-wrapper.du .read-status').forEach(el => {
            el.className = 'read-status read';
            el.innerHTML = '<span style="color: #4fc3f7;">✓✓</span>';
        });
    }
});

socket.on('connect', () => {
    socket.emit('join', { receiver: receiver });
    if (myId && receiver) {
        socket.emit('mark_read', { user_id: myId, sender_id: receiver });
    }
});