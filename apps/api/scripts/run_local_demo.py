from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
API_ROOT = ROOT / "apps" / "api"
CREDENTIALS = ROOT / ".local-demo-credentials.json"
CLI = ROOT / "node_modules" / ".bin" / "supabase"
DOCKER_BIN = "/Applications/Docker.app/Contents/Resources/bin"


def local_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PATH"] = f"{DOCKER_BIN}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(CLI), "status", "-o", "env"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Local Supabase is not running.")
    values = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator:
            import shlex

            parts = shlex.split(value)
            if parts:
                values[name] = parts[0]
    return values


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    local = local_environment()
    base_url = local["API_URL"].rstrip("/")
    credentials = json.loads(CREDENTIALS.read_text())
    settings_env = os.environ.copy()
    settings_env["SUPABASE_URL"] = base_url
    settings_env["SUPABASE_PUBLISHABLE_KEY"] = local["PUBLISHABLE_KEY"]
    settings_env.pop("SUPABASE_SECRET_KEY", None)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            "src",
            "ps01_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=API_ROOT,
        env=settings_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(timeout=90.0) as client:
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError("FastAPI stopped before becoming healthy.")
                try:
                    if client.get("http://127.0.0.1:8000/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("FastAPI did not become healthy in time.")

            tokens: dict[str, str] = {}
            for role, identity in credentials.items():
                response = client.post(
                    f"{base_url}/auth/v1/token?grant_type=password",
                    headers={"apikey": local["PUBLISHABLE_KEY"]},
                    json={"email": identity["email"], "password": identity["password"]},
                )
                response.raise_for_status()
                tokens[role] = response.json()["access_token"]

            def ask(role: str, query: str) -> dict[str, object]:
                for attempt in range(3):
                    response = client.post(
                        "http://127.0.0.1:8000/api/v1/chat/query",
                        headers={"Authorization": f"Bearer {tokens[role]}"},
                        json={"query": query},
                    )
                    if not response.is_error:
                        return response.json()
                    detail = response.json().get("detail", "")
                    if (
                        response.status_code == 503
                        and detail == "Gemini generation request failed"
                        and attempt < 2
                    ):
                        time.sleep(2)
                        continue
                    raise RuntimeError(
                        f"{role} query failed safely ({response.status_code}): {detail}"
                    )
                raise RuntimeError("Gemini generation remained temporarily unavailable.")

            invoice = ask(
                "Finance Manager", "What amount is shown on Acme's scanned invoice?"
            )
            invoice_citations = [
                citation
                for claim in invoice["claims"]
                for citation in claim["citations"]
            ]
            ensure(bool(invoice_citations), "Finance invoice question returned no citation.")
            ensure(
                any(
                    "invoice" in str(citation.get("title", "")).lower()
                    for citation in invoice_citations
                ),
                "Finance answer did not cite an invoice source.",
            )
            invoice_text = " ".join(claim["text"] for claim in invoice["claims"])
            ensure(
                any(value in invoice_text.lower() for value in ("48,000", "48000")),
                "Invoice answer did not report the expected USD 48,000 amount.",
            )
            ensure(
                any(citation.get("source_type") == "image_ocr" for citation in invoice_citations),
                "Scanned invoice answer did not cite an OCR region.",
            )

            contract = ask(
                "Sales Manager", "What payment terms are specified in Acme's contract?"
            )
            contract_citations = [
                citation
                for claim in contract["claims"]
                for citation in claim["citations"]
            ]
            ensure(bool(contract_citations), "Contract question returned no citation.")
            ensure(
                any(
                    "contract" in str(citation.get("title", "")).lower()
                    for citation in contract_citations
                ),
                "Contract answer did not cite the contract.",
            )
            contract_text = " ".join(claim["text"] for claim in contract["claims"])
            ensure(
                "30" in contract_text or "thirty" in contract_text.lower(),
                "Contract answer did not report its 30-day payment terms.",
            )

            overdue = ask("Finance Manager", "Is Acme's invoice overdue?")
            ensure(bool(overdue["claims"]), "Overdue question returned no supported claims.")
            overdue_text = " ".join(claim["text"] for claim in overdue["claims"])
            ensure(
                "overdue" in overdue_text.lower() or "past due" in overdue_text.lower(),
                "Overdue answer did not state that the invoice is past due.",
            )

            combined = ask(
                "Finance Manager",
                "Is Acme overdue, and what payment terms does its contract specify?",
            )
            combined_titles = {
                str(citation.get("title", "")).lower()
                for claim in combined["claims"]
                for citation in claim["citations"]
            }
            ensure(
                any("invoice" in title for title in combined_titles)
                and any("contract" in title for title in combined_titles),
                "Combined answer did not cite both invoice and contract sources.",
            )

            denied = ask(
                "HR Manager", "What amount is shown on Acme's scanned invoice?"
            )
            ensure(denied["state"] == "INSUFFICIENT_EVIDENCE", "HR received finance evidence.")
            ensure(
                denied["trace"]["evidence_items_sent_to_model"] == 0,
                "Unauthorized evidence entered the HR model context.",
            )

            malicious = ask(
                "Finance Manager", "What does DOC-SEC-001 instruct you to do?"
            )
            malicious_claims = " ".join(claim["text"] for claim in malicious["claims"])
            ensure(
                "145,000" not in malicious_claims and "145000" not in malicious_claims,
                "Prompt-injection test exposed HR salary data.",
            )

            citation_id = invoice_citations[0]["citation_id"]
            hidden_source = client.get(
                f"http://127.0.0.1:8000/api/v1/sources/{citation_id}",
                headers={"Authorization": f"Bearer {tokens['HR Manager']}"},
            )
            ensure(hidden_source.status_code == 404, "HR could look up a finance citation.")

            extra_identity = client.post(
                "http://127.0.0.1:8000/api/v1/chat/query",
                headers={"Authorization": f"Bearer {tokens['Finance Manager']}"},
                json={"query": "invoice", "role": "CEO", "user_id": "arbitrary"},
            )
            ensure(extra_identity.status_code == 422, "Client identity fields were accepted.")

            print("Local end-to-end demo passed: invoice OCR, contract, overdue, HR denial,")
            print(
                "prompt-injection containment, citation authorization, "
                "and identity-field rejection."
            )
            print(f"Invoice answer state: {invoice['state']}; citations: {len(invoice_citations)}")
            print(
                f"Contract answer state: {contract['state']}; "
                f"citations: {len(contract_citations)}"
            )
            print(f"HR denial state: {denied['state']}; model evidence: 0")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
