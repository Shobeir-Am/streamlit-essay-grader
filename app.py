# -*- coding: utf-8 -*-
"""
Created on Thu May  1 14:20:34 2025

@author: amirn
"""

# app.py
import io
from pathlib import Path

import pandas as pd
import streamlit as st
import openai

from grader import grade_files

# ------------ sidebar: parameters ----------------
st.sidebar.header("Grading options")

api_key = st.sidebar.text_input(
    "OpenAI API key",
    type="password",
    value=st.secrets.get("OPENAI_API_KEY", ""),
)
openai.api_key = api_key

model = st.sidebar.selectbox(
    "Model", ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"], index=1
)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.6, 0.05)
delay = st.sidebar.number_input(
    "Delay between calls (seconds)", min_value=0.0, value=1.0, step=0.5
)
output_basename = st.sidebar.text_input("Excel base name", "feedback")

st.sidebar.divider()

# ------------ main layout ----------------
st.title("📄 Essay Grading Tool (ChatGPT)")

uploaded_files = st.file_uploader(
    "Upload DOCX or PDF essays", type=["docx", "pdf"], accept_multiple_files=True
)

rubric_file = st.file_uploader("Upload rubric (DOCX)", type=["docx"])
system_file = st.file_uploader("Upload system prompt (DOCX)", type=["docx"])

run_btn = st.button("Run grading", disabled=not (uploaded_files and rubric_file and system_file and api_key))

# ------------ run grading ----------------
if run_btn:
    # read rubric & system prompt
    from grader import read_docx  # re-use helper
    rubric_text = read_docx(Path(rubric_file.name)) if rubric_file else ""
    system_prompt = read_docx(Path(system_file.name)) if system_file else ""

    # temporarily save uploaded essays to disk-like Path objects
    tmp_paths = []
    for uf in uploaded_files:
        tmp_path = Path(st.experimental_get_query_params().get("session", [""])[0]) / uf.name  # unique folder per session
        with open(tmp_path, "wb") as f:
            f.write(uf.getbuffer())
        tmp_paths.append(tmp_path)

    # progress bar
    progress = st.progress(0, text="Grading essays…")
    df_out = grade_files(
        tmp_paths, rubric_text, system_prompt, model, temperature, delay
    )
    progress.progress(100, text="Done!")

    st.subheader("Results")
    st.dataframe(df_out, use_container_width=True)

    # prepare Excel in-memory
    towrite = io.BytesIO()
    df_out.to_excel(towrite, index=False)
    towrite.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=towrite,
        file_name=f"{output_basename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
