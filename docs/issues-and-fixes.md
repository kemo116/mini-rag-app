# Mini-RAG: Issues I Faced and How I Fixed Them

Stack: FastAPI, PostgreSQL + pgvector, Docker Compose, Nginx, Prometheus, Grafana Cloud, GitHub Actions.
This file covers the monitoring/pipeline problems from `tut-011` and everything from `tut-012`: moving to a
new GitHub org, deploying to a real AWS Lightsail server, setting up CI/CD, and fixing the RAG answer
endpoint. Earlier branches are in the timeline at the bottom.

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

## Moving the repo to a new GitHub organization

### 11. New org, new repo, keeping full history
- **What I did:** created the org and an empty repo, added it as a second git remote, and pushed my branch straight to its `main`:
  ```
  git remote add neworg https://github.com/my-rag-org/mini-rag.git
  git push neworg tut-012:main
  ```
- **`git remote add` does not create anything on GitHub** — the org and repo must already exist. It only gives a short name to a URL so `git push`/`pull` know where to go.
- **Gotcha:** GitHub no longer accepts a plain password for `git push` over HTTPS. I had to generate a personal access token (Settings → Developer settings → Tokens) and paste that in as the password instead.
- **Side effect:** GitHub warned about three old MongoDB journal files (~100MB each) sitting in old commits from before the pgvector migration. Only a warning (nothing over the 100MB hard limit), but it bloats the repo. Left as an open item — fixing it means rewriting history.

---

## Setting up the Lightsail server (SSH, keys, VS Code)

### 12. Two different SSH keys, easy to mix up
- **`github_user_key`** (RSA, made first): lets **my PC log into the Lightsail server**. Used with `ssh -i` from my machine.
- **`github_deploy_key`** (ED25519, made later): lets **the server log into GitHub** to `git clone`/`pull` the private repo. Registered as a GitHub *deploy key*, scoped to one repo only.
- **How to tell them apart when confused:** `ssh -T git@github.com` tells you which one is in play — if it succeeds it prints the repo name the deploy key is scoped to (`Hi my-rag-org/mini-rag!`), not a personal account name.
- **How to explain it:** one key is "my laptop → server", the other is "server → GitHub". Never the same key.

### 13. `ssh -T git@github.com` failed: "Bad configuration option: identifyfile"
- **Cause:** a typo in `~/.ssh/config` — `identifyfile` instead of `IdentityFile`. SSH refuses to read the *entire* config file if one line is misspelled, so nothing in it took effect at all.
- **Fix:** correct the spelling. `IdentitiesOnly yes` (a real, separate option) can be added alongside it to stop SSH from trying other keys first.

### 14. `ssh -i ~/.ssh/github_user_key ...` → "Permission denied (publickey)", but the file existed
- **Cause 1:** used `ssh -l keyname` instead of `-i keyfile`. `-l` sets the *login username*, not the key — so it tried to log in as a user literally named `github_user_key`.
- **Cause 2 (later, on the server itself):** `~/.ssh/config`'s `IdentityFile` pointed at `github_user_key`, but that private key no longer existed there — it had already been copied out to `ubuntu`'s home and downloaded to my PC (correct, since that key is for *logging into* the server, not needed *on* the server). The config should have pointed at `github_deploy_key` instead (the one actually meant for the server → GitHub direction).
- **Fix:** use `-i` (not `-l`) for a key file, and make sure `IdentityFile` in a config points at the right key for that direction.

### 15. Downloaded private key landed inside the git project folder
- **Symptom:** `scp`'d `github_user_key` down from the server, but `ls ~/.ssh/github_user_key` said "No such file" on my PC.
- **Cause:** it had landed in the project root (`E:\...\mini-rag-app\github_user_key`) instead of `~/.ssh/`, because that's where my terminal happened to be pointed during the `scp`. It showed up as untracked (`??`) in `git status` — one `git add .` away from accidentally being committed and pushed.
- **Fix:** moved it to `~/.ssh/github_user_key`, `chmod 600` it, confirmed it was never tracked (`git check-ignore` / `git status`).
- **How to explain it:** always check *where* a downloaded credential landed before trusting it's safe — a git repo is not a safe place for keys "just for now".

