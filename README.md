# ResumeX - Smart Resume Screening & Candidate Ranking

A dark, futuristic academic prototype for an IBM/GenAI project.

## What it does

- Accepts multiple PDF, DOCX and TXT resumes
- Accepts a job description
- Extracts resume text
- Detects relevant skills
- Calculates TF-IDF/NLP relevance
- Compares candidate skills with job requirements
- Estimates experience match
- Produces a transparent weighted ranking
- Includes a responsive dark UI with a falling-star animation

## Scoring model

The current demo uses:

- 45% resume/job-description relevance
- 35% required skill coverage
- 20% experience match

This is intentionally transparent so it is easy to explain during a project demo/viva.

## Run locally

### 1. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start

```bash
python app.py
```

Open:

http://127.0.0.1:5000

## Suggested IBM presentation angle

The base system is an NLP ranking engine. For a stronger GenAI version, add a RAG/LLM layer that explains *why* each candidate ranked where they did, while keeping the numerical score deterministic and auditable.

Example explanation:

> Candidate A ranked #1 because 8/9 required skills were detected and the resume had strong semantic overlap with the role description.

## Important academic note

This is a prototype, not a production hiring system. Real hiring systems require bias testing, privacy controls, human review, explainability, and careful validation before being used for employment decisions.

## GenAI + RAG upgrade

The upgraded version adds a lightweight Retrieval-Augmented Generation pipeline:

1. Resume text is split into chunks.
2. TF-IDF retrieves the resume chunks most relevant to the job description.
3. The retrieved evidence is passed to the explanation layer.
4. If `OLLAMA_MODEL` is configured and Ollama is running locally, a local LLM writes the explanation.
5. If no LLM is available, the app falls back to a deterministic evidence-based explanation, so the demo still works offline.

### Optional: enable a real local LLM

Install Ollama, then pull a model such as `llama3.2`:

```bash
ollama pull llama3.2
```

Windows PowerShell:

```powershell
$env:OLLAMA_MODEL="llama3.2"
python app.py
```

Command Prompt:

```cmd
set OLLAMA_MODEL=llama3.2
python app.py
```

The UI will show **LOCAL LLM + RAG** when this mode is active.

### Architecture

```text
                 ┌─────────────────────┐
                 │    Job Description  │
                 └──────────┬──────────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────────┐
│ PDF/DOCX/TXT │────►│ Resume Extraction│
└──────────────┘     └────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Skill + Experience│
                    │    Extraction     │
                    └─────────┬─────────┘
                              │
                ┌─────────────▼─────────────┐
                │ TF-IDF Ranking + Retrieval│
                └─────────────┬─────────────┘
                              │
                    top relevant evidence
                              │
                ┌─────────────▼─────────────┐
                │   Local LLM (optional)    │
                │        + RAG prompt       │
                └─────────────┬─────────────┘
                              │
                              ▼
                Explainable Candidate Ranking
```

### Viva explanation

**Why RAG?** Instead of asking an LLM to invent an explanation from an entire resume, the system retrieves the most relevant resume sections for the job first. The explanation is therefore grounded in candidate evidence.

**Why keep the numeric score deterministic?** The score remains auditable: 45% semantic relevance, 35% skill coverage, and 20% experience match. The LLM explains the result rather than secretly changing the ranking.

**Why local LLM?** It allows a demo without sending resumes to an external API and is useful for an academic privacy demonstration.


## Vercel deployment

This project is configured for Vercel's Python/Flask runtime. Static assets are in `public/static/`, and the Flask entry point remains `app.py`. The deployment is designed for the serverless request payload limit, so resume uploads are limited to 4 MB per request.

The optional Ollama integration is for local development only. A Vercel deployment cannot reach an Ollama server running on your personal PC. For cloud GenAI, connect the explanation layer to a hosted model API and store the API key in Vercel Environment Variables.

## Local Flask static files

The Flask app is configured to serve the Vercel-compatible `public/static` directory
through `/static`, so the same project works both locally and on Vercel.
