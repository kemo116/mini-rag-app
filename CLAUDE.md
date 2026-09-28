# mini-rag — Guided Learning Walkthrough

## Goal
Kareem finished a course that built this project (a minimal RAG / question-answering app) across 12 branches.
Much of it was followed without fully understanding it. The goal now is to **understand every file, every line,
every config, and every tool**, branch by branch, while Kareem takes notes.

## How the walkthrough works
1. **Branch `tut-001`**: explain every file line by line.
2. **Each later branch `tut-00N`**: explain only what is *new or changed* compared to the previous branch
   (use `git diff tut-00(N-1)..tut-00N --stat`, then read the changed files), line by line.
3. For every new tool or concept (e.g. nginx, Docker, Postgres, pgvector, Qdrant, Prometheus, Grafana),
   explain **what it is, why the project needs it, and how it fits** with the rest.
4. Flag bugs, bad practices, and security issues found along the way (list below).
5. After `tut-012`: discuss the organization repo https://github.com/my-rag-org/mini-rag (git remote `neworg`).

## Rules for Claude during the walkthrough
- Read-only: do **not** modify, commit to, or check out the tutorial branches. Use `git show <branch>:<path>`
  and `git diff` to read them.
- Write explanations in a note-friendly format: headings per file, short tables, "why it matters" lines.
- One branch per session/turn unless asked otherwise; end each branch with a short recap.
- Update the progress tracker and glossary below after each branch.

## Repo facts
- Branches: `main`, `tut-001` … `tut-012` (current working branch: `tut-012`).
- Remotes: `origin` = github.com/kemo116/mini-rag-app, `neworg` = github.com/my-rag-org/mini-rag.
- Environment: Miniconda on Windows.

## Progress tracker
- [x] tut-001 — project skeleton (env template, .gitignore, README, requirements, assets/, license)
- [ ] tut-002
- [ ] tut-003
- [ ] tut-004
- [ ] tut-005
- [ ] tut-006
- [ ] tut-007
- [ ] tut-008
- [ ] tut-009
- [ ] tut-010
- [ ] tut-011
- [ ] tut-012
- [ ] my-rag-org/mini-rag discussion

## Glossary (tools & concepts covered so far)
| Term | One-line meaning | First seen |
|---|---|---|
| RAG | Retrieval-Augmented Generation: fetch relevant docs, then have an LLM answer using them | tut-001 |
| Conda env | Isolated Python install + packages per project | tut-001 |
| Environment variables / `.env` | Config & secrets kept outside the code | tut-001 |
| `.gitignore` | Patterns of files git must never track | tut-001 |
| FastAPI | Python web framework for building HTTP APIs | tut-001 |
| Uvicorn / ASGI | The server that runs a FastAPI app; ASGI is the async Python server↔app interface | tut-001 |
| python-multipart | Parses form data / file uploads for FastAPI | tut-001 |
| `.gitkeep` | Empty placeholder so git tracks an otherwise-empty folder | tut-001 |
| Apache 2.0 | Permissive open-source license with a patent grant | tut-001 |

## Issues found
- **tut-001 `.env.example` contains a real-looking OpenAI API key** and it is pushed to GitHub history.
  Action: revoke it on the OpenAI dashboard; `.env.example` should only hold placeholders.
- tut-001 README: `cp .env.example` is missing the destination (`cp .env.example .env`).
- tut-001 README: `conda create -n mini-rag` doesn't pin Python (`conda create -n mini-rag python=3.x`).
