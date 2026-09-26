# Mini-RAG: Issues I Faced and How I Fixed Them

Stack: FastAPI, PostgreSQL + pgvector, Docker Compose, Nginx, Prometheus, Grafana Cloud.
This file covers the monitoring and pipeline problems from branch `tut-011`. Earlier branches are in the timeline at the bottom.

---

## The big picture (say this first when explaining)

I added Prometheus + Grafana monitoring to the FastAPI app. The dashboard stayed empty, and getting it to work exposed
five separate problems in a chain. Each one had to be fixed before the next one became visible:

```
App code ──► /metrics ──► Prometheus ──► remote_write ──► Grafana Cloud ──► Dashboard
  (1,2,3)      (3)           (7)             (6,7)            (6)             (1)
```

---

## Monitoring issues

### 1. Dashboard panels empty: metric names did not match
- **Symptom:** the imported Grafana dashboard showed "No data" everywhere.
- **Cause:** the dashboard queries `http_requests_total` and `http_request_duration_seconds` and filters on labels `path`, `status` and `app_name`. My app exported a label called `endpoint` and had no `app_name`. The "Application Name" dropdown reads `fastapi_app_info`, which did not exist, so `$app_name` was empty.
- **Fix:** in `src/utils/metrics.py` I used the labels `method`, `path`, `status` and `app_name`. I added a `fastapi_app_info{app_name="mini-rag-app"}` gauge and used the route template (`/api/v1/nlp/{project_id}`) as `path` so labels stay small.
- **Detour worth knowing:** I first renamed everything to `fastapi_*` for the stock dashboard 18739. This was wrong, because my dashboard was a customized copy with different names. Lesson: read the dashboard JSON queries before changing the app.
- **How to explain it:** a dashboard is just saved queries. If the app doesn't export the exact metric and label names, nothing matches.

### 2. `/metrics` returned 404
- **Symptom:** Prometheus logs showed `GET /metrics 404`.
- **Cause:** in `src/main.py`, `app = FastAPI()` was created and `setup_metrics(app)` was called on it. Later the file did `app = FastAPI(lifespan=lifespan)`, which replaced the first app. The middleware and `/metrics` route were lost.
- **Fix:** call `setup_metrics(app)` after the final `app = FastAPI(lifespan=lifespan)`, and delete the first `FastAPI()`.
- **How to explain it:** I configured an object and then overwrote it with a new one.

### 3. Grafana Cloud could not see my local Prometheus
- **Symptom:** the app exported metrics, but the dashboard was still empty.
- **Cause:** the dashboard uses the Grafana Cloud datasource, and Grafana Cloud cannot reach `fastapi:8000` inside my Docker network. Nothing pushed data to it.
- **Fix:** added a `remote_write` block to `docker/prometheus/prometheus.yml` with the Grafana Cloud push URL, my username, and a token with the metrics-write scope.
- **How to explain it:** Prometheus pulls from my app, but the cloud cannot pull from my laptop. So Prometheus must push.

### 4. Choosing the right setup option in Grafana Cloud
- **Symptom:** Grafana's page offered "Via Grafana Alloy" first.
- **Fix:** I chose "From my local Prometheus server" instead, because I already run Prometheus. The token scope is a metrics-write scope, not `set:alloy-data-write`.

### 5. Token kept out of git
- **Fix:** the token lives in `docker/prometheus/gc_token`, read by Prometheus through `password_file`. The file is listed in `docker/.gitignore`. `prometheus.yml` only holds the URL and username.

### 6. Prometheus could not read the token file (the longest one)
- **Symptom:** the Prometheus log repeated `unable to read file ... is a directory`.
- **Cause, layer 1:** I started the container before the token file existed. Docker created an empty **folder** with that name for the bind mount.
- **Cause, layer 2:** after I deleted the folder and created the real file (Windows and WSL both showed a 168-byte file), the container still saw a folder. Docker's file sharing for the `E:` drive (`/mnt/e`) kept a stale cache entry for that exact name.
- **Fix:** mount the whole `./prometheus` folder at `/etc/prometheus/secrets` instead of a single file, rename the token file to `gc_token` to get past the stale entry, and recreate the container.
- **How to explain it:** single-file bind mounts are fragile. If the file is missing at start, Docker makes a folder. Always create the file first, and prefer mounting a folder.

