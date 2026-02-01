"""
SSM Question Generator Pipeline

Generates medical exam questions using OpenAI GPT-4o-mini with automatic verification.

Usage:
    python -m ssm.generator.pipeline --input medicina.pdf --materia "Cardiologia" --count 20
    python -m ssm.generator.pipeline --materia "Pediatria" --argomento "Malattie esantematiche" --count 15
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import httpx

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from . import config
from .prompts import (
    GENERATION_PROMPT,
    CONTEXT_WITH_TEXT,
    CONTEXT_WITHOUT_TEXT,
    VERIFICATION_PROMPT,
)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file using PyMuPDF."""
    if fitz is None:
        raise ImportError("PyMuPDF is required for PDF extraction. Install with: pip install PyMuPDF")

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Pagina {page_num + 1} ---\n{text}")

    return "\n\n".join(text_parts)


def extract_text_from_txt(txt_path: str) -> str:
    """Read text content from a TXT file."""
    path = Path(txt_path)
    if not path.exists():
        raise FileNotFoundError(f"TXT file not found: {txt_path}")

    return path.read_text(encoding="utf-8")


def extract_text(file_path: str) -> str:
    """Extract text from PDF or TXT file based on extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use .pdf or .txt")


async def call_openai_api(
    client: httpx.AsyncClient,
    messages: list[dict],
    max_retries: int = config.MAX_RETRIES,
) -> str:
    """Make an async call to OpenAI API with retry logic."""
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config.OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    for attempt in range(max_retries):
        try:
            response = await client.post(
                f"{config.OPENAI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit
                wait_time = config.RETRY_DELAY_SECONDS * (attempt + 1)
                print(f"Rate limited, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            elif attempt == max_retries - 1:
                raise
            else:
                await asyncio.sleep(config.RETRY_DELAY_SECONDS)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(config.RETRY_DELAY_SECONDS)

    raise RuntimeError("Max retries exceeded")


def parse_json_response(response: str) -> list[dict]:
    """Parse JSON from API response, handling potential markdown formatting."""
    content = response.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    return json.loads(content)


async def generate_questions_batch(
    client: httpx.AsyncClient,
    materia: str,
    argomento: str,
    count: int,
    context_text: Optional[str] = None,
) -> list[dict]:
    """Generate a batch of questions using OpenAI API."""

    if context_text:
        context_section = CONTEXT_WITH_TEXT.format(text=context_text[:8000])  # Limit context size
    else:
        context_section = CONTEXT_WITHOUT_TEXT

    prompt = GENERATION_PROMPT.format(
        materia=materia,
        argomento=argomento,
        count=count,
        context_section=context_section,
    )

    messages = [
        {"role": "system", "content": "Sei un generatore di domande mediche per il concorso SSM. Rispondi sempre con JSON valido."},
        {"role": "user", "content": prompt},
    ]

    response = await call_openai_api(client, messages)
    questions = parse_json_response(response)

    return questions


async def verify_questions(
    client: httpx.AsyncClient,
    questions: list[dict],
) -> list[dict]:
    """Verify questions using OpenAI self-check."""
    if not questions:
        return []

    prompt = VERIFICATION_PROMPT.format(
        questions_json=json.dumps(questions, ensure_ascii=False, indent=2)
    )

    messages = [
        {"role": "system", "content": "Sei un revisore esperto di domande mediche. Rispondi sempre con JSON valido."},
        {"role": "user", "content": prompt},
    ]

    response = await call_openai_api(client, messages)
    verifications = parse_json_response(response)

    return verifications


def filter_valid_questions(
    questions: list[dict],
    verifications: list[dict],
) -> list[dict]:
    """Filter out questions that failed verification."""
    valid_questions = []

    # Create a map of verification results by index
    verification_map = {}
    for v in verifications:
        idx = v.get("domanda_index", -1)
        verification_map[idx] = v

    for i, question in enumerate(questions):
        verification = verification_map.get(i, verification_map.get(i + 1))  # Handle 0 or 1-based indexing

        if verification is None or verification.get("is_valid", True):
            valid_questions.append(question)
        else:
            issues = verification.get("issues", [])
            print(f"  [ESCLUSA] Domanda {i + 1}: {', '.join(issues)}")

    return valid_questions


def validate_question_structure(question: dict) -> bool:
    """Validate that a question has the correct structure."""
    required_fields = ["materia", "domanda", "risposte", "risposta_corretta_text", "commento"]

    for field in required_fields:
        if field not in question:
            return False

    risposte = question.get("risposte", [])
    if len(risposte) != 5:
        return False

    correct_count = sum(1 for r in risposte if r.get("isCorrect", False))
    if correct_count != 1:
        return False

    return True


def save_jsonl(questions: list[dict], output_path: str) -> int:
    """Save questions to JSONL format."""
    path = Path(output_path)

    valid_count = 0
    with path.open("w", encoding="utf-8") as f:
        for question in questions:
            # Ensure required fields with defaults
            question.setdefault("has_image", False)
            question.setdefault("image_src", None)
            question.setdefault("argomenti", question.get("materia", ""))

            if validate_question_structure(question):
                f.write(json.dumps(question, ensure_ascii=False) + "\n")
                valid_count += 1
            else:
                print(f"  [SKIP] Struttura invalida: {question.get('domanda', 'N/A')[:50]}...")

    return valid_count


async def run_pipeline(
    input_file: Optional[str],
    materia: str,
    argomento: Optional[str],
    count: int,
    output_file: str,
    skip_verification: bool = False,
) -> None:
    """Run the complete question generation pipeline."""

    if not config.OPENAI_API_KEY:
        print("ERRORE: OPENAI_API_KEY non configurata.")
        print("Imposta la variabile d'ambiente o crea un file .env")
        sys.exit(1)

    # Extract context text if input file provided
    context_text = None
    if input_file:
        print(f"Estrazione testo da: {input_file}")
        context_text = extract_text(input_file)
        print(f"  Estratti {len(context_text)} caratteri")

    # Use materia as argomento if not specified
    if not argomento:
        argomento = materia

    print(f"\nGenerazione di {count} domande...")
    print(f"  Materia: {materia}")
    print(f"  Argomento: {argomento}")

    all_questions = []

    async with httpx.AsyncClient() as client:
        # Generate questions in batches
        remaining = count
        batch_num = 0

        while remaining > 0:
            batch_size = min(remaining, config.DEFAULT_BATCH_SIZE)
            batch_num += 1

            print(f"\n  Batch {batch_num}: generazione {batch_size} domande...")

            try:
                questions = await generate_questions_batch(
                    client,
                    materia=materia,
                    argomento=argomento,
                    count=batch_size,
                    context_text=context_text,
                )
                print(f"    Generate {len(questions)} domande")
                all_questions.extend(questions)
            except Exception as e:
                print(f"    ERRORE: {e}")

            remaining -= batch_size

            if remaining > 0:
                await asyncio.sleep(config.RATE_LIMIT_DELAY_SECONDS)

        # Verify questions
        if not skip_verification and all_questions:
            print(f"\nVerifica delle {len(all_questions)} domande generate...")

            try:
                verifications = await verify_questions(client, all_questions)
                all_questions = filter_valid_questions(all_questions, verifications)
                print(f"  Domande valide dopo verifica: {len(all_questions)}")
            except Exception as e:
                print(f"  ATTENZIONE: Verifica fallita ({e}), mantengo tutte le domande")

    # Save to JSONL
    print(f"\nSalvataggio in: {output_file}")
    saved_count = save_jsonl(all_questions, output_file)
    print(f"  Salvate {saved_count} domande valide")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"COMPLETATO")
    print(f"  Domande richieste: {count}")
    print(f"  Domande generate: {len(all_questions)}")
    print(f"  Domande salvate: {saved_count}")
    print(f"  Output: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera domande SSM usando OpenAI GPT-4o-mini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python -m ssm.generator.pipeline --input medicina.pdf --materia "Cardiologia" --count 20
  python -m ssm.generator.pipeline --materia "Pediatria" --argomento "Malattie esantematiche" --count 15
  python -m ssm.generator.pipeline --input capitolo.txt --materia "Gastroenterologia" --count 10
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="File PDF o TXT da cui estrarre il contesto (opzionale)"
    )
    parser.add_argument(
        "--materia", "-m",
        type=str,
        required=True,
        help="Materia delle domande (es. Cardiologia, Pediatria)"
    )
    parser.add_argument(
        "--argomento", "-a",
        type=str,
        default=None,
        help="Argomento specifico (opzionale, default: materia)"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=config.DEFAULT_COUNT,
        help=f"Numero di domande da generare (default: {config.DEFAULT_COUNT})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=config.DEFAULT_OUTPUT_FILE,
        help=f"File output JSONL (default: {config.DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Salta la fase di verifica delle domande"
    )

    args = parser.parse_args()

    asyncio.run(run_pipeline(
        input_file=args.input,
        materia=args.materia,
        argomento=args.argomento,
        count=args.count,
        output_file=args.output,
        skip_verification=args.skip_verification,
    ))


if __name__ == "__main__":
    main()