### 16. VS Code Remote-SSH host didn't show up in the picker
- **Cause:** wrote the SSH config with Notepad (`notepad ~/.ssh/config`). Notepad silently saved it as `config.txt`, since I didn't quote the filename in its Save dialog. VS Code's Remote-SSH extension looks for a file named exactly `config`, so it never saw the new host.
- **Fix:** `mv ~/.ssh/config.txt ~/.ssh/config`, then reload/reopen the host picker.

### 17. `vscode.dev` is not the server, and not local either
- **Confusion:** opened `vscode.dev/github/my-rag-org/mini-rag` expecting to edit files on the Lightsail server.
- **What it actually is:** a browser-only editor that reads/writes straight to the **GitHub repo** via its API — a third place, separate from both my PC and the server. Edits there become commits; they don't touch the server until a `git pull` there.
- **Near-miss:** while poking around in it, real `.env` files with live secrets (`.env.app`, `.env.postgres`, etc.) showed up staged for commit (marked "A" in the Source Control panel). Almost pushed real credentials to GitHub. Caught it before committing.
- **How to explain it:** "connected to a repo" in an editor does not mean "connected to a server". Check the URL/window title before trusting where your edits are going.
- **Fix for the real thing (Remote-SSH):** installed the *Remote - SSH* VS Code extension, pointed its config at `github_user_key` (the laptop → server key, from issue 14), and connected — window title shows the server's IP, terminal commands run for real on the server, no GitHub round-trip needed to see edits.

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

