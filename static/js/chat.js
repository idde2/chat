const socket = io({
    path: window.location.pathname.startsWith('/chat') ? '/chat/socket.io' : '/socket.io'
});

function formatTime(element) {
    const raw = element.getAttribute('data-time');
    if (!raw) return;
    const date = new Date(raw);
    element.innerHTML = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

document.querySelectorAll('.time').forEach((e) => { formatTime(e) });

const receiver = document.body.getAttribute('data-receiver');
const myId = document.body.getAttribute('data-user');
const groupId = document.body.getAttribute('data-group-id');

if (groupId) {
    socket.emit('join', { group_id: groupId });
} else {
    socket.emit('join', { receiver: receiver });

    if (myId && receiver) {
        socket.emit('mark_read', { user_id: myId, sender_id: receiver });
    }
}

async function decryptExistingMessages() {
    const paragraphs = document.querySelectorAll('.message-wrapper p');
    for (const p of paragraphs) {
        if (p.textContent && p.textContent.startsWith('ENC:')) {
            p.textContent = await decryptMessage(p.textContent);
        }
    }
}

// ------------------------ E2E Web Crypto API Helper ------------------------
let e2eKey = null;

async function initE2E() {
    try {
        if (window.crypto && window.crypto.subtle) {
            const pairId = groupId ? `group_${groupId}` : [myId, receiver].sort().join('_');
            const keyMaterial = await window.crypto.subtle.digest(
                'SHA-256',
                new TextEncoder().encode(`eddi_chat_secret_${pairId}`)
            );
            e2eKey = await window.crypto.subtle.importKey(
                'raw',
                keyMaterial,
                { name: 'AES-GCM' },
                false,
                ['encrypt', 'decrypt']
            );
            console.log("E2E Schlüssel erfolgreich abgeleitet.");
        }
    } catch (e) {
        console.warn("E2E Crypto Fallback aktiv", e);
    }
}
initE2E().then(decryptExistingMessages);

async function encryptMessage(text) {
    if (!e2eKey) return text;
    try {
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const encoded = new TextEncoder().encode(text);
        const encrypted = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            e2eKey,
            encoded
        );
        const combined = new Uint8Array(iv.length + encrypted.byteLength);
        combined.set(iv, 0);
        combined.set(new Uint8Array(encrypted), iv.length);
        return 'ENC:' + btoa(String.fromCharCode(...combined));
    } catch (e) {
        console.error("Verschlüsselungsfehler:", e);
        return text;
    }
}

async function decryptMessage(cipherText) {
    if (!e2eKey || typeof cipherText !== 'string' || !cipherText.startsWith('ENC:')) {
        return cipherText;
    }
    try {
        const rawStr = atob(cipherText.slice(4));
        const combined = new Uint8Array(rawStr.length);
        for (let i = 0; i < rawStr.length; i++) {
            combined[i] = rawStr.charCodeAt(i);
        }
        const iv = combined.slice(0, 12);
        const data = combined.slice(12);
        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            e2eKey,
            data
        );
        return new TextDecoder().decode(decrypted);
    } catch (e) {
        console.warn("Entschlüsselungsfehler (Text ungültig oder Schlüssel weicht ab):", e);
        return cipherText;
    }
}

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

// ------------------------ Form Submit Handler (AJAX) ------------------------
const chatForm = document.querySelector('form.input');
if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const inputEl = document.getElementById('msg-input');
        if (!inputEl) return;
        const text = inputEl.value.trim();
        if (!text) return;

        inputEl.value = '';

        const encText = await encryptMessage(text);
        const formData = new FormData();
        formData.append("msg", encText);
        if (groupId) {
            formData.append("group_id", groupId);
        }

        let targetUrl = chatForm.getAttribute('action') || window.location.href;
        if (!targetUrl.startsWith('/chat') && window.location.pathname.startsWith('/chat')) {
            targetUrl = '/chat' + targetUrl;
        }

        try {
            await fetch(targetUrl, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: formData
            });
        } catch (err) {
            console.error("Fehler beim Senden der Nachricht:", err);
        }
    });
}

function scrollToBottom() {
    const container = document.querySelector('.container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

window.addEventListener('DOMContentLoaded', scrollToBottom);
window.addEventListener('load', scrollToBottom);
scrollToBottom();

// ------------------------ Socket Events ------------------------
socket.on('msg', async (data) => {
    console.log("Empfangene Live-Nachricht:", data);
    const container = document.querySelector('.container');
    if (!container) return;
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

    const clearContent = await decryptMessage(data.content);
    const statusHtml = isMe ? `<span class="read-status sent" style="font-size: 12px; font-weight: bold; margin-left: 4px;">✓</span>` : '';
    const msgId = data.msg_id || 0;
    if (msgId) div.setAttribute('data-msg-id', msgId);

    const quickReactionsHtml = msgId ? `<div class="quick-reactions">
        <span onclick="toggleReaction(${msgId}, '👍')">👍</span>
        <span onclick="toggleReaction(${msgId}, '❤️')">❤️</span>
        <span onclick="toggleReaction(${msgId}, '😂')">😂</span>
        <span onclick="toggleReaction(${msgId}, '🔥')">🔥</span>
    </div>` : '';

    div.innerHTML = `${mediaHtml}<p>${clearContent}</p><div style="display: flex; align-items: center; justify-content: flex-end; gap: 4px;"><p data-time="${new Date().toISOString()}" class="time"></p>${statusHtml}</div>${quickReactionsHtml}`;

    container.appendChild(div);
    scrollToBottom();

    const time = div.querySelector('.time');
    formatTime(time);

    if (!isMe && !groupId) {
        socket.emit('mark_read', { user_id: myId, sender_id: receiver });
    }
});

socket.on('messages_read', (data) => {
    if (String(data.reader_id) === String(receiver)) {
        document.querySelectorAll('.message-wrapper.du .read-status').forEach(el => {
            el.className = 'read-status read';
            el.innerHTML = '<span style="color: #4fc3f7;">✓✓</span>';
        });
    }
});

socket.on('connect', () => {
    if (groupId) {
        socket.emit('join', { group_id: groupId });
    } else {
        socket.emit('join', { receiver: receiver });
        if (myId && receiver) {
            socket.emit('mark_read', { user_id: myId, sender_id: receiver });
        }
    }
});


// ------------------------ Typing Indicator ------------------------
const msgInput = document.getElementById('msg-input');
let typingTimeout = null;

if (msgInput) {
    msgInput.addEventListener('input', () => {
        if (!groupId && receiver) {
            socket.emit('typing', { user_id: myId, receiver: receiver });

            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                socket.emit('stop_typing', { user_id: myId, receiver: receiver });
            }, 1500);
        }
    });
}

