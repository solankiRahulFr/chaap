let ws;
let currentRecipient = null;
let token = sessionStorage.getItem("access_token");
let currentUser = null;

// --- UI ELEMENTS ---
const authContainer = document.getElementById("auth-container");
const chatContainer = document.getElementById("chat-container");
const userListEl = document.getElementById("userList");
const messagesEl = document.getElementById("messages");
const currUserEl = document.getElementById("currentUser");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// --- EVENT HANDLERS ---
document.getElementById("login-btn").onclick = login;
document.getElementById("register-btn").onclick = register;
document.getElementById("logout-btn").onclick = logout;
document.getElementById("sendBtn").onclick = sendMessage;
messageInput.addEventListener('keydown', function(e){
    if(e.key === 'Enter'){
        e.preventDefault();
        sendMessage();
    }
})

// --- AUTH ---
async function register() {
  const username = document.getElementById("register-username").value;
  const password = document.getElementById("register-password").value;
  if (!username || !password) return alert("Enter username & password");

  const res = await fetch("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) return alert("Registration failed");

  alert("User created! You can now login.");
}

async function login() {
    
    
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  if (!username || !password) return alert("Enter username & password");

  const res = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });


  if (!res.ok) return alert("Login failed");
  const data = await res.json();
  token = data.access_token;
  sessionStorage.setItem("access_token", token);
  authContainer.style.display = "none";
  chatContainer.style.display = "flex";
  currUserEl.innerText =username
  connectWebSocket();
  loadUsers();
    currentRecipient = null;
  messageInput.disabled = true;
  sendBtn.disabled = true;
  messagesEl.innerHTML = "";
    document.getElementById(
    "chat-header"
  ).textContent = `Select a user to chat`;
}

function logout() {
  sessionStorage.removeItem("access_token");
  token = null;
  messagesEl.innerHTML = "";
  currentRecipient=null;
  if (ws) ws.close();
  chatContainer.style.display = "none";
  authContainer.style.display = "block";
  currUserEl.innerText =""
    document.getElementById(
    "chat-header"
  ).textContent = `Select a user to chat`;
}

// --- WEBSOCKET ---
function connectWebSocket() {
  ws = new WebSocket(`ws://${location.host}/ws?token=${token}`);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    addMessage(msg.sender_id, msg.content, false);
  };

  ws.onclose = () => console.log("WebSocket closed");
}

// --- USERS ---
async function loadUsers() {
  const res = await fetch("/users", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const users = await res.json();
  userListEl.innerHTML = "";
  const onlineRes = await fetch("/online-users", {
    headers: { "Authorization": "Bearer " + token }
  });
  const onlineUsers = await onlineRes.json();
  const onlineIds = onlineUsers.map(u => u.username);
  users.forEach((u) => {
    const li = document.createElement("li");
    li.innerHTML = `<p class="userListOnline">${u.username} ${onlineIds.includes(u.username) ? '<span style="color:green;">●</span>' : '<span style="color:gray;">●</span>'}</p>`;
    li.onclick = () => selectUser(u);
    userListEl.appendChild(li);
  });

}

// --- MESSAGES ---
function sendMessage() {
  const input = document.getElementById("messageInput");
  const text = input.value.trim() || "";
  if (!text || !currentRecipient) return;

  const msg = {
    recipient_id: currentRecipient.id,
    content: text,
  };
  ws.send(JSON.stringify(msg));
  addMessage("You", text, true);
  input.value = "";
}

function addMessage(sender, text, self = false) {
    if(text && currentRecipient){
             const div = document.createElement("div");
            div.classList.add("message");
            if (self) div.classList.add("self");
            else div.classList.add("received");
            if (sender) div.textContent = `${text}`;
            messagesEl.appendChild(div);
            messagesEl.scrollTop= messagesEl.scrollHeight;
    }
 
}

// User selected

async function selectUser(user) {
  currentRecipient = user;
  document
    .querySelectorAll("#userList li")
    .forEach((el) => el.classList.remove("active"));
  const clicked = Array.from(document.querySelectorAll("#userList li")).find(   
    (el) =>{
        const p = el.querySelector('p.userListOnline');
        const name = p.childNodes[0].nodeValue.trim();
        return name=== user.username}
  );
  clicked.classList.add("active");
  document.getElementById(
    "chat-header"
  ).textContent = `Chat with ${currentRecipient.username}`;
  messageInput.disabled = false;
  sendBtn.disabled = false;
  messagesEl.innerHTML = "";
  await loadChatHistory(user.id);
}



async function loadChatHistory(userId) {
    const res = await fetch(`/messages/${userId}`, {
    headers: { "Authorization": "Bearer " + token }
    });
    const messages = await res.json();
    messagesEl.innerHTML = "";
    messages.forEach(m => {
    const div = document.createElement("div");
    div.className = "message " + (m.sender_id === currentRecipient.id ? "received" : "self");
    div.textContent = m.content;
    messagesEl.appendChild(div);
    });
    messagesEl.scrollTop = messagesEl.scrollHeight;
}