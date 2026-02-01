"""
SSM Question Generator - Web UI

Simple Flask-based web interface for generating SSM questions.

Usage:
    python web.py
    Then open http://localhost:5000 in your browser
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread

from flask import Flask, render_template_string, request, jsonify, Response

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ssm.generator import config
from ssm.generator.pipeline import (
    generate_questions_batch,
    verify_questions,
    filter_valid_questions,
    validate_question_structure,
    extract_text,
)

import httpx

app = Flask(__name__)

# Store generation progress
generation_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "message": "",
    "questions": [],
    "errors": []
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSM Question Generator</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2rem;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #a0a0a0;
        }

        input, select, textarea {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #00d4ff;
        }

        .row {
            display: flex;
            gap: 20px;
        }

        .row .form-group {
            flex: 1;
        }

        button {
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            color: #fff;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.3);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .progress-container {
            display: none;
            margin-top: 20px;
        }

        .progress-bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            width: 0%;
            transition: width 0.3s;
        }

        .status-message {
            margin-top: 10px;
            color: #a0a0a0;
            font-size: 14px;
        }

        .results {
            display: none;
        }

        .question-preview {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 3px solid #00d4ff;
        }

        .question-preview h4 {
            color: #00d4ff;
            margin-bottom: 8px;
            font-size: 14px;
        }

        .question-preview p {
            color: #e0e0e0;
            line-height: 1.5;
        }

        .answers {
            margin-top: 10px;
            padding-left: 20px;
        }

        .answer {
            padding: 4px 0;
            color: #a0a0a0;
        }

        .answer.correct {
            color: #00ff88;
            font-weight: 500;
        }

        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }

        .stat {
            flex: 1;
            text-align: center;
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stat-label {
            color: #a0a0a0;
            font-size: 14px;
            margin-top: 4px;
        }

        .actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .actions button {
            flex: 1;
        }

        .btn-secondary {
            background: rgba(255,255,255,0.1);
        }

        .error {
            background: rgba(255,0,0,0.2);
            border: 1px solid rgba(255,0,0,0.3);
            color: #ff6b6b;
            padding: 12px;
            border-radius: 8px;
            margin-top: 10px;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .checkbox-group input {
            width: auto;
        }

        .file-input-wrapper {
            position: relative;
        }

        .file-input-wrapper input[type="file"] {
            position: absolute;
            left: 0;
            top: 0;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        .file-input-display {
            padding: 12px 16px;
            border: 2px dashed rgba(255,255,255,0.2);
            border-radius: 8px;
            text-align: center;
            color: #a0a0a0;
            transition: border-color 0.3s;
        }

        .file-input-wrapper:hover .file-input-display {
            border-color: #00d4ff;
        }

        .api-key-warning {
            background: rgba(255,165,0,0.2);
            border: 1px solid rgba(255,165,0,0.3);
            color: #ffa500;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>SSM Question Generator</h1>

        <div id="apiKeyWarning" class="api-key-warning">
            OPENAI_API_KEY non configurata. Inserisci la tua API key qui sotto.
        </div>

        <div class="card">
            <form id="generateForm">
                <div class="form-group">
                    <label>API Key OpenAI (opzionale se configurata come env var)</label>
                    <input type="password" id="apiKey" placeholder="sk-...">
                </div>

                <div class="row">
                    <div class="form-group">
                        <label>Materia *</label>
                        <select id="materia" required>
                            <option value="">Seleziona materia...</option>
                            <option value="Cardiologia">Cardiologia</option>
                            <option value="Pneumologia">Pneumologia</option>
                            <option value="Gastroenterologia">Gastroenterologia</option>
                            <option value="Neurologia">Neurologia</option>
                            <option value="Nefrologia">Nefrologia</option>
                            <option value="Endocrinologia">Endocrinologia</option>
                            <option value="Ematologia">Ematologia</option>
                            <option value="Oncologia">Oncologia</option>
                            <option value="Pediatria">Pediatria</option>
                            <option value="Ginecologia">Ginecologia</option>
                            <option value="Ortopedia">Ortopedia</option>
                            <option value="Dermatologia">Dermatologia</option>
                            <option value="Psichiatria">Psichiatria</option>
                            <option value="Chirurgia Generale">Chirurgia Generale</option>
                            <option value="Medicina d'Urgenza">Medicina d'Urgenza</option>
                            <option value="Anestesiologia">Anestesiologia</option>
                            <option value="Radiologia">Radiologia</option>
                            <option value="Medicina Interna">Medicina Interna</option>
                            <option value="Malattie Infettive">Malattie Infettive</option>
                            <option value="Reumatologia">Reumatologia</option>
                            <option value="custom">Altra (specifica sotto)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Numero domande *</label>
                        <input type="number" id="count" value="10" min="1" max="50" required>
                    </div>
                </div>

                <div class="form-group">
                    <label>Argomento specifico (opzionale)</label>
                    <input type="text" id="argomento" placeholder="Es: Scompenso cardiaco, Aritmie...">
                </div>

                <div class="form-group">
                    <label>Testo di riferimento (opzionale)</label>
                    <textarea id="contextText" rows="4" placeholder="Incolla qui testo da libri, appunti o materiale di studio..."></textarea>
                </div>

                <div class="form-group checkbox-group">
                    <input type="checkbox" id="skipVerification">
                    <label for="skipVerification" style="margin: 0;">Salta verifica (più veloce ma meno accurato)</label>
                </div>

                <button type="submit" id="generateBtn">Genera Domande</button>

                <div class="progress-container" id="progressContainer">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="status-message" id="statusMessage">Inizializzazione...</div>
                </div>

                <div class="error" id="errorBox" style="display: none;"></div>
            </form>
        </div>

        <div class="card results" id="resultsCard">
            <h2 style="margin-bottom: 20px;">Risultati</h2>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="statGenerated">0</div>
                    <div class="stat-label">Generate</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="statValid">0</div>
                    <div class="stat-label">Valide</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="statExcluded">0</div>
                    <div class="stat-label">Escluse</div>
                </div>
            </div>

            <div id="questionsPreview"></div>

            <div class="actions">
                <button class="btn-secondary" onclick="downloadJsonl()">Scarica JSONL</button>
                <button onclick="appendToFile()">Aggiungi a domande_unite.jsonl</button>
            </div>
        </div>
    </div>

    <script>
        let generatedQuestions = [];

        // Check API key status on load
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                if (!data.api_key_configured) {
                    document.getElementById('apiKeyWarning').style.display = 'block';
                }
            });

        document.getElementById('generateForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const btn = document.getElementById('generateBtn');
            const progress = document.getElementById('progressContainer');
            const errorBox = document.getElementById('errorBox');
            const results = document.getElementById('resultsCard');

            btn.disabled = true;
            progress.style.display = 'block';
            errorBox.style.display = 'none';
            results.style.display = 'none';

            let materia = document.getElementById('materia').value;
            if (materia === 'custom') {
                materia = document.getElementById('argomento').value || 'Medicina Generale';
            }

            const data = {
                materia: materia,
                argomento: document.getElementById('argomento').value || materia,
                count: parseInt(document.getElementById('count').value),
                context_text: document.getElementById('contextText').value || null,
                skip_verification: document.getElementById('skipVerification').checked,
                api_key: document.getElementById('apiKey').value || null
            };

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                // Poll for progress
                const pollInterval = setInterval(async () => {
                    const statusRes = await fetch('/api/progress');
                    const status = await statusRes.json();

                    document.getElementById('progressFill').style.width =
                        (status.progress / status.total * 100) + '%';
                    document.getElementById('statusMessage').textContent = status.message;

                    if (!status.running) {
                        clearInterval(pollInterval);
                    }
                }, 500);

                const result = await response.json();
                clearInterval(pollInterval);

                if (result.success) {
                    generatedQuestions = result.questions;
                    showResults(result);
                } else {
                    throw new Error(result.error);
                }

            } catch (error) {
                errorBox.textContent = error.message;
                errorBox.style.display = 'block';
            } finally {
                btn.disabled = false;
                document.getElementById('progressFill').style.width = '100%';
            }
        });

        function showResults(result) {
            document.getElementById('resultsCard').style.display = 'block';
            document.getElementById('statGenerated').textContent = result.total_generated;
            document.getElementById('statValid').textContent = result.questions.length;
            document.getElementById('statExcluded').textContent = result.excluded;

            const preview = document.getElementById('questionsPreview');
            preview.innerHTML = '';

            result.questions.forEach((q, i) => {
                const div = document.createElement('div');
                div.className = 'question-preview';

                const correct = q.risposte.find(r => r.isCorrect);

                div.innerHTML = `
                    <h4>Domanda ${i + 1} - ${q.materia}</h4>
                    <p>${q.domanda}</p>
                    <div class="answers">
                        ${q.risposte.map(r => `
                            <div class="answer ${r.isCorrect ? 'correct' : ''}">
                                ${r.isCorrect ? '✓' : '○'} ${r.text}
                            </div>
                        `).join('')}
                    </div>
                `;
                preview.appendChild(div);
            });
        }

        function downloadJsonl() {
            const content = generatedQuestions.map(q => JSON.stringify(q)).join('\\n');
            const blob = new Blob([content], { type: 'application/jsonl' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `domande_${document.getElementById('materia').value}_${Date.now()}.jsonl`;
            a.click();
            URL.revokeObjectURL(url);
        }

        async function appendToFile() {
            try {
                const response = await fetch('/api/append', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ questions: generatedQuestions })
                });
                const result = await response.json();
                if (result.success) {
                    alert(`${result.count} domande aggiunte a ${result.file}`);
                } else {
                    throw new Error(result.error);
                }
            } catch (error) {
                alert('Errore: ' + error.message);
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
def api_status():
    return jsonify({
        "api_key_configured": bool(config.OPENAI_API_KEY),
        "model": config.OPENAI_MODEL
    })


@app.route('/api/progress')
def api_progress():
    return jsonify(generation_status)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    global generation_status

    data = request.json
    materia = data.get('materia', 'Medicina Generale')
    argomento = data.get('argomento', materia)
    count = min(data.get('count', 10), 50)  # Max 50 questions
    context_text = data.get('context_text')
    skip_verification = data.get('skip_verification', False)
    api_key = data.get('api_key') or config.OPENAI_API_KEY

    if not api_key:
        return jsonify({"success": False, "error": "API key non configurata"})

    generation_status = {
        "running": True,
        "progress": 0,
        "total": count,
        "message": "Avvio generazione...",
        "questions": [],
        "errors": []
    }

    try:
        # Run async generation in sync context
        questions = asyncio.run(run_generation(
            api_key=api_key,
            materia=materia,
            argomento=argomento,
            count=count,
            context_text=context_text,
            skip_verification=skip_verification
        ))

        generation_status["running"] = False
        generation_status["message"] = "Completato!"

        return jsonify({
            "success": True,
            "questions": questions,
            "total_generated": generation_status["progress"],
            "excluded": generation_status["progress"] - len(questions)
        })

    except Exception as e:
        generation_status["running"] = False
        generation_status["message"] = f"Errore: {str(e)}"
        return jsonify({"success": False, "error": str(e)})


async def run_generation(api_key, materia, argomento, count, context_text, skip_verification):
    global generation_status

    all_questions = []

    async with httpx.AsyncClient() as client:
        # Temporarily override API key
        original_key = config.OPENAI_API_KEY
        config.OPENAI_API_KEY = api_key

        try:
            remaining = count
            batch_num = 0

            while remaining > 0:
                batch_size = min(remaining, config.DEFAULT_BATCH_SIZE)
                batch_num += 1

                generation_status["message"] = f"Generazione batch {batch_num}..."

                questions = await generate_questions_batch(
                    client,
                    materia=materia,
                    argomento=argomento,
                    count=batch_size,
                    context_text=context_text,
                )

                all_questions.extend(questions)
                generation_status["progress"] = len(all_questions)

                remaining -= batch_size

                if remaining > 0:
                    await asyncio.sleep(config.RATE_LIMIT_DELAY_SECONDS)

            # Verify questions
            if not skip_verification and all_questions:
                generation_status["message"] = "Verifica domande..."

                try:
                    verifications = await verify_questions(client, all_questions)
                    all_questions = filter_valid_questions(all_questions, verifications)
                except Exception as e:
                    generation_status["errors"].append(f"Verifica fallita: {e}")

            # Validate structure
            valid_questions = []
            for q in all_questions:
                q.setdefault("has_image", False)
                q.setdefault("image_src", None)
                q.setdefault("argomenti", q.get("materia", ""))
                if validate_question_structure(q):
                    valid_questions.append(q)

            return valid_questions

        finally:
            config.OPENAI_API_KEY = original_key


@app.route('/api/append', methods=['POST'])
def api_append():
    data = request.json
    questions = data.get('questions', [])

    if not questions:
        return jsonify({"success": False, "error": "Nessuna domanda da salvare"})

    # Find the main jsonl file
    base_path = Path(__file__).parent.parent
    target_file = base_path / "domande_unite_no_duplicati.jsonl"

    if not target_file.exists():
        target_file = base_path / "domande_unite.jsonl"

    try:
        with open(target_file, "a", encoding="utf-8") as f:
            for q in questions:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")

        return jsonify({
            "success": True,
            "count": len(questions),
            "file": target_file.name
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def main():
    print("=" * 50)
    print("SSM Question Generator - Web UI")
    print("=" * 50)
    print()
    print("Apri il browser su: http://localhost:5000")
    print()
    print("Premi Ctrl+C per terminare")
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
