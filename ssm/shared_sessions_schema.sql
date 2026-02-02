-- Schema per Sessioni Condivise Quiz SSM
-- Eseguire in Supabase SQL Editor

-- Tabella sessioni condivise
CREATE TABLE shared_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(6) UNIQUE NOT NULL,
  created_by uuid REFERENCES auth.users NOT NULL,
  creator_name text,
  question_ids jsonb NOT NULL,
  quiz_type varchar(50) NOT NULL,
  question_count int NOT NULL,
  time_limit int,
  status varchar(20) DEFAULT 'waiting',
  started_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Tabella partecipanti
CREATE TABLE session_participants (
  session_id uuid REFERENCES shared_sessions(id) ON DELETE CASCADE,
  user_id uuid REFERENCES auth.users NOT NULL,
  user_name text,
  user_email text,
  answers jsonb DEFAULT '{}',
  score numeric,
  correct int DEFAULT 0,
  wrong int DEFAULT 0,
  skipped int DEFAULT 0,
  completed_at timestamptz,
  joined_at timestamptz DEFAULT now(),
  PRIMARY KEY (session_id, user_id)
);

-- Abilita RLS (Row Level Security)
ALTER TABLE shared_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_participants ENABLE ROW LEVEL SECURITY;

-- Policy per shared_sessions
-- Tutti gli utenti autenticati possono vedere le sessioni
CREATE POLICY "Users can view sessions" ON shared_sessions
  FOR SELECT USING (auth.uid() IS NOT NULL);

-- Gli utenti possono creare sessioni
CREATE POLICY "Users can create sessions" ON shared_sessions
  FOR INSERT WITH CHECK (auth.uid() = created_by);

-- I creatori possono aggiornare le proprie sessioni
CREATE POLICY "Creators can update their sessions" ON shared_sessions
  FOR UPDATE USING (auth.uid() = created_by);

-- Policy per session_participants
-- Tutti gli utenti autenticati possono vedere i partecipanti
CREATE POLICY "Users can view participants" ON session_participants
  FOR SELECT USING (auth.uid() IS NOT NULL);

-- Gli utenti possono unirsi alle sessioni
CREATE POLICY "Users can join sessions" ON session_participants
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Gli utenti possono aggiornare la propria partecipazione
CREATE POLICY "Users can update own participation" ON session_participants
  FOR UPDATE USING (auth.uid() = user_id);

-- Gli utenti possono lasciare le sessioni (delete)
CREATE POLICY "Users can leave sessions" ON session_participants
  FOR DELETE USING (auth.uid() = user_id);

-- Abilita Realtime per le tabelle
ALTER PUBLICATION supabase_realtime ADD TABLE shared_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE session_participants;

-- Indici per performance
CREATE INDEX idx_shared_sessions_code ON shared_sessions(code);
CREATE INDEX idx_shared_sessions_status ON shared_sessions(status);
CREATE INDEX idx_session_participants_session ON session_participants(session_id);