- **Recurred on the new server (issue 9's file-loss problem, not a new bug):** first `docker compose up --build` on Lightsail also lost uploaded files on rebuild, same root cause as issue 9. Confirms the `fastapi_files` volume open item is worth doing before it bites again.

---

## Setting up monitoring on the new server: `docker-compose.yml`/`.env` mistakes

### 18. `postgres-exporter`: `connect: connection refused` to `pgvector:5433`
- **Cause:** `docker-compose.yml` maps `"5433:5432"` for `pgvector` — port 5433 is only the **host-facing** port (what my PC or `psql` from outside Docker would use). *Inside* the Docker network, other containers must always use the container's real port, `5432`. `.env.postgres.exporter`'s `DATA_SOURCE_URI` was wrongly set to `pgvector:5433/...`.
- **Fix:** changed it to `pgvector:5432/...`.
- **How to explain it:** a `"host:container"` port mapping only rewrites the *host* side. Container-to-container traffic never goes through it.

### 19. Typo in the database name: `posgres` vs `postgres`
- **Found alongside issue 18:** `DATA_SOURCE_URI=pgvector:5433/posgres?...` — missing a `t`. Had to check `POSTGRES_DB` in `.env.postgres` to confirm the real database name and match it exactly.

### 20. `gc_token` missing on the new server — expected, not a bug
- **Symptom:** Prometheus on Lightsail immediately failed with the same `gc_token: no such file or directory` error from issue 6.
- **Cause:** `gc_token` is (correctly) gitignored, so it simply doesn't exist on a fresh clone/server. It has to be created fresh on every new machine.
- **Fix:** generated a new Grafana Cloud token (old ones can't be viewed again, only revoked) and wrote it to `docker/prometheus/gc_token` on the new server.
- **Lesson for next time:** any gitignored secret file needs its own "first-time setup" step documented per machine — it will *always* look like a bug the first time on a new server.

---

## The `postgres-exporter` password mystery (the long one)

This took the longest because every plausible cause was disproven one at a time, and my own verification method
was flawed for most of it. Worth reading end-to-end as an example of how to debug systematically instead of
guessing.

**Symptom throughout:** `postgres-exporter` logs repeated `pq: password authentication failed for user "postgres"`,
while `fastapi` connected to the same database with no problem.

1. **First (wrong) suspicion — mismatched passwords between files.** Compared `.env.postgres` and
   `.env.postgres.exporter` by eye; they "looked" the same. **Real proof needs more than eyeballing** — used
   `sha256sum` of the actual env var *inside each running container* to compare them byte-for-byte:
   ```
   sudo docker compose exec pgvector sh -c 'printf "%s" "$POSTGRES_PASSWORD" | sha256sum'
   sudo docker compose exec postgres-exporter sh -c 'printf "%s" "$DATA_SOURCE_PASSWORD" | sha256sum'
   ```
   Hashes matched exactly. Ruled out.

2. **Second suspicion — a stale Postgres data volume.** `POSTGRES_PASSWORD` only takes effect the *first* time a
   Postgres data directory is initialized; editing it later does nothing until the volume is wiped. Did a full
   `docker compose down && docker volume rm docker_pgvector && docker compose up --build` to force a real
   re-init (watched for `running bootstrap script` / `CREATE DATABASE` in the log to confirm it actually
   happened). Still failed identically. Ruled out.

3. **Third suspicion — a URI-unsafe character in the password.** `postgres-exporter` builds its DSN by gluing
   `user:password@host` into a URL string; a password containing `@ / % # ? : " '` etc. could break that gluing.
   Generated a brand-new password with `openssl rand -hex 24` (hex-only, provably URL-safe), re-synced it across
   **all three** files that needed it (`.env.postgres`, `.env.postgres.exporter`, `src/.env`/`.env.app`), wiped
   the volume again. Still failed. Ruled out.
   - **Side lesson learned here:** `docker-compose.yml`'s `fastapi` service loads `docker/env/.env.app`, which
     sets real OS environment variables inside the container. `src/.env` is a *separate*, lower-priority file
     baked into the image, read only by `pydantic_settings` as a fallback. Alembic's migration script reads
     `os.getenv(...)` directly, which only ever sees the OS env vars from `.env.app` — never `src/.env`. Editing
     the wrong one of these three files is an easy, invisible mistake, and exactly what caused `fastapi` to
     break too partway through this debugging session.

4. **Fourth suspicion — SCRAM-SHA-256 vs this exporter's driver.** Postgres 18 defaults to `scram-sha-256` auth.
   Tried forcing the whole cluster to the simpler `md5` method (`POSTGRES_HOST_AUTH_METHOD=md5` in
   `.env.postgres`, wipe + re-init, confirmed via `cat pg_hba.conf` that `md5` really was active). Still failed
   identically. Ruled out.

5. **The flaw in my own test, found here.** Every "proof the password works" I'd been running was:
   ```
   docker compose exec pgvector sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -h pgvector -U postgres -c "SELECT 1;"'
   ```
   Running this **from inside `pgvector`'s own container** can resolve `pgvector` to `127.0.0.1`, which
   `pg_hba.conf` marks `trust` — **no password check happens at all**. The test could "pass" independent of
   whether the password was actually right. **Fixed test:** run it from a totally separate, throwaway container
   on the same Docker network, so the connection genuinely crosses the bridge network the way
   `postgres-exporter` has to:
   ```
   sudo docker run --rm --network docker_backend -e PGPASSWORD='...' postgres:18 \
     psql -h pgvector -U postgres -c "SELECT 1;"
   ```
   This succeeded — **definitively** proving the password, the network path, and `md5` auth were all correct,
   and the problem was inside `postgres-exporter` itself all along.

6. **Fifth suspicion — wrong environment variable name.** Guessed the exporter might read `DATA_SOURCE_PASS`
   instead of `DATA_SOURCE_PASSWORD`. Added it. Also tried the single-string `DATA_SOURCE_NAME` form instead of
   the split `URI`/`USER`/`PASSWORD` variables, to rule out a config-parsing bug entirely. Both failed
   identically.

7. **Real cause, finally: a version-compatibility bug.** `postgres-exporter:v0.20.1`'s Go Postgres driver simply
   can't complete auth against PostgreSQL 18 — a genuinely new server version. Every *other* client tested
   (Python's `psycopg2`/`asyncpg` via `fastapi`, and standard `psql`) worked fine with the exact same
   credentials; only this one specific binary couldn't.
   - **Fix:** changed the image tag in `docker-compose.yml`:
     ```yaml
     image: quay.io/prometheuscommunity/postgres-exporter:latest   # was v0.20.1
     ```
     Recreated the container. Log immediately showed `"Semantic version changed" ... to=18.6.0` — success, no
     more auth errors.
   - **Committed this fix** (not left as a one-off manual server change) so it survives the next
     `docker compose up --build` anywhere.

- **Leftover cosmetic issue:** `docker compose ps` still showed `postgres-exporter` as `(unhealthy)` after the
  real fix. Its healthcheck (`pg_isready -U postgres`) was copy-pasted from `pgvector`'s block — but
  `postgres-exporter`'s image has no `pg_isready` at all (it's not a Postgres client), so the check can never
  succeed, regardless of whether the exporter is actually fine. Fixed by pointing the healthcheck at the
  exporter's own metrics endpoint instead (`wget --spider http://localhost:9187/metrics`).
- **Harmless noise, not a bug:** every `postgres-exporter` start logs
  `level=WARN ... msg="Error loading config" err="... postgres_exporter.yml: no such file or directory"`. This
  is just it checking for an *optional* advanced-config file that this setup doesn't use (config is done via
  `DATA_SOURCE_*` env vars instead). `WARN`, not fatal, and unrelated to auth.

**The real lesson from this whole saga:** when a fix doesn't work, don't just try the *next* guess — check
whether the *test proving the previous guess wrong* was itself valid. The same-container `psql` test looked
like solid proof for three separate wrong theories before its flaw (loopback bypassing password auth) was
caught.

---

## The Lightsail server went unreachable (VS Code, then everything)

### 21. VS Code's Remote-SSH connection kept dying
- **Symptom:** VS Code couldn't reconnect to the server, kept timing out.
- **First move:** tested with plain `ssh mini-rag-server` in Git Bash instead of trusting VS Code's own error
  message. It worked fine — proved the problem was specific to the VS Code extension (a stuck/corrupted remote
  server process), not the actual connection.
- **How to explain it:** always test the simplest tool first. VS Code's Remote-SSH is a layer on top of plain SSH
  — if plain SSH works, the bug is in that layer, not the network or the server.
- **Practical takeaway:** for quick server work, plain SSH + `nano` + `tmux` is a fully valid workflow and doesn't
  depend on VS Code at all. Docker containers run under `dockerd`, independent of any SSH/VS Code session —
  closing a terminal never stops them (as long as they were started with `-d`, or even without it, since only
  the *log stream* you're watching stops).

### 22. Then plain SSH *also* timed out
- **Symptom:** `ssh mini-rag-server` → `Connection timed out`.
- **Checked in order, to isolate client vs. server:**
  1. Lightsail console → instance showed **"Running"**, public IP matched `~/.ssh/config` exactly, firewall
     allowed port 22 from any address. Ruled out the obvious config mistakes.
  2. `Test-NetConnection -Port 22` from PowerShell — failed (`TcpTestSucceeded: False`), and even `ping` timed
     out. Consistent with either a local network block or a genuinely dead server.
  3. **The decisive test:** Lightsail's own **browser-based SSH** (via the console's "Connect" tab) — this
     routes through AWS's internal network, completely bypassing my PC and ISP. It failed too
     (`UPSTREAM_ERROR [515]`).
- **Conclusion:** if AWS's *own* infrastructure can't reach the instance, the problem isn't my PC, my network, or
  my firewall — the instance itself is hung. My best guess: it ran low on memory. A 2GB RAM instance was running
  FastAPI (with file-watching reload), Postgres, Grafana, Prometheus, Qdrant, Nginx, and two exporters
  simultaneously — likely triggered the kernel's OOM killer, which can kill `sshd` and leave the VM "Running"
  but unreachable.
- **Fix:** **Reboot** from the Lightsail console (a real infra-level restart, different from `sudo reboot`
  inside the OS — needed here since nothing could get in to run that command anyway). Came back up fine.
- **Prevention:** attached a **Static IP** afterward (free while attached to a running instance) so a future
  Stop/Start cycle won't silently change the IP in `~/.ssh/config` again.
- **How to explain it:** test from outside your own network before assuming it's the server's fault, but also
  don't stop at "my client can't connect" — test whether *anything* can connect, including the cloud provider's
  own tools.

---

## Setting up CI/CD (GitHub Actions deploy workflow)

### 23. A real secret got committed and pushed to GitHub
- **Symptom:** `git commit` output showed `create mode 100644 docker/gc_token` — the real Grafana Cloud token,
  now in the repo's history on `my-rag-org/mini-rag`.
- **Cause:** this was a *second* `gc_token` file, at `docker/gc_token` — a different path than the one already
  gitignored (`docker/prometheus/gc_token`), so the existing `.gitignore` rule never caught it.
- **Fix, immediately:**
  1. **Revoked the token in Grafana Cloud** (Access Policies page — the "Prometheus details" page only lets you
     *create* tokens, not see/revoke old ones) and generated a fresh one. Treated the pushed one as permanently
     burned, not just deleted.
  2. `git rm --cached docker/gc_token`, added `docker/gc_token` to `.gitignore`, committed and pushed the fix.
  3. Put the new token back in the same path (untracked).
- **How to explain it:** a leaked secret isn't fixed by deleting the file — it's already in git history and
  anyone with repo access can see it in an old commit. The credential itself has to be rotated.

### 24. GitHub Actions workflow file wasn't triggering at all
- **Symptom:** pushed `.github/workflows/deploy-main.yml`, nothing appeared under the Actions tab.
- **Cause 1 — invalid YAML:** the `script:` block for `appleboy/ssh-action` was written as
  ```yaml
  script: 
    cd /home/github_user/workspace/mini-rag
    git pull
  ```
  A multi-line string like this needs a literal block indicator (`script: |`) — without it, GitHub can't parse
  the workflow as valid, and it may not even list it.
- **Cause 2 — branch name case mismatch:** the trigger was `branches: - Main` (capital M), but the real branch
  is `main` (lowercase, confirmed by `git push origin main` working). Branch matching is case-sensitive, so this
  would never have fired even with valid YAML.
- **Fix:** `script: |` plus the actual content indented under it, and `main` (lowercase) everywhere, including a
  stray `git checkout Main` inside the script (removed entirely — unnecessary since the working copy already
  tracks `main`).

### 25. Workflow reported ✅ success, but the app never actually updated
- **Symptom:** pushed a real code fix, workflow went green, but `/docs` still showed the old behavior.
- **First check:** `sudo docker compose ps` — `fastapi`'s `STATUS` showed "Up about an hour", older than the
  push. The restart never happened, despite the green checkmark.
- **Cause, found in the Action's own log:**
  ```
  err: sudo: a terminal is required to read the password
  err: sudo: a password is required
  ```
  My manual test (`sudo -n true`) had misleadingly "worked" earlier — but only because my *interactive* SSH
  session still had a cached sudo credential from typing a password minutes before (sudo caches for ~15 min per
  session). GitHub Actions runs a fresh, non-interactive session every time — no cache, no terminal — so
  `sudo systemctl restart minirag.service` genuinely failed there. The script had no `set -e`, so the failure
  didn't stop it, and the later port-80 check still passed (nginx was still up from before), so the whole job
  reported success.
- **Fix:** gave passwordless sudo for exactly this one command:
  ```bash
  sudo visudo -f /etc/sudoers.d/minirag-deploy
  ```
  ```
  github_user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart minirag.service
  ```
  Verified properly this time with `sudo -k` first (clears the cached credential so the test can't be fooled the
  same way again), then `sudo -n systemctl restart minirag.service`.
- **How to explain it:** a green checkmark only means "the script didn't exit non-zero" — not "every command in
  it succeeded". A health check on the wrong thing (port 80/nginx instead of whether `fastapi` actually
  restarted) can hide a completely broken deploy step.