### 7. Dashboard panels that look wrong but are not bugs
- **Requests Count shows 12 everywhere:** the query is `count_over_time(...)`, which counts scrapes, not requests. A better query is `sum by (method, path) (increase(http_requests_total[24h]))`.
- **"Request In Process" shows values in the billions:** one query plots `http_requests_created`, which is a Unix timestamp.
- **Total Exceptions / 4xx panels show "No data":** they only count 404s, and I had none. Request a URL that does not exist to fill them.

---

## Pipeline issues (upload, process, index)

### 8. `NO_FILE_FOUND_WITH_THIS_ID` after uploading
- **Symptom:** upload returned `file_id: "2"`, but `/process` with that id said the file was not found.
- **Cause:** upload returns the database id (`asset_id`). `/process` looked up by `asset_name`, which is the generated filename.
- **Fix:** in `src/models/AssetModel.py`, `get_asset_record` tries the name first. If that fails and the value is all digits, it looks up by `asset_id` within the same project.

### 9. Internal Server Error on `/process`
- **Cause 1:** a typo in `src/controllers/ProcessController.py`: `return none` instead of `return None`. This raised a `NameError` whenever the file was missing on disk.
- **Cause 2:** uploaded files are saved inside the container at `assets/files`, and the `fastapi` service had no volume for that folder. Every `docker compose up --build` replaced the container and deleted the files, while the database rows stayed. So ids from before a rebuild point to files that no longer exist.
- **Fix:** fixed the typo. The volume is still to do (see open items).

### 10. `/process` returned "success" with 0 chunks
- **Cause:** I sent an old filename from before a rebuild. The file was gone, the error was only logged, and the endpoint still returned success.
- **Fix:** upload again and use the new `file_id`. Making `/process` return an error when nothing loads is still to do.

---

## Open items

1. Add a volume `fastapi_files:/app/assets/files` to the `fastapi` service so uploads survive rebuilds.
2. Make `/process` return an error when no file was loaded.
3. Optionally fix the dashboard's Requests Count query (see 7).
4. Before committing, check that `docker/prometheus/prometheus.yml` has no real token in it.
5. Add `.gitignore` entries for `docker/prometheus/gc_token` (done) and keep the old `grafana_cloud_api_key` entry.

---

## Quick debugging habits that solved these

- Read the logs first: `sudo docker logs <container> --since 5m`.
- Filter the noise: `| grep -iE "error|failed|401|403"`.
- Check each link in the chain in order: app `/metrics` → Prometheus targets → remote_write log → Grafana Explore → dashboard.
- What the container sees can differ from what the host sees: `docker exec <container> ls -la <path>`.
- Use Grafana **Explore** with `up` and `http_requests_total` to test the data before blaming the dashboard.

---

## Timeline by branch (fill in the issues you remember)

The commit messages below are all I know about earlier branches. Add the problem and fix for each you want to explain.

| Branch | What was built (from commits) | Issues I faced and how I fixed them |
|---|---|---|
| tut-001 – tut-002 | boilerplate, requirements, `.gitignore`, WSL branch | _fill in_ |
| tut-003 – tut-004 | base, controllers, file upload | _fill in_ |
| tut-005 – tut-006 | process requests, MongoDB, chunking, first Docker service | _fill in_ |
| tut-007 | indexes for project and chunks, assets for multiple files | _fill in_ |
| tut-008 | OpenAI/Cohere factories, Qdrant vector DB, "fixing errors and running the project" | _fill in_ |
| tut-009 | Gemini and Groq providers, RAG answer endpoint | _fill in_ |
| tut-010 | Arabic and English answers, response-language footer, Ollama | _fill in_ |
| tut-011 | pgvector (replacing Mongo/Qdrant), Nginx, Prometheus, Grafana monitoring | everything above |
