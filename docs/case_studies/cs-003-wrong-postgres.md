# CS-003: Ingestion worked, but into the wrong database

**Phase:** 2 · **Date:** 2026-11-11 · **Status:** Done

## Context
Spec 2.4 loads the rules corpus into Postgres with pgvector. It asked for a Docker Compose service on port 5432, with `ATLAS_DB_URL=postgresql://...@localhost:5432/atlas` in `.env`.

## Symptom
`docker compose up` reported the container healthy. The ingest script ran twice and printed exactly what the spec asked for: `found 38, new 38` and then `found 38, new 0, skipped 38`. But `psql` inside the container said `relation "rule_chunks" does not exist`.

## Investigation
1. Both runs succeeded and agreed with each other, so the script was writing to a real, working database, just not the one being checked.
2. `ss -ltn` showed a listener on `127.0.0.1:5432`, and Docker published `0.0.0.0:5432`. Two servers were sharing one port number on different addresses.
3. The process list showed a native PostgreSQL 16 running in WSL, which already had an `atlas` database with pgvector available.
4. Asking the connection itself settled it: `SHOW server_version` returned 16.15 (Ubuntu), while the container runs 17.

## Root cause
`localhost` resolved to `127.0.0.1`, where the native server listens. That address is more specific than Docker's `0.0.0.0` binding, so the native server won every connection. Nothing failed, because the native server had the same user, database and extension. And no part of the pipeline said which server it was talking to.

## Fix: steps taken
1. **Chose one primary.** The native Postgres on 5432 stays the default, and `ATLAS_DB_URL` is unchanged.
2. **Gave the container its own port.** `docker-compose.yml` now maps host port 5433, so using it is an explicit choice in `ATLAS_DB_URL`, never an accident. The README says so.
3. **Made the target visible.** `ingest_rules.py` prints `host, port, database, server version` before it changes anything. It never prints the password, because it reads the connection's info, not the URL. `connect()` was split from `prepare()` so that "before it changes anything" is really true.
4. Stopped the empty container (`docker compose down`) and updated spec 2.4, requirement 1.

## Result
Every ingest run now starts with a line like `connected: host=localhost port=5432 database=atlas server=16.15 (...)`. A wrong target shows up in the first line of output instead of in a later debugging session.

## Lessons
- "It worked" is not "it worked where I think". Verify the side effect where you expect it, not only the script's own report.
- Two services can share a port number on different addresses without either one failing.
- Scripts with side effects should name their target before they act.
- The best evidence is a fact only the target knows (here, the server version), not a fact both candidates share.

## Summary
"My ingestion script reported success twice, but the table wasn't in the Docker database I checked. A native Postgres in WSL was listening on 127.0.0.1:5432, which beat Docker's 0.0.0.0:5432 binding, and it happened to have the same database and extension, so nothing errored. I proved it by asking the connection for its server version. The fix was to choose one primary, move the container to its own port, and make the script print its target before it changes anything. Now a wrong target is visible in the first line of output."