function updateReactionsUI(messageId, reactions) {
    const msgEl = document.querySelector(`[data-msg-id="${messageId}"]`);
    if (!msgEl) return;

    let reactionsBar = msgEl.querySelector('.reactions-bar');
    if (!reactionsBar) {
        reactionsBar = document.createElement('div');
        reactionsBar.className = 'reactions-bar';
        msgEl.appendChild(reactionsBar);
    }

    reactionsBar.innerHTML = '';
    if (reactions) {
        for (const [emoji, users] of Object.entries(reactions)) {
            if (users && users.length > 0) {
                const badge = document.createElement('span');
                badge.className = 'reaction-badge';
                badge.innerText = `${emoji} ${users.length}`;
                badge.onclick = () => toggleReaction(messageId, emoji);
                reactionsBar.appendChild(badge);
            }
        }
    }
}

socket.on('reaction_update', (data) => {
    if (data && data.message_id && data.reactions) {
        updateReactionsUI(data.message_id, data.reactions);
    }
});

const getApiPrefix = () => window.location.pathname.startsWith('/chat') ? '/chat' : '';

async function toggleReaction(msgId, emoji) {
    if (!msgId) return;
    try {
        const res = await fetch(`${getApiPrefix()}/reactions/${msgId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ emoji: emoji })
        });
        const data = await res.json();
        if (data && data.reactions) {
            updateReactionsUI(msgId, data.reactions);
        }
    } catch (e) {
        console.error("Fehler beim Senden der Reaktion", e);
    }
}

async function openMediaGallery() {
    const modal = document.getElementById('mediaGalleryModal');
    if (!modal) return;

    modal.classList.remove('hidden');
    const grid = document.getElementById('galleryGrid');
    grid.innerHTML = '<p style="color: var(--text-muted); text-align: center; grid-column: 1/-1;">Lade Medien...</p>';

    const targetType = groupId ? 'group' : 'user';
    const targetId = groupId ? groupId : receiver;

    try {
        const res = await fetch(`${getApiPrefix()}/media/${targetType}/${targetId}`);
        const data = await res.json();

        if (data.code === 200 && data.media && data.media.length > 0) {
            grid.innerHTML = data.media.map(item => {
                const url = item.file_url || '';
                const isImg = item.file_type === 'image' || url.match(/\.(jpg|jpeg|png|gif|webp)$/i);
                const isAudio = item.file_type === 'audio' || url.match(/\.(mp3|wav|ogg|m4a|webm)$/i);

                if (isImg) {
                    return `<div class="gallery-item"><a href="${url}" target="_blank"><img src="${url}" alt="Bild" loading="lazy"></a></div>`;
                } else if (isAudio) {
                    return `<div class="gallery-item"><a href="${url}" target="_blank"><i class="fa-solid fa-file-audio" style="font-size: 2rem; color: #10b981;"></i><br><span style="font-size:0.7rem; display:block; margin-top:4px;">Audio</span></a></div>`;
                } else {
                    return `<div class="gallery-item"><a href="${url}" target="_blank"><i class="fa-solid fa-file-lines" style="font-size: 2rem; color: #3b82f6;"></i><br><span style="font-size:0.7rem; display:block; margin-top:4px;">Dokument</span></a></div>`;
                }
            }).join('');
        } else {
            grid.innerHTML = '<p style="color: var(--text-muted); text-align: center; grid-column: 1/-1;">Keine Medien in diesem Chat vorhanden.</p>';
        }
    } catch (e) {
        console.error("Fehler beim Laden der Galerie:", e);
        grid.innerHTML = '<p style="color: #ef4444; text-align: center; grid-column: 1/-1;">Fehler beim Laden der Medien.</p>';
    }
}

function closeMediaGallery() {
    const modal = document.getElementById('mediaGalleryModal');
    if (modal) modal.classList.add('hidden');
}

const icons = document.getElementById('icons');
const iconsUser = document.getElementById('icons-user');
if (icons && iconsUser) {
    icons.addEventListener('click', () => {
        iconsUser.className = iconsUser.className === 'icons-user' ? 'icons-user show' : 'icons-user';
    });
}

