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
        if (typeof getDraftKey === 'function') localStorage.removeItem(getDraftKey());

        const encText = await encryptMessage(text);
        const formData = new FormData();
        formData.append("msg", encText);
        if (groupId) {
            formData.append("group_id", groupId);
        }

        const replyToId = document.getElementById('reply-to-id-input')?.value;
        if (replyToId) formData.append("reply_to_id", replyToId);

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

        cancelReply();
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
            mediaHtml = `<div class="audio-player-wrapper"><audio controls src="${data.file_url}"></audio><button type="button" class="speed-btn" onclick="toggleAudioSpeed(this)">1x</button></div>`;
        } else {
            mediaHtml = `<a href="${data.file_url}" target="_blank" style="color: #4fc3f7; text-decoration: underline; display: block; margin-bottom: 5px;"><i class="fa-solid fa-file"></i> ${data.content}</a>`;
        }
    }

    const clearContent = await decryptMessage(data.content);
    const statusHtml = isMe ? `<span class="read-status sent" style="font-size: 12px; font-weight: bold; margin-left: 4px;">✓</span>` : '';
    const msgId = data.msg_id || 0;
    if (msgId) div.setAttribute('data-msg-id', msgId);
    if (data.reply_to_id) div.setAttribute('data-reply-to-id', data.reply_to_id);

    // Build quote box if replying
    let quoteHtml = '';
    if (data.reply_to_id) {
        const origEl = document.querySelector(`[data-msg-id="${data.reply_to_id}"]`);
        if (origEl) {
            const origP = origEl.querySelector('p');
            const origName = origEl.classList.contains('du') ? 'Du' : (origEl.querySelector('div[style]')?.textContent || 'Unbekannt');
            const origText = origP ? origP.textContent.substring(0, 80) : '...';
            quoteHtml = `<div class="quote-box" onclick="scrollToMessage(${data.reply_to_id})"><div class="quote-box-sender">${origName}</div><div class="quote-box-text">${origText}</div></div>`;
        }
    }

    function escapeAttr(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    const quickReactionsHtml = msgId ? `<div class="quick-reactions">
        <span onclick="toggleReaction(${msgId}, '👍')">👍</span>
        <span onclick="toggleReaction(${msgId}, '❤️')">❤️</span>
        <span onclick="toggleReaction(${msgId}, '😂')">😂</span>
        <span onclick="toggleReaction(${msgId}, '🔥')">🔥</span>
        <span class="action-icon pin-action" onclick="pinMessage(${msgId})" title="Anheften"><i class="fa-solid fa-thumbtack"></i></span>
        <span class="reply-action" data-msg-id="${msgId}" data-sender-name="${escapeAttr(data.sender || '')}" onclick="handleReplyClick(this)" title="Antworten"><i class="fa-solid fa-reply"></i></span>
        ${isMe ? `<span class="action-icon edit-action" onclick="openEditModal(${msgId})" title="Bearbeiten"><i class="fa-solid fa-pen"></i></span>` : ''}
        <span class="action-icon delete-action" onclick="openDeleteModal(${msgId}, ${isMe ? 'true' : 'false'})" title="Löschen"><i class="fa-solid fa-trash"></i></span>
    </div>` : '';

    div.innerHTML = `${quoteHtml}${mediaHtml}<p>${clearContent}</p><div style="display: flex; align-items: center; justify-content: flex-end; gap: 4px;"><p data-time="${new Date().toISOString()}" class="time"></p>${statusHtml}</div><div class="reactions-bar"></div>${quickReactionsHtml}`;

    container.appendChild(div);
    scrollToBottom();

    const time = div.querySelector('.time');
    formatTime(time);

    if (!isMe && !groupId) {
        socket.emit('mark_read', { user_id: myId, sender_id: receiver });
    }

    // Play notification sound and trigger desktop notification for incoming messages
    if (!isMe) {
        playNotificationSound();
        if (typeof triggerSystemNotification === 'function') {
            triggerSystemNotification(data.sender || 'Unbekannt', clearContent);
        }
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

// ======================== Feature: Reply System ========================
let currentReplyId = null;

function handleReplyClick(el) {
    if (!el) return;
    const msgId = el.getAttribute('data-msg-id');
    const senderName = el.getAttribute('data-sender-name');
    setReply(msgId, senderName, el);
}

function setReply(msgId, senderName, triggerEl) {
    currentReplyId = msgId;
    const msgEl = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (!msgEl) return;

    const nameEl = document.getElementById('reply-user-name');
    const snippetEl = document.getElementById('reply-message-snippet');
    const inputEl = document.getElementById('reply-to-id-input');
    const bar = document.getElementById('reply-preview-bar');

    if (nameEl) nameEl.textContent = senderName || 'Unbekannt';
    if (snippetEl) {
        const p = msgEl.querySelector('p');
        snippetEl.textContent = p ? p.textContent.substring(0, 100) : '...';
    }
    if (inputEl) inputEl.value = String(msgId);
    if (bar) bar.classList.remove('hidden');

    const msgInput = document.getElementById('msg-input');
    if (msgInput) msgInput.focus();
}

function cancelReply() {
    currentReplyId = null;
    const bar = document.getElementById('reply-preview-bar');
    const inputEl = document.getElementById('reply-to-id-input');
    if (bar) bar.classList.add('hidden');
    if (inputEl) inputEl.value = '';
}

function scrollToMessage(msgId) {
    const el = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.add('highlight-flash');
    setTimeout(() => el.classList.remove('highlight-flash'), 1500);
}

// Render quote boxes for existing messages that have reply_to_id
function renderQuoteBoxes() {
    document.querySelectorAll('.message-wrapper[data-reply-to-id]').forEach(el => {
        const replyId = el.getAttribute('data-reply-to-id');
        if (!replyId || el.querySelector('.quote-box')) return;

        const origEl = document.querySelector(`[data-msg-id="${replyId}"]`);
        if (!origEl) return;

        const origP = origEl.querySelector('p');
        const origSenderDiv = origEl.querySelector('div[style]');
        const origName = origEl.classList.contains('du') ? 'Du' : (origSenderDiv ? origSenderDiv.textContent.trim() : 'Unbekannt');
        const origText = origP ? origP.textContent.substring(0, 80) : '...';

        const quoteBox = document.createElement('div');
        quoteBox.className = 'quote-box';
        quoteBox.onclick = () => scrollToMessage(parseInt(replyId));
        quoteBox.innerHTML = `<div class="quote-box-sender">${origName}</div><div class="quote-box-text">${origText}</div>`;
        el.insertBefore(quoteBox, el.firstChild);
    });
}

// Re-render quote boxes after E2E decryption finishes
const origDecryptExisting = decryptExistingMessages;
decryptExistingMessages = async function() {
    await origDecryptExisting();
    renderQuoteBoxes();
};

// ======================== Feature: Voice Messages ========================
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingSeconds = 0;
let mediaStream = null;
let isRecording = false;

function getSupportedAudioMimeType() {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    for (let t of types) {
        if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
}

function toggleVoiceRecording() {
    if (isRecording) {
        stopAndSendVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

async function startVoiceRecording() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
        console.error('Mikrofon-Zugriff verweigert:', e);
        alert('Bitte erlaube den Mikrofon-Zugriff.');
        return;
    }

    const mimeType = getSupportedAudioMimeType();
    const options = mimeType ? { mimeType } : {};

    try {
        mediaRecorder = new MediaRecorder(mediaStream, options);
    } catch (e) {
        console.error('MediaRecorder Fehler:', e);
        mediaStream.getTracks().forEach(t => t.stop());
        return;
    }

    audioChunks = [];
    recordingSeconds = 0;
    isRecording = true;

    mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.start(250);

    // UI: Show recording bar, update mic button
    const recBar = document.getElementById('recording-bar');
    const micBtn = document.getElementById('mic-btn');
    if (recBar) recBar.classList.remove('hidden');
    if (micBtn) micBtn.classList.add('recording');

    const timerEl = document.getElementById('recording-timer');
    recordingInterval = setInterval(() => {
        recordingSeconds++;
        if (timerEl) {
            const min = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
            const sec = String(recordingSeconds % 60).padStart(2, '0');
            timerEl.textContent = `${min}:${sec}`;
        }
        if (recordingSeconds >= 120) {
            stopAndSendVoiceRecording();
        }
    }, 1000);
}

function stopAndSendVoiceRecording() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

    mediaRecorder.onstop = async () => {
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunks, { type: mimeType });
        audioChunks = [];

        const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
        const formData = new FormData();
        formData.append('file', blob, `voice_message.${ext}`);

        if (groupId) {
            formData.append('group_id', groupId);
        } else {
            formData.append('receiver_id', receiver);
        }

        try {
            await fetch(getApiPrefix() + '/upload', { method: 'POST', body: formData });
        } catch (e) {
            console.error('Voice upload Fehler:', e);
        }

        resetRecordingUI();
    };

    mediaRecorder.stop();
    if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
}

function cancelVoiceRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.onstop = () => {}; // discard
        mediaRecorder.stop();
    }
    if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
    audioChunks = [];
    resetRecordingUI();
}

