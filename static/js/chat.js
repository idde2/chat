const socket = io({
    path: '/chat/socket.io'
});



function formatTime(element) {
    const raw = element.getAttribute('data-time');
    const date = new Date(raw);
    element.innerHTML = date.toLocaleTimeString() + ' ' + date.toLocaleDateString("de-DE");
}

document.querySelectorAll('.time').forEach( (e) => { formatTime(e) });




const receiver = document.body.getAttribute('data-receiver');

socket.emit('join', { receiver: receiver });

socket.on('msg', (data) => {
    const container = document.querySelector('.container');
    const div = document.createElement('div');

    // Vergleich über sender_id (als String zur Sicherheit)
    const myId = document.body.getAttribute('data-user');
    const isMe = (String(data.sender_id) === String(myId));

    console.log("DEBUG: Received msg", data, "isMe:", isMe, "myId:", myId);

    div.className = `message-wrapper ${isMe ? 'du' : 'fremd'}`;

    div.innerHTML = `<p>${data.content}</p><p data-time="${new Date().toISOString()}" class="time"></p>`;

    container.insertBefore(div, container.lastElementChild);
    container.scrollTop = container.scrollHeight;

    const time = div.querySelector('.time');
    const d = new Date(time.getAttribute('data-time'));
    time.innerHTML = d.toLocaleTimeString() + ' ' + d.toLocaleDateString("de-DE");
    document.querySelectorAll('.time').forEach(formatTime);
});
socket.on('connect', () => {
    const receiver = document.body.getAttribute('data-receiver');
    // Sende direkt das Join-Event
    socket.emit('join', { receiver: receiver });
});