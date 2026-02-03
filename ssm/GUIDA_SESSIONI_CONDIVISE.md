# Guida Implementazione Sessioni Condivise SSM

## Regole Fondamentali Supabase

### 1. Query che restituiscono un singolo record

**MAI usare `.single()`** - fallisce con errore 406 se non trova righe.

```javascript
// SBAGLIATO
const { data } = await supabase
    .from('tabella')
    .select('*')
    .eq('id', id)
    .single();

// CORRETTO
const { data } = await supabase
    .from('tabella')
    .select('*')
    .eq('id', id)
    .maybeSingle();
```

### 2. Operazioni di modifica (update, insert, delete)

**SEMPRE aggiungere `.select()`** dopo le operazioni di modifica per garantire che la Promise si risolva.

```javascript
// SBAGLIATO - la Promise potrebbe non risolversi mai
const { error } = await supabase
    .from('tabella')
    .update({ campo: valore })
    .eq('id', id);

// CORRETTO
const { data, error } = await supabase
    .from('tabella')
    .update({ campo: valore })
    .eq('id', id)
    .select()
    .maybeSingle();
```

### 3. Timeout di sicurezza

**SEMPRE wrappare le chiamate Supabase con timeout** per evitare blocchi indefiniti.

```javascript
async function supabaseWithTimeout(promise, timeoutMs = 5000) {
    const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout after ${timeoutMs}ms`)), timeoutMs)
    );
    return Promise.race([promise, timeout]);
}

// Uso
const { data, error } = await supabaseWithTimeout(
    supabase.from('tabella').select('*').eq('id', id).maybeSingle(),
    5000
);
```

---

## Struttura Database Consigliata

### Tabella `shared_sessions`
```sql
create table shared_sessions (
    id uuid primary key default gen_random_uuid(),
    code text unique not null,          -- Codice 6 caratteri per join
    host_id uuid references auth.users(id),
    status text default 'waiting',      -- waiting, active, completed
    config jsonb,                        -- Configurazione quiz
    created_at timestamptz default now()
);
```

### Tabella `session_participants`
```sql
create table session_participants (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references shared_sessions(id) on delete cascade,
    user_id uuid references auth.users(id),
    display_name text,
    answers jsonb,
    score integer,
    correct integer,
    wrong integer,
    skipped integer,
    completed_at timestamptz,
    joined_at timestamptz default now(),

    unique(session_id, user_id)
);
```

### Indici
```sql
create index idx_participants_session on session_participants(session_id);
create index idx_sessions_code on shared_sessions(code);
create index idx_sessions_status on shared_sessions(status);
```

---

## Policy RLS

### shared_sessions
```sql
-- Tutti possono leggere sessioni in waiting/active
create policy "read_active_sessions" on shared_sessions
    for select using (status in ('waiting', 'active'));

-- Solo l'host può modificare
create policy "host_update" on shared_sessions
    for update using (auth.uid() = host_id);

-- Utenti autenticati possono creare
create policy "create_session" on shared_sessions
    for insert with check (auth.uid() = host_id);
```

### session_participants
```sql
-- Partecipanti vedono solo la propria sessione
create policy "read_own_session" on session_participants
    for select using (
        session_id in (
            select id from shared_sessions
            where status in ('waiting', 'active', 'completed')
        )
    );

-- Ognuno può modificare solo il proprio record
create policy "update_own" on session_participants
    for update using (auth.uid() = user_id);

-- Utenti autenticati possono unirsi
create policy "join_session" on session_participants
    for insert with check (auth.uid() = user_id);
```

---

## Pattern Realtime

### Subscription corretta
```javascript
const channel = supabase
    .channel(`session:${sessionId}`)
    .on('postgres_changes',
        {
            event: '*',
            schema: 'public',
            table: 'session_participants',
            filter: `session_id=eq.${sessionId}`
        },
        (payload) => {
            console.log('Participant change:', payload);
            // Aggiorna UI
        }
    )
    .subscribe((status) => {
        console.log('Subscription status:', status);
    });

// IMPORTANTE: Cleanup quando si esce
function cleanup() {
    supabase.removeChannel(channel);
}
```

### Non fidarsi solo del Realtime
Il realtime può perdere eventi. Fare sempre polling periodico come backup:

```javascript
let pollInterval = setInterval(async () => {
    await refreshParticipants();
}, 10000); // Ogni 10 secondi

// Cleanup
clearInterval(pollInterval);
```

---

## Gestione Stati

### Stati sessione
1. `waiting` - In attesa che tutti si uniscano
2. `active` - Quiz in corso
3. `completed` - Tutti hanno finito

### Flusso HOST
1. Crea sessione → stato `waiting`
2. Attende partecipanti (realtime + polling)
3. Avvia quiz → stato `active`
4. Completa quiz → salva risultati
5. Quando tutti completano → stato `completed`

### Flusso GUEST
1. Inserisce codice
2. Join sessione
3. Attende avvio (realtime)
4. Completa quiz → salva risultati
5. Vede risultati quando disponibili

---

## Checklist Pre-Implementazione

- [ ] Tabelle create con indici corretti
- [ ] Policy RLS testate singolarmente
- [ ] Realtime abilitato sulle tabelle
- [ ] Funzione helper per timeout Supabase
- [ ] Usare `.maybeSingle()` invece di `.single()`
- [ ] Usare `.select()` dopo ogni update/insert/delete
- [ ] Gestione errori con fallback su dati locali
- [ ] Cleanup subscription su unmount/navigazione
- [ ] Polling backup oltre al realtime

---

## Errori Comuni da Evitare

| Errore | Conseguenza | Soluzione |
|--------|-------------|-----------|
| `.single()` su query vuota | Errore 406 | Usare `.maybeSingle()` |
| Update senza `.select()` | Promise non si risolve | Aggiungere `.select().maybeSingle()` |
| No timeout su query | UI bloccata per sempre | Wrappare con `Promise.race()` |
| No cleanup subscription | Memory leak, eventi duplicati | `removeChannel()` su uscita |
| Fidarsi solo di realtime | Eventi persi | Aggiungere polling backup |
| No indici su foreign key | Query lente | Creare indici |