function resetRecordingUI() {
    isRecording = false;
    clearInterval(recordingInterval);
    recordingSeconds = 0;
    const recBar = document.getElementById('recording-bar');
    const micBtn = document.getElementById('mic-btn');
    const timerEl = document.getElementById('recording-timer');
    if (recBar) recBar.classList.add('hidden');
    if (micBtn) micBtn.classList.remove('recording');
    if (timerEl) timerEl.textContent = '00:00';
}

function toggleAudioSpeed(btn) {
    const audio = btn.parentElement.querySelector('audio');
    if (!audio) return;
    const speeds = [1, 1.5, 2];
    const current = audio.playbackRate;
    const idx = speeds.indexOf(current);
    const next = speeds[(idx + 1) % speeds.length];
    audio.playbackRate = next;
    btn.textContent = next + 'x';
}

// ======================== Feature: In-Chat Live Search ========================
let searchResults = [];
let currentSearchIndex = -1;

function toggleChatSearch() {
    const bar = document.getElementById('chat-search-bar');
    if (!bar) return;
    bar.classList.toggle('hidden');
    if (!bar.classList.contains('hidden')) {
        const input = document.getElementById('chat-search-input');
        if (input) input.focus();
    } else {
        closeChatSearch();
    }
}

function onChatSearchInput() {
    const input = document.getElementById('chat-search-input');
    const query = input ? input.value.trim() : '';

    // Restore original text first
    document.querySelectorAll('.message-wrapper p').forEach(p => {
        if (p.dataset.originalText !== undefined) {
            p.textContent = p.dataset.originalText;
        }
    });

    searchResults = [];
    currentSearchIndex = -1;

    if (!query) {
        updateSearchCounter();
        return;
    }

    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');

    document.querySelectorAll('.message-wrapper p').forEach(p => {
        if (p.dataset.originalText === undefined) {
            p.dataset.originalText = p.textContent;
        }
        const originalText = p.dataset.originalText;
        if (regex.test(originalText)) {
            p.innerHTML = originalText.replace(regex, '<mark class="search-highlight">$1</mark>');
        }
    });

    searchResults = Array.from(document.querySelectorAll('mark.search-highlight'));
    if (searchResults.length > 0) {
        focusSearchResult(0);
    } else {
        updateSearchCounter();
    }
}

