(() => {
  const config = window.VALEZAP_CONFIG || {};
  const chatLog = document.getElementById('chat-log');
  const messageForm = document.getElementById('message-form');
  const messageInput = document.getElementById('message-input');
  const sendButton = messageForm.querySelector('.send-button');
  const formStatus = document.getElementById('form-status');
  const connectionStatus = document.getElementById('connection-status');
  const template = document.getElementById('message-template');

  const storageKey = 'valezap-session';
  let sessionToken = null;
  let playerId = null;
  let conversationEnded = false;
  let initializing = true;

  function escapeHtml(value) {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function applyFormatting(raw) {
    let safe = escapeHtml(raw);

    safe = safe.replace(/```([\s\S]+?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    safe = safe.replace(/`([^`]+?)`/g, '<code>$1</code>');
    safe = safe.replace(/\*(.+?)\*/g, '<strong>$1</strong>');
    safe = safe.replace(/_(.+?)_/g, '<em>$1</em>');
    safe = safe.replace(/~(.+?)~/g, '<del>$1</del>');
    safe = safe.replace(/\n/g, '<br />');

    return safe;
  }

  function formatTime(isoString) {
    const date = isoString ? new Date(isoString) : new Date();
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  function ensureTemplate() {
    if (!template?.content) {
      throw new Error('Template de mensagem não encontrado');
    }
    return template.content.firstElementChild;
  }

  function appendMessage({ sender, content, created_at: createdAt }) {
    const baseTemplate = ensureTemplate();
    const clone = baseTemplate.cloneNode(true);
    const bubble = clone.querySelector('.message');
    const messageContent = clone.querySelector('.message-content');
    const messageTime = clone.querySelector('.message-time');

    const messageClass = sender === 'player' ? 'message--player' : 'message--valezap';
    bubble.classList.add(messageClass);

    messageContent.innerHTML = applyFormatting(content);
    messageTime.textContent = formatTime(createdAt);

    chatLog.appendChild(clone);
    chatLog.scrollTop = chatLog.scrollHeight;
    return clone;
  }

  function updateStatus(text, type = 'info') {
    if (!text) {
      formStatus.textContent = '';
      formStatus.className = 'form-status';
      return;
    }
    formStatus.textContent = text;
    formStatus.className = `form-status form-status--${type}`;
  }

  function setConnectionState(state) {
    connectionStatus.textContent = state;
  }

  function lockInput() {
    sendButton.disabled = true;
    messageInput.disabled = true;
  }

  function unlockInput() {
    if (!conversationEnded) {
      sendButton.disabled = false;
      messageInput.disabled = false;
      messageInput.focus();
    }
  }

  function endConversation() {
    conversationEnded = true;
    lockInput();
    updateStatus('Conversa encerrada. Obrigado!', 'success');
  }

  function getPlayerFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const player = params.get('player');
    if (player && /^[A-Za-z0-9_-]{1,64}$/.test(player)) {
      return player;
    }
    return null;
  }

  function persistPlayerInUrl(player) {
    const url = new URL(window.location.href);
    url.searchParams.set('player', player);
    window.history.replaceState({}, '', url);
  }

  function generatePlayerId() {
    if (window.crypto?.randomUUID) {
      return window.crypto.randomUUID();
    }
    return `player-${Math.random().toString(36).slice(2, 10)}`;
  }

  function restoreCachedSession(player) {
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (cached.player !== player) return null;
      if (typeof cached.expires_at === 'string' && cached.session_token) {
        const expires = new Date(cached.expires_at);
        if (Number.isNaN(expires.getTime()) || expires < new Date()) {
          sessionStorage.removeItem(storageKey);
          return null;
        }
        return cached;
      }
    } catch (error) {
      console.warn('Não foi possível restaurar sessão cacheada', error);
      sessionStorage.removeItem(storageKey);
    }
    return null;
  }

  function cacheSession(session) {
    sessionStorage.setItem(storageKey, JSON.stringify(session));
  }

  async function ensureSession(player) {
    const cached = restoreCachedSession(player);
    if (cached) {
      sessionToken = cached.session_token;
      return cached;
    }

    const response = await fetch('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player }),
    });

    if (!response.ok) {
      throw new Error('Não foi possível iniciar a sessão');
    }

    const data = await response.json();
    sessionToken = data.session_token;
    const sessionData = {
      player: data.player,
      session_token: data.session_token,
      expires_at: data.expires_at,
    };
    cacheSession(sessionData);
    return sessionData;
  }

  async function loadHistory() {
    if (!sessionToken) return;
    const response = await fetch(`/api/messages?session_token=${encodeURIComponent(sessionToken)}`);
    if (!response.ok) {
      throw new Error('Falha ao carregar mensagens anteriores');
    }
    const payload = await response.json();
    chatLog.innerHTML = '';
    payload.messages.forEach((message) => appendMessage(message));
    if (payload.is_active === false) {
      endConversation();
    }
  }

  function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 180)}px`;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (conversationEnded) {
      return;
    }

    const rawMessage = messageInput.value.trim();
    if (!rawMessage) {
      updateStatus('Digite uma mensagem.', 'error');
      return;
    }

    if (rawMessage.length > (config.maxMessageLength || 700)) {
      updateStatus('Mensagem excede o limite permitido.', 'error');
      return;
    }

    lockInput();
    updateStatus('Enviando...', 'info');

    const playerMessage = { sender: 'player', content: rawMessage, created_at: new Date().toISOString() };
    const pendingMessage = appendMessage(playerMessage);
    messageInput.value = '';
    autoResizeTextarea();

    try {
      const response = await fetch('/api/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_token: sessionToken,
          player: playerId,
          message: rawMessage,
        }),
      });

      if (!response.ok) {
        throw new Error('Erro ao enviar mensagem');
      }

      const payload = await response.json();

      if (payload.player_message && pendingMessage) {
        const contentEl = pendingMessage.querySelector('.message-content');
        const timeEl = pendingMessage.querySelector('.message-time');
        if (payload.player_message.content && contentEl) {
          contentEl.innerHTML = applyFormatting(payload.player_message.content);
        }
        if (payload.player_message.created_at && timeEl) {
          timeEl.textContent = formatTime(payload.player_message.created_at);
        }
      }

      if (payload.valezap_message) {
        appendMessage(payload.valezap_message);
      }

      if (payload.ended) {
        endConversation();
      } else {
        updateStatus('Mensagem entregue.', 'success');
        unlockInput();
      }
    } catch (error) {
      if (pendingMessage?.remove) {
        pendingMessage.remove();
      }
      updateStatus('Não foi possível entregar a mensagem. Tente novamente.', 'error');
      console.error(error);
      unlockInput();
    }
  }

  function handleInput() {
    updateStatus('');
    autoResizeTextarea();
  }

  async function bootstrap() {
    try {
      playerId = getPlayerFromUrl();
      if (!playerId) {
        playerId = generatePlayerId();
        persistPlayerInUrl(playerId);
      }

      setConnectionState('conectando...');
      const sessionData = await ensureSession(playerId);
      setConnectionState('online');
      await loadHistory();

      sessionToken = sessionData.session_token;
      initializing = false;
      unlockInput();
    } catch (error) {
      console.error('Falha ao inicializar o ValeZap', error);
      setConnectionState('offline');
      updateStatus('Não foi possível iniciar a conversa. Recarregue a página.', 'error');
      lockInput();
    }
  }

  messageForm.addEventListener('submit', handleSubmit);
  messageInput.addEventListener('input', handleInput);
  window.addEventListener('load', bootstrap);
})();


