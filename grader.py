# -*- coding: utf-8 -*-
"""
Created on March 17 14:19:41 2025

@author: amirn
"""

# grader.py
from pathlib import Path
import time
import json
import re
import openai
import pandas as pd
from docx import Document
import pdfplumber


# ---------- helpers ----------
def read_docx(file_path: Path) -> str:
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def read_pdf(file_path: Path) -> str:
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_json_from_response(raw: str) -> dict | None:
    """Pull a JSON object out of an LLM reply (best-effort)."""
    try:
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return None


# ---------- main routine ----------
def grade_files(
    files: list[Path],
    rubric_text: str,
    system_prompt: str,
    model: str,
    temperature: float,
    delay: float,
) -> pd.DataFrame:
    """
    Parameters
    ----------
    files : list of Path objects (PDF or DOCX)
    rubric_text : string with rubric
    system_prompt : string (system role content)
    model, temperature, delay : OpenAI parameters

    Returns
    -------
    pd.DataFrame  with columns  file_name | feedback | grade
    """
    results = []
    for fp in files:
        # --- read essay ----------------------------------------------------
        if fp.suffix.lower() == ".docx":
            essay_text = read_docx(fp)
        elif fp.suffix.lower() == ".pdf":
            essay_text = read_pdf(fp)
        else:
            raise ValueError(f"Unsupported file type: {fp.name}")

        analysis_request = f"{rubric_text}\n\nEssay:\n{essay_text}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_request},
        ]

        # --- call OpenAI ----------------------------------------------------
        try:
            response = openai.ChatCompletion.create(
                model=model, messages=messages, temperature=temperature
            )
            raw_reply = response.choices[0].message.content.strip()
            parsed = extract_json_from_response(raw_reply)
            feedback = parsed.get("feedback") if parsed else raw_reply
            grade = parsed.get("grade") if parsed else "not found"
        except Exception as exc:
            feedback = f"ERROR: {exc}"
            grade = "error"

        results.append({"file_name": fp.name, "feedback": feedback, "grade": grade})
        time.sleep(delay)

    return pd.DataFrame(results)