function focusSearchResult(index) {
    searchResults.forEach(el => el.classList.remove('active-highlight'));
    currentSearchIndex = index;
    if (searchResults[index]) {
        searchResults[index].classList.add('active-highlight');
        searchResults[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    updateSearchCounter();
}

function navigateSearch(direction) {
    if (searchResults.length === 0) return;
    const newIndex = (currentSearchIndex + direction + searchResults.length) % searchResults.length;
    focusSearchResult(newIndex);
}

function onSearchKeyDown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        navigateSearch(event.shiftKey ? -1 : 1);
    } else if (event.key === 'Escape') {
        closeChatSearch();
    }
}

function closeChatSearch() {
    const bar = document.getElementById('chat-search-bar');
    const input = document.getElementById('chat-search-input');
    if (bar) bar.classList.add('hidden');
    if (input) input.value = '';

    // Restore all original text
    document.querySelectorAll('.message-wrapper p').forEach(p => {
        if (p.dataset.originalText !== undefined) {
            p.textContent = p.dataset.originalText;
        }
    });
    searchResults = [];
    currentSearchIndex = -1;
    updateSearchCounter();
}

function updateSearchCounter() {
    const counter = document.getElementById('search-counter');
    if (!counter) return;
    if (searchResults.length === 0) {
        counter.textContent = '0/0';
    } else {
        counter.textContent = `${currentSearchIndex + 1}/${searchResults.length}`;
    }
}