- **Also learned:** `docker compose restart` does **not** reload `env_file` changes — it only restarts the
  existing container with its old environment. Picking up new `.env` values needs `docker compose up -d
  <service>` (recreates the container) instead.

---

## Fixing the RAG answer endpoint (`answer_rag_error`)

### 26. Missing comma → silent syntax error → stale code kept running
- **Symptom:** added a `datetime` field to the welcome route's response; it never showed up, even after
  committing, pushing, and a successful-looking deploy.
- **Cause:** a real Python syntax error:
  ```python
  return {
      "app_version": app_version
      "datetime": datetime.now()...   # missing comma above
  }
  ```
  This is invalid Python — the app can't start with this file. Combined with issue 25 (deploy reporting success
  without actually restarting), the *old*, still-valid code kept serving requests, which looked exactly like "my
  change didn't take" rather than "my change is broken".
- **Fix:** added the missing comma, then made sure the redeploy actually happened this time (see issue 25).

### 27. `/index/answer/{project_id}` always returned `{"signal": "answer_rag_error"}`
- **Symptom:** search worked fine (`/index/search` returned real results), but asking a question always failed
  with a generic error and no clue why.
- **Why the error was so vague:** the route only checks `if not answer: return ... ANSWER_RAG_ERROR`. The actual
  LLM provider classes (`GroqProvider`, `CohereProvider`, `OllamaProvider`, etc.) all **catch their own
  exceptions internally and just log + return `None`** rather than raising — a deliberate "fail soft" design,
  but it means the real reason never reaches the HTTP response, only the container logs.
