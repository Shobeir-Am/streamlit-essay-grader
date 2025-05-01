# -*- coding: utf-8 -*-
"""
Created on Thu May  1 14:20:34 2025

@author: amirn
"""
# app.py
import io
from typing import List

import openai
import pandas as pd
import streamlit as st
from grader import grade_files, read_docx

# ───────────────────────── sidebar: parameters ────────────────────────────
st.sidebar.header("Grading options")

api_key = st.sidebar.text_input(
    "OpenAI API key",
    value=st.secrets.get("OPENAI_API_KEY", ""),
    type="password",
    help="Key is stored only in this session or Streamlit Secrets.",
)
openai.api_key = api_key

model = st.sidebar.selectbox(
    "Model", [  "o4-mini",          
        "o3",               
        "o1",               
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4o-32k",
        "gpt-4-turbo",
        "gpt-3.5-turbo-0125",], index=0
)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.6, 0.05)
delay = st.sidebar.number_input(
    "Delay between calls (sec)", min_value=0.0, value=1.0, step=0.5
)
output_basename = st.sidebar.text_input("Excel base name", "feedback")

st.sidebar.markdown("---")

# ────────────────────────── main upload area ─────────────────────────────
st.title("📄 Essay Grading Tool (ChatGPT)")

uploaded_files = st.file_uploader(
    "Upload DOCX or PDF essays",
    type=["docx", "pdf"],
    accept_multiple_files=True,
)

rubric_file = st.file_uploader("Upload rubric (DOCX)", type=["docx"])
system_file = st.file_uploader("Upload system prompt (DOCX)", type=["docx"])

run_btn = st.button(
    "🚀 Run grading",
    disabled=not (uploaded_files and rubric_file and system_file and api_key),
)

# ──────────────────────────── run grading ────────────────────────────────
if run_btn:
    with st.spinner("Parsing rubric and prompt …"):
        rubric_text = read_docx(rubric_file)
        system_prompt = read_docx(system_file)

    st.info(f"Processing **{len(uploaded_files)}** essays …")
    progress = st.progress(0)
    df_out = grade_files(
        uploads=uploaded_files,
        rubric_text=rubric_text,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        delay=delay,
    )
    progress.progress(100)

    st.success("✅ Grading complete")
    st.dataframe(df_out, use_container_width=True)

    # Excel download
    buffer = io.BytesIO()
    df_out.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label="📥 Download Excel",
        data=buffer,
        file_name=f"{output_basename}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
    
    