// ======================== Feature: Image Lightbox ========================
let lightboxImages = [];
let currentLightboxIndex = 0;
let isZoomed = false;

document.body.addEventListener('click', (e) => {
    const img = e.target.closest('.message-wrapper img, .gallery-item img, .gallery-grid img');
    if (!img) return;
    // Exclude profile images
    if (img.closest('.user-info')) return;
    // Exclude non-image links (audio icons etc.)
    if (!img.src || img.src.includes('fa-')) return;

    e.preventDefault();
    e.stopPropagation();

    // Collect all chat images
    lightboxImages = Array.from(document.querySelectorAll('.message-wrapper img, .gallery-item img, .gallery-grid img')).filter(i => {
        return i.src && !i.closest('.user-info') && !i.src.includes('fa-');
    });

    const idx = lightboxImages.indexOf(img);
    openLightbox(idx >= 0 ? idx : 0);
});

function openLightbox(index) {
    currentLightboxIndex = index;
    isZoomed = false;

    const modal = document.getElementById('imageLightboxModal');
    const lbImg = document.getElementById('lightbox-img');
    const dlBtn = document.getElementById('lightbox-download');
    const counter = document.getElementById('lightbox-counter');

    if (!modal || !lbImg) return;

    const src = lightboxImages[index]?.src || '';
    lbImg.src = src;
    lbImg.classList.remove('zoomed');
    if (dlBtn) dlBtn.href = src;
    if (counter) counter.textContent = `${index + 1} / ${lightboxImages.length}`;

    modal.classList.remove('hidden');
    document.addEventListener('keydown', lightboxKeyHandler);
}

function closeLightbox() {
    const modal = document.getElementById('imageLightboxModal');
    if (modal) modal.classList.add('hidden');
    document.removeEventListener('keydown', lightboxKeyHandler);
    isZoomed = false;
    const lbImg = document.getElementById('lightbox-img');
    if (lbImg) lbImg.classList.remove('zoomed');
}

function navigateLightbox(direction) {
    if (lightboxImages.length === 0) return;
    currentLightboxIndex = (currentLightboxIndex + direction + lightboxImages.length) % lightboxImages.length;
    isZoomed = false;

    const lbImg = document.getElementById('lightbox-img');
    const dlBtn = document.getElementById('lightbox-download');
    const counter = document.getElementById('lightbox-counter');

    const src = lightboxImages[currentLightboxIndex]?.src || '';
    if (lbImg) { lbImg.src = src; lbImg.classList.remove('zoomed'); }
    if (dlBtn) dlBtn.href = src;
    if (counter) counter.textContent = `${currentLightboxIndex + 1} / ${lightboxImages.length}`;
}

function toggleLightboxZoom(event) {
    event.stopPropagation();
    const lbImg = document.getElementById('lightbox-img');
    if (!lbImg) return;
    isZoomed = !isZoomed;
    lbImg.classList.toggle('zoomed', isZoomed);
}

function handleLightboxBackdropClick(event) {
    if (event.target === document.getElementById('imageLightboxModal')) {
        closeLightbox();
    }
}

function lightboxKeyHandler(e) {
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowLeft') navigateLightbox(-1);
    else if (e.key === 'ArrowRight') navigateLightbox(1);
}

// ======================== Feature: Audio Notification ========================
let audioCtx = null;

function unlockAudioContext() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) audioCtx = new AudioContext();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}
document.addEventListener('click', unlockAudioContext, { once: true });