- **Real cause, found in `docker compose logs -f fastapi` while re-triggering the request:**
  ```
  Ollama generation error: The endpoint eb13-45-244-55-179.ngrok-free.app is offline. ERR_NGROK_3200
  ```
  `GENERATION_BACKEND` was set to Ollama, pointed at a free `ngrok` tunnel — which only exists while Ollama +
  ngrok are actively running on some other machine (mine, during earlier development). Free ngrok URLs die the
  moment that process stops and change on every restart, so this was never going to work reliably on a
  standalone server.
- **Fix:** switched to **Groq** instead — free tier, no dependency on any other machine staying online.
  ```
  GENERATION_BACKEND=GROQ
  GROQ_API_KEY=...
  GENERATION_MODEL_ID=openai/gpt-oss-20b
  ```
  (`GroqProvider` was already fully implemented from earlier development — just wasn't the active backend.)
- **Detour 1:** first tried `GENERATION_MODEL_ID=llama-3.3-70b-versatile` — Groq's model catalog changes over
  time, and that id no longer existed (`404 model_not_found`). Fetched the live list instead of guessing again:
  ```bash
  curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $KEY"
  ```
  and picked `openai/gpt-oss-20b` (a real text-generation model — the list also included audio/speech/moderation
  models like `whisper-*` and `orpheus-*` that would *not* have worked here).
- **Detour 2, a real near-miss:** pasted the Groq API key directly into a terminal command as
  `-H "Authorization: Bearer $gsk_..."` — the `$` made Bash try to expand it as a variable (which doesn't exist),
  sending an empty key, **and** posted the real key in plain text in the process. Treated it as leaked
  immediately: revoked it in the Groq console and generated a fresh one, same as the `gc_token` incident (issue
  23). Correct syntax has no `$` before a literal value: `-H "Authorization: Bearer gsk_actualkeyhere"`.
- **How to explain it:** a clean `{"signal": "..._error"}` JSON response (not a raw Python traceback) is a sign
  the code *caught* a failure gracefully rather than crashing — which means the real reason is only in the
  server logs, not the HTTP response. Always tail the logs while reproducing the request.

---

## Open items

1. Add a volume `fastapi_files:/app/assets/files` to the `fastapi` service so uploads survive rebuilds (bit
   twice now — issues 9 and its recurrence on the new server).
2. Make `/process` return an error when no file was loaded.
3. Optionally fix the dashboard's Requests Count query (see 7).
4. Before committing, check that `docker/prometheus/prometheus.yml` has no real token in it.
5. `.gitignore` entries for `docker/prometheus/gc_token` and `grafana_cloud_api_key` — done.
6. Rewrite git history to drop the old ~100MB MongoDB journal files GitHub warned about (issue 11) — not done,
   bigger/riskier change, low priority since it's a warning not a hard limit.
7. Clean up leftover debugging env vars in `.env.postgres.exporter` (`DATA_SOURCE_PASS`, `DATA_SOURCE_NAME` from
   step 6 of the password saga) — harmless now that the real fix (image tag) is in, but unused clutter.
8. `postgres-exporter` healthcheck fix (`pg_isready` → `wget .../metrics`) — done.
9. `postgres-exporter` image pinned to `latest` for PostgreSQL 18 compatibility — done and committed.
10. Static IP attached to the Lightsail instance so future restarts don't silently change the SSH host — done.
11. Passwordless sudo for the deploy restart command (`/etc/sudoers.d/minirag-deploy`) — done.
12. GitHub Actions workflow YAML fixed (`script: |`, lowercase `main`) — done and committed.
13. `docker/gc_token` leak: revoked, removed from tracking, gitignored, replaced — done. `docker/prometheus/gc_token`
    (the other path) was already gitignored from issue 5/6.
14. `GENERATION_BACKEND` switched from Ollama (fragile ngrok dependency) to Groq — done.
15. Consider adding `set -e` (or per-command `|| exit 1`) to the deploy workflow's script, so a real failure
    (like issue 25's sudo error) makes the whole job fail loudly instead of silently continuing.
16. Consider a health check in the deploy script that actually verifies `fastapi` restarted (e.g. checking
    `docker compose ps` uptime or hitting `/api/v1/`), not just that *something* is listening on port 80.

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
| tut-011 | pgvector (replacing Mongo/Qdrant), Nginx, Prometheus, Grafana monitoring | issues 1–10 |
| tut-012 | moved repo to a new GitHub org, deployed to AWS Lightsail (Ubuntu 24, SSH, Docker), fixed monitoring for the real server, set up CI/CD, fixed the RAG answer endpoint | issues 11–27, the `postgres-exporter` saga, and the Lightsail unreachable saga |
