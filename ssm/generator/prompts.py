"""Prompt templates for SSM question generation and verification."""

GENERATION_PROMPT = '''Sei un esperto di medicina e devi generare domande a risposta multipla per il concorso SSM (Scuole di Specializzazione in Medicina).

MATERIA: {materia}
ARGOMENTO: {argomento}
NUMERO DOMANDE DA GENERARE: {count}

{context_section}

Genera esattamente {count} domande di alta qualità seguendo queste regole:
1. Ogni domanda deve avere ESATTAMENTE 5 risposte
2. Una sola risposta deve essere corretta (isCorrect: true)
3. Le risposte devono essere plausibili e ben formulate
4. Il commento deve spiegare perché la risposta corretta è giusta
5. Le domande devono essere di livello appropriato per il concorso SSM

FORMATO OUTPUT - Genera un array JSON valido con questa struttura esatta:
[
  {{
    "materia": "{materia}",
    "argomenti": "{argomento}",
    "domanda": "Testo della domanda?",
    "has_image": false,
    "image_src": null,
    "risposte": [
      {{"id": 1, "text": "Prima risposta", "isCorrect": false}},
      {{"id": 2, "text": "Seconda risposta (corretta)", "isCorrect": true}},
      {{"id": 3, "text": "Terza risposta", "isCorrect": false}},
      {{"id": 4, "text": "Quarta risposta", "isCorrect": false}},
      {{"id": 5, "text": "Quinta risposta", "isCorrect": false}}
    ],
    "risposta_corretta_text": "Seconda risposta (corretta)",
    "commento": "Spiegazione dettagliata del perché questa è la risposta corretta..."
  }}
]

IMPORTANTE:
- Rispondi SOLO con l'array JSON, senza testo aggiuntivo
- Assicurati che il JSON sia valido e parsabile
- La risposta_corretta_text deve corrispondere esattamente al text della risposta con isCorrect: true
'''

CONTEXT_WITH_TEXT = '''CONTESTO/TESTO DI RIFERIMENTO:
---
{text}
---

Usa il testo sopra come base per generare domande pertinenti e accurate.'''

CONTEXT_WITHOUT_TEXT = '''Genera le domande basandoti sulle tue conoscenze mediche aggiornate.'''


VERIFICATION_PROMPT = '''Sei un revisore esperto di domande mediche per il concorso SSM.

Analizza le seguenti domande e verifica:
1. Correttezza medica/scientifica della risposta indicata come corretta
2. Che le risposte errate siano effettivamente errate
3. Che il commento sia accurato e utile
4. Che la domanda sia formulata in modo chiaro

Per ogni domanda, rispondi con un oggetto JSON:
{{
  "domanda_index": <numero>,
  "is_valid": true/false,
  "issues": ["lista di problemi se non valida"],
  "suggested_fix": "suggerimento opzionale per correzione"
}}

DOMANDE DA VERIFICARE:
{questions_json}

Rispondi con un array JSON contenente la verifica di ogni domanda.
IMPORTANTE: Rispondi SOLO con l'array JSON, senza testo aggiuntivo.
'''