function playNotificationSound() {
    if (localStorage.getItem('chat_sound_enabled') === 'false') return;
    try {
        unlockAudioContext();
        if (!audioCtx) return;

        const now = audioCtx.currentTime;

        const osc1 = audioCtx.createOscillator();
        const gain1 = audioCtx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(659.25, now); // E5
        gain1.gain.setValueAtTime(0.15, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc1.connect(gain1);
        gain1.connect(audioCtx.destination);
        osc1.start(now);
        osc1.stop(now + 0.25);

        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(987.77, now + 0.1); // B5
        gain2.gain.setValueAtTime(0.2, now + 0.1);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        osc2.start(now + 0.1);
        osc2.stop(now + 0.4);
    } catch (e) {
        console.warn("Audio-Benachrichtigung konnte nicht abgespielt werden:", e);
    }
}

function toggleSoundSetting() {
    const btn = document.getElementById('sound-toggle-btn');
    if (!btn) return;
    const icon = btn.querySelector('i');
    const enabled = localStorage.getItem('chat_sound_enabled') !== 'false';
    if (enabled) {
        localStorage.setItem('chat_sound_enabled', 'false');
        if (icon) { icon.className = 'fa-solid fa-volume-xmark'; }
    } else {
        localStorage.setItem('chat_sound_enabled', 'true');
        if (icon) { icon.className = 'fa-solid fa-volume-high'; }
    }
}

// Initialize sound icon state on page load
(function initSoundIcon() {
    const btn = document.getElementById('sound-toggle-btn');
    if (!btn) return;
    const icon = btn.querySelector('i');
    if (localStorage.getItem('chat_sound_enabled') === 'false') {
        if (icon) icon.className = 'fa-solid fa-volume-xmark';
    }
})();

// ======================== Feature 1: Edit & Delete System ========================
let activeEditMsgId = null;
let activeDeleteMsgId = null;

function openEditModal(msgId) {
    activeEditMsgId = msgId;
    const msgEl = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (!msgEl) return;
    const p = msgEl.querySelector('p');
    if (!p) return;

    let text = p.dataset.originalText || p.textContent;
    text = text.replace(/\s*\(bearbeitet\)$/, '');

    const input = document.getElementById('edit-message-input');
    if (input) input.value = text;

    const modal = document.getElementById('editMessageModal');
    if (modal) modal.classList.remove('hidden');
}

function closeEditModal() {
    activeEditMsgId = null;
    const modal = document.getElementById('editMessageModal');
    if (modal) modal.classList.add('hidden');
}

async function saveEditedMessage() {
    if (!activeEditMsgId) return;
    const input = document.getElementById('edit-message-input');
    const newText = input ? input.value.trim() : '';
    if (!newText) return;

    const encText = await encryptMessage(newText);
    try {
        const res = await fetch(`${getApiPrefix()}/edit_msg`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ msg_id: activeEditMsgId, content: encText })
        });
        if (res.ok) {
            closeEditModal();
        } else {
            const data = await res.json();
            alert("Fehler beim Bearbeiten: " + (data.error || "Unbekannter Fehler"));
        }
    } catch (e) {
        console.error("Edit Fehler:", e);
    }
}

socket.on('msg_edited', async (data) => {
    const el = document.querySelector(`[data-msg-id="${data.msg_id}"]`);
    if (!el) return;
    const p = el.querySelector('p');
    if (p) {
        const clearContent = await decryptMessage(data.content);
        p.dataset.originalText = clearContent;
        p.textContent = clearContent;
    }
});

function openDeleteModal(msgId, isMe) {
    activeDeleteMsgId = msgId;
    const forAllBtn = document.getElementById('delete-for-all-btn');
    if (forAllBtn) {
        if (isMe) {
            forAllBtn.style.display = 'block';
        } else {
            forAllBtn.style.display = 'none';
        }
    }
    const modal = document.getElementById('deleteMessageModal');
    if (modal) modal.classList.remove('hidden');
}

function closeDeleteModal() {
    activeDeleteMsgId = null;
    const modal = document.getElementById('deleteMessageModal');
    if (modal) modal.classList.add('hidden');
}

