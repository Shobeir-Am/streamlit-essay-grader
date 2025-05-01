# -*- coding: utf-8 -*-
"""
Created on March 17 14:19:41 2025

@author: amirn
"""


# grader.py
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import IO, Any, Iterable, Union

import openai
import pandas as pd
import pdfplumber
from docx import Document as _DocxDocument


# ───────────────────────────────── helpers ──────────────────────────────────
FileLike = Union[str, Path, IO[bytes], Any]  # accepts UploadedFile too


def read_docx(src: FileLike) -> str:
    """
    Extract full text from a .docx.

    `src` can be:
      • a filesystem path (str | Path)
      • a file-like object (BytesIO, SpooledTemporaryFile, Streamlit UploadedFile)
    """
    doc = _DocxDocument(src)
    return "\n".join(p.text for p in doc.paragraphs)


def read_pdf(src: FileLike) -> str:
    """Extract text from every page of a (text-based) PDF."""
    with pdfplumber.open(src) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def extract_json_from_response(raw: str) -> dict | None:
    """Best-effort pull of a JSON object out of an LLM reply."""
    try:
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        start, end = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return None


# ───────────────────────────── main orchestrator ────────────────────────────
def grade_files(
    uploads: Iterable[FileLike],
    rubric_text: str,
    system_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.6,
    delay: float = 1.0,
) -> pd.DataFrame:
    """
    Parameters
    ----------
    uploads  : iterable of Path or UploadedFile or BytesIO
    rubric_text, system_prompt : strings already decoded
    model, temperature, delay  : OpenAI params

    Returns
    -------
    DataFrame with columns  file_name | feedback | grade
    """
    results: list[dict[str, str]] = []

    for f in uploads:
        # Identify file name (works for Path and UploadedFile)
        fname = Path(f.name).name if hasattr(f, "name") else str(f)

        # Read essay
        ext = Path(fname).suffix.lower()
        if ext == ".docx":
            essay_text = read_docx(f)
        elif ext == ".pdf":
            essay_text = read_pdf(f)
        else:
            results.append(
                dict(
                    file_name=fname,
                    feedback=f"ERROR: unsupported file type '{ext}'",
                    grade="error",
                )
            )
            continue

        # Compose messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"{rubric_text}\n\nEssay:\n{essay_text}",
            },
        ]

        # Call OpenAI
        try:
            # NEW v1-style call 
            resp = openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            raw = resp.choices[0].message.content.strip()
            parsed = extract_json_from_response(raw)
            feedback = parsed.get("feedback") if parsed else raw
            grade    = parsed.get("grade")    if parsed else "not found"
        except Exception as exc:
            feedback, grade = f"ERROR: {exc}", "error"

        results.append(
            dict(file_name=fname, feedback=feedback, grade=grade)
        )
        time.sleep(delay)

    return pd.DataFrame(results)