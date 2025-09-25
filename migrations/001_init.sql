CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_token TEXT UNIQUE NOT NULL,
    player_id TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    session_token TEXT NOT NULL REFERENCES chat_sessions (session_token) ON DELETE CASCADE,
    sender TEXT NOT NULL CHECK (sender IN ('player', 'valezap') AND sender = lower(sender)),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_token ON chat_sessions (session_token);
CREATE INDEX IF NOT EXISTS idx_messages_session_token ON messages (session_token);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at);

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

ALTER TABLE chat_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS chat_sessions_owner ON chat_sessions;
CREATE POLICY chat_sessions_owner ON chat_sessions
    USING (session_token = current_setting('app.current_session_id', true));

DROP POLICY IF EXISTS chat_sessions_insert ON chat_sessions;
CREATE POLICY chat_sessions_insert ON chat_sessions
    FOR INSERT
    WITH CHECK (current_setting('app.current_session_id', true) IS NULL);

DROP POLICY IF EXISTS messages_owner ON messages;
CREATE POLICY messages_owner ON messages
    USING (session_token = current_setting('app.current_session_id', true));

DROP POLICY IF EXISTS messages_insert ON messages;
CREATE POLICY messages_insert ON messages
    FOR INSERT
    WITH CHECK (session_token = current_setting('app.current_session_id', true));