async function confirmDeleteMessage(mode) {
    if (!activeDeleteMsgId) return;
    const msgId = activeDeleteMsgId;
    closeDeleteModal();
    await deleteMessage(msgId, mode);
}

async function deleteMessage(msgId, mode) {
    try {
        const res = await fetch(`${getApiPrefix()}/delete_msg`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ msg_id: msgId, mode: mode })
        });
        if (res.ok && mode === 'me') {
            const el = document.querySelector(`[data-msg-id="${msgId}"]`);
            if (el) el.remove();
        }
    } catch (e) {
        console.error("Delete Fehler:", e);
    }
}

socket.on('msg_deleted', (data) => {
    const el = document.querySelector(`[data-msg-id="${data.msg_id}"]`);
    if (el) el.remove();
});

// ======================== Feature 2: Drag & Drop & Paste Preview ========================
let pendingUploadBlob = null;

function showUploadPreview(fileOrBlob) {
    pendingUploadBlob = fileOrBlob;
    const bar = document.getElementById('upload-preview-bar');
    const imgEl = document.getElementById('upload-preview-img');
    const docEl = document.getElementById('upload-preview-doc');
    const filenameEl = document.getElementById('upload-preview-filename');

    if (!bar) return;
    bar.classList.remove('hidden');

    const isImage = fileOrBlob.type && fileOrBlob.type.indexOf('image') !== -1;
    if (isImage) {
        const reader = new FileReader();
        reader.onload = (e) => {
            if (imgEl) {
                imgEl.src = e.target.result;
                imgEl.classList.remove('hidden');
            }
            if (docEl) docEl.classList.add('hidden');
        };
        reader.readAsDataURL(fileOrBlob);
    } else {
        if (imgEl) imgEl.classList.add('hidden');
        if (docEl) docEl.classList.remove('hidden');
        if (filenameEl) filenameEl.textContent = fileOrBlob.name || 'Datei';
    }
}

function cancelUploadPreview() {
    pendingUploadBlob = null;
    const bar = document.getElementById('upload-preview-bar');
    if (bar) bar.classList.add('hidden');
}

async function confirmUploadPreview() {
    if (!pendingUploadBlob) return;
    const blob = pendingUploadBlob;
    cancelUploadPreview();

    const formData = new FormData();
    const fileName = blob.name || `paste_${Date.now()}.png`;
    formData.append('file', blob, fileName);

    if (groupId) {
        formData.append('group_id', groupId);
    } else {
        formData.append('receiver_id', receiver);
    }

    try {
        await fetch(`${getApiPrefix()}/upload`, {
            method: 'POST',
            body: formData
        });
    } catch (e) {
        console.error("Upload Preview Fehler:", e);
    }
}

document.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
    if (!items) return;
    for (let item of items) {
        if (item.type.indexOf('image') !== -1) {
            e.preventDefault();
            const blob = item.getAsFile();
            if (blob) showUploadPreview(blob);
            break;
        }
    }
});

const dropZone = document.body;
['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        const overlay = document.getElementById('dropzone-overlay');
        if (overlay) overlay.classList.remove('hidden');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (eventName === 'drop' || e.target.id === 'dropzone-overlay') {
            const overlay = document.getElementById('dropzone-overlay');
            if (overlay) overlay.classList.add('hidden');
        }
    }, false);
});

dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
        showUploadPreview(files[0]);
    }
});

// ======================== Feature 3: Pin Message System ========================
let currentPinnedMsgId = null;

async function pinMessage(msgId) {
    if (!msgId) return;
    try {
        await fetch(`${getApiPrefix()}/pin/${msgId}`, { method: 'POST' });
    } catch (e) {
        console.error("Pin Fehler:", e);
    }
}

async function unpinCurrentMessage() {
    const targetType = groupId ? 'group' : 'user';
    const targetId = groupId ? groupId : receiver;
    try {
        await fetch(`${getApiPrefix()}/unpin/${targetType}/${targetId}`, { method: 'POST' });
    } catch (e) {
        console.error("Unpin Fehler:", e);
    }
}

