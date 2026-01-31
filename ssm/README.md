# Simulatore SSM

WebApp per la preparazione al concorso SSM (Specializzazioni Mediche Italiane).

## Funzionalità

### Quiz
- **Simulazione SSM**: 140 domande in 210 minuti con distribuzione reale per materia (SSM 2024)
- **Esercitazione rapida**: 20 domande casuali con feedback immediato
- **Quiz personalizzato**: Scegli materie e numero di domande
- **Ripassa errori**: Quiz sulle domande sbagliate in precedenza
- **Rinforza punti deboli**: Quiz mirato sulle materie sotto il 60%

### Punteggio SSM Reale
- +1 punto per risposta corretta
- -0.25 punti per risposta errata
- 0 punti per risposta omessa
- Possibilità di saltare domande e navigare liberamente

### Statistiche Avanzate
- **Punteggio Proiettato**: Stima del punteggio SSM basata sulla performance per materia
- **Grafico di andamento**: Visualizza i progressi nel tempo
- **Analisi per materia/argomento**: Identifica i punti deboli
- **Cronologia simulazioni**: Storico completo delle simulazioni SSM

### Sincronizzazione Cloud
- Login con Google (OAuth)
- Sync automatico tra dispositivi via Supabase
- Dati sempre aggiornati su tutti i dispositivi

## Tecnologie

- HTML/CSS/JavaScript (vanilla, single-file)
- [Supabase](https://supabase.com) (auth + database)
- [Chart.js](https://www.chartjs.org/) (grafici)

## Configurazione Supabase

### 1. Crea progetto Supabase
Vai su [supabase.com](https://supabase.com) e crea un nuovo progetto.

### 2. Configura Google OAuth
1. Vai su **Authentication** → **Providers** → **Google**
2. Abilita Google e configura con le credenziali da Google Cloud Console
3. Aggiungi il redirect URL: `https://tuoprogetto.supabase.co/auth/v1/callback`

### 3. Crea la tabella
Esegui in **SQL Editor**:

```sql
CREATE TABLE user_progress (
  user_id uuid REFERENCES auth.users NOT NULL PRIMARY KEY,
  stats_data jsonb DEFAULT '{}'::jsonb,
  wrong_ids jsonb DEFAULT '[]'::jsonb,
  simulations jsonb DEFAULT '[]'::jsonb,
  projection_history jsonb DEFAULT '[]'::jsonb,
  updated_at timestamptz DEFAULT now()
);

-- Row Level Security
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own progress" ON user_progress
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own progress" ON user_progress
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress" ON user_progress
  FOR UPDATE USING (auth.uid() = user_id);
```

### 4. Configura le credenziali nell'app
Nel file `index.html`, aggiorna:

```javascript
const SUPABASE_URL = 'https://tuoprogetto.supabase.co';
const SUPABASE_KEY = 'tua-anon-key';
```

## Distribuzione Domande SSM 2024

| Materia | Domande |
|---------|---------|
| Cardiologia e Chirurgia Cardiovascolare | 14 |
| Chirurgia Generale | 10 |
| Ginecologia | 9 |
| Anestesia | 9 |
| Neurologia e Neurochirurgia | 7 |
| Pediatria | 7 |
| Ortopedia | 7 |
| Pneumologia e Chirurgia Toracica | 6 |
| Dermatologia | 6 |
| Gastroenterologia | 5 |
| Endocrinologia e Nutrizione | 5 |
| Malattie Infettive e Microbiologia | 5 |
| Radiologia | 5 |
| Statistica, Epidemiologia e Sanità Pubblica | 5 |
| Reumatologia | 5 |
| Urologia | 5 |
| Otorinolaringoiatria | 5 |
| Ematologia | 4 |
| Oncologia | 3 |
| Nefrologia | 3 |
| Psichiatria | 3 |
| Oftalmologia | 2 |
| Medicina del Lavoro | 2 |
| Medicina legale | 2 |
| *Immunologia* | 2 |
| *Genetica* | 2 |
| *Scienze di base* | 2 |
| **Totale** | **140** |

> *Le ultime 3 materie non sono nell'SSM ufficiale ma sono presenti nel database per completare le 140 domande.*

## Formato Domande

Le domande sono in formato JSONL (`domande_unite_no_duplicati.jsonl`):

```json
{
  "materia": "Cardiologia e Chirurgia Cardiovascolare",
  "argomenti": "Scompenso cardiaco",
  "domanda": "Testo della domanda...",
  "has_image": false,
  "image_src": null,
  "risposte": [
    {"id": 1, "text": "Risposta A", "isCorrect": false},
    {"id": 2, "text": "Risposta B", "isCorrect": true},
    {"id": 3, "text": "Risposta C", "isCorrect": false},
    {"id": 4, "text": "Risposta D", "isCorrect": false},
    {"id": 5, "text": "Risposta E", "isCorrect": false}
  ],
  "risposta_corretta_text": "Risposta B",
  "commento": "Spiegazione della risposta corretta..."
}
```

## Deploy

### GitHub Pages
1. Vai su **Settings** → **Pages**
2. Seleziona branch `main` e cartella `/ (root)` o `/ssm`
3. Il sito sarà disponibile su `https://username.github.io/repo/ssm/`

### Locale
Apri `index.html` in un browser (serve un server locale per il fetch delle domande):

```bash
# Con Python
python -m http.server 8000

# Con Node.js
npx serve
```

## Struttura File

```
ssm/
├── index.html                      # App completa (single-file)
├── domande_unite_no_duplicati.jsonl # Database domande
└── README.md                       # Questa documentazione
```

## License

MIT
