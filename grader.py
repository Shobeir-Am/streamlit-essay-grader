# -*- coding: utf-8 -*-
"""
Created on March 17 14:19:41 2025

@author: amirn
"""
# grader.py
from __future__ import annotations

import json, re, time
from pathlib import Path
from typing import IO, Any, Iterable, Union

import openai
import pandas as pd
import pdfplumber
from docx import Document as _DocxDocument

FileLike = Union[str, Path, IO[bytes], Any]  # Streamlit UploadedFile fits here

# ───────────────────────── helpers ──────────────────────────
def read_docx(src: FileLike) -> str:
    doc = _DocxDocument(src)
    return "\n".join(p.text for p in doc.paragraphs)

def read_pdf(src: FileLike) -> str:
    with pdfplumber.open(src) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

def extract_json(raw: str) -> dict | None:
    try:
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
    except Exception:
        return None

# ───────────────────── main orchestrator ────────────────────
def grade_files(
    uploads: Iterable[FileLike],
    rubric_text: str,
    system_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.6,
    delay: float = 1.0,
) -> pd.DataFrame:
    results: list[dict[str, str]] = []

    for f in uploads:
        fname = Path(getattr(f, "name", str(f))).name
        ext = Path(fname).suffix.lower()

        essay = read_docx(f) if ext == ".docx" else read_pdf(f) if ext == ".pdf" else None
        if essay is None:
            results.append(
                dict(file_name=fname, feedback=f"Unsupported file type {ext}", grade="error")
            )
            continue

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{rubric_text}\n\nEssay:\n{essay}"},
        ]

        try:
            # Build kwargs — omit temperature for o-series models
            kwargs = dict(model=model, messages=messages)
            if not model.startswith("o"):
                kwargs["temperature"] = temperature

            resp = openai.chat.completions.create(**kwargs)
            raw = resp.choices[0].message.content.strip()
            parsed = extract_json(raw)

            feedback = parsed.get("feedback") if parsed else raw
            grade    = parsed.get("grade")    if parsed else "not found"
        except Exception as exc:
            feedback, grade = f"ERROR: {exc}", "error"

        results.append(dict(file_name=fname, feedback=feedback, grade=grade))
        time.sleep(delay)

    return pd.DataFrame(results)