function scrollToPinnedMessage() {
    if (currentPinnedMsgId) {
        scrollToMessage(currentPinnedMsgId);
    }
}

socket.on('pin_update', async (data) => {
    const bar = document.getElementById('pinned-bar');
    const snippetEl = document.getElementById('pinned-snippet');
    const senderEl = document.getElementById('pinned-sender');

    if (data && data.msg_id) {
        currentPinnedMsgId = data.msg_id;
        const clearText = await decryptMessage(data.content);
        if (snippetEl) snippetEl.textContent = clearText;
        if (senderEl) senderEl.textContent = data.sender_name || 'Unbekannt';
        if (bar) bar.classList.remove('hidden');
    } else {
        currentPinnedMsgId = null;
        if (bar) bar.classList.add('hidden');
    }
});

async function loadPinnedMessage() {
    const targetType = groupId ? 'group' : 'user';
    const targetId = groupId ? groupId : receiver;
    try {
        const res = await fetch(`${getApiPrefix()}/pinned/${targetType}/${targetId}`);
        const data = await res.json();
        if (data.code === 200 && data.pinned) {
            currentPinnedMsgId = data.pinned.msg_id;
            const bar = document.getElementById('pinned-bar');
            const snippetEl = document.getElementById('pinned-snippet');
            const senderEl = document.getElementById('pinned-sender');
            const clearText = await decryptMessage(data.pinned.content);
            if (snippetEl) snippetEl.textContent = clearText;
            if (senderEl) senderEl.textContent = data.pinned.sender_name || 'Unbekannt';
            if (bar) bar.classList.remove('hidden');
        }
    } catch (e) {
        console.error("Fehler beim Laden des Pins:", e);
    }
}
window.addEventListener('DOMContentLoaded', loadPinnedMessage);

// ======================== Feature 4: System Push Notifications ========================
function initPushNotifications() {
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }
}

function triggerSystemNotification(sender, text) {
    if (document.hidden && "Notification" in window && Notification.permission === "granted") {
        const notif = new Notification(`Neue Nachricht von ${sender}`, {
            body: text,
            icon: `/chat/static/img/profil/${sender}.png`
        });
        notif.onclick = () => {
            window.focus();
            notif.close();
        };
    }
}
document.addEventListener('click', initPushNotifications, { once: true });

// ======================== Feature 5: Auto-Save Drafts ========================
const getDraftKey = () => `chat_draft_${groupId ? 'group_' + groupId : 'user_' + receiver}`;

function initDrafts() {
    const savedDraft = localStorage.getItem(getDraftKey());
    const inputEl = document.getElementById('msg-input');
    if (savedDraft && inputEl) {
        inputEl.value = savedDraft;
    }
}

if (msgInput) {
    msgInput.addEventListener('input', () => {
        const val = msgInput.value;
        if (val.trim()) {
            localStorage.setItem(getDraftKey(), val);
        } else {
            localStorage.removeItem(getDraftKey());
        }
    });
}
window.addEventListener('DOMContentLoaded', initDrafts);

// ======================== Feature 6: Infinite Scroll & Pagination ========================
let isLoadingHistory = false;
let hasMoreHistory = true;

const containerEl = document.querySelector('.container');
if (containerEl) {
    containerEl.addEventListener('scroll', async () => {
        if (containerEl.scrollTop < 60 && !isLoadingHistory && hasMoreHistory) {
            await loadOlderMessages();
        }
    });
}

async function loadOlderMessages() {
    const container = document.querySelector('.container');
    if (!container) return;

    const firstMsg = container.querySelector('.message-wrapper[data-msg-id]');
    if (!firstMsg) return;
    const oldestId = firstMsg.getAttribute('data-msg-id');

    isLoadingHistory = true;
    const loader = document.getElementById('pagination-loader');
    if (loader) loader.classList.remove('hidden');

    const targetType = groupId ? 'group' : 'user';
    const targetId = groupId ? groupId : receiver;

    try {
        const res = await fetch(`${getApiPrefix()}/messages/history?target_type=${targetType}&target_id=${targetId}&before_id=${oldestId}&limit=50`);
        const data = await res.json();

        if (data.code === 200 && data.messages && data.messages.length > 0) {
            const oldScrollHeight = container.scrollHeight;

            const fragment = document.createDocumentFragment();
            for (const msgData of data.messages) {
                const msgEl = await createMessageElement(msgData);
                fragment.appendChild(msgEl);
            }

            const insertPoint = loader ? loader.nextSibling : container.firstChild;
            container.insertBefore(fragment, insertPoint);

            const newScrollHeight = container.scrollHeight;
            container.scrollTop = newScrollHeight - oldScrollHeight;

            hasMoreHistory = data.has_more;
        } else {
            hasMoreHistory = false;
        }
    } catch (e) {
        console.error("Fehler beim Nachladen der Historie:", e);
    } finally {
        isLoadingHistory = false;
        if (loader) loader.classList.add('hidden');
    }
}

async function createMessageElement(data) {
    const div = document.createElement('div');
    const isMe = (String(data.sender_id) === String(myId));
    div.className = `message-wrapper ${isMe ? 'du' : 'fremd'}`;

    const msgId = data.msg_id || 0;
    if (msgId) div.setAttribute('data-msg-id', msgId);
    if (data.reply_to_id) div.setAttribute('data-reply-to-id', data.reply_to_id);

    let senderHeader = '';
    if (groupId && data.username) {
        senderHeader = `<div style="font-size:0.85rem; color:#cfcfcf; margin-bottom:4px;">${data.username}</div>`;
    }

    let mediaHtml = '';
    if (data.file_url) {
        if (data.file_type === 'image') {
            mediaHtml = `<img src="${data.file_url}" alt="Bild" style="max-width: 250px; border-radius: 8px; display: block; margin-bottom: 5px;">`;
        } else if (data.file_type === 'audio') {
            mediaHtml = `<div class="audio-player-wrapper"><audio controls src="${data.file_url}"></audio><button type="button" class="speed-btn" onclick="toggleAudioSpeed(this)">1x</button></div>`;
        } else {
            mediaHtml = `<a href="${data.file_url}" target="_blank" style="color: #4fc3f7; text-decoration: underline; display: block; margin-bottom: 5px;"><i class="fa-solid fa-file"></i> ${data.content}</a>`;
        }
    }

    const clearContent = await decryptMessage(data.content);
    const statusHtml = isMe ? `<span class="read-status ${data.status || 'sent'}" style="font-size: 12px; font-weight: bold; margin-left: 4px;">✓</span>` : '';

    function escapeAttr(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    const quickReactionsHtml = msgId ? `<div class="quick-reactions">
        <span onclick="toggleReaction(${msgId}, '👍')">👍</span>
        <span onclick="toggleReaction(${msgId}, '❤️')">❤️</span>
        <span onclick="toggleReaction(${msgId}, '😂')">😂</span>
        <span onclick="toggleReaction(${msgId}, '🔥')">🔥</span>
        <span class="action-icon pin-action" onclick="pinMessage(${msgId})" title="Anheften"><i class="fa-solid fa-thumbtack"></i></span>
        <span class="reply-action" data-msg-id="${msgId}" data-sender-name="${escapeAttr(data.username || '')}" onclick="handleReplyClick(this)" title="Antworten"><i class="fa-solid fa-reply"></i></span>
        ${isMe ? `<span class="action-icon edit-action" onclick="openEditModal(${msgId})" title="Bearbeiten"><i class="fa-solid fa-pen"></i></span>` : ''}
        <span class="action-icon delete-action" onclick="openDeleteModal(${msgId}, ${isMe ? 'true' : 'false'})" title="Löschen"><i class="fa-solid fa-trash"></i></span>
    </div>` : '';

    div.innerHTML = `${senderHeader}${mediaHtml}<p>${clearContent}</p><div style="display: flex; align-items: center; justify-content: flex-end; gap: 4px;"><p data-time="${data.time}" class="time"></p>${statusHtml}</div><div class="reactions-bar"></div>${quickReactionsHtml}`;

    const timeEl = div.querySelector('.time');
    if (timeEl) formatTime(timeEl);

    return div;
}
