# Render deployment guide

## Overview

PhishShift is a synthetic phishing-risk scanner for helpdesk triage. It is designed to explain risk without opening links or collecting real credentials.

## Required configuration

- Python 3.11
- Render web service
- Gunicorn entrypoint: `gunicorn app.wsgi:app --workers 2 --threads 4 --timeout 120`
- Health check: `/healthz`
- Environment: `FLASK_ENV=production`

## Render service setup

1. Connect the Git repository to Render.
2. Create a web service from the repository root.
3. Use the existing `render.yaml` file as the deployment manifest.
4. Keep the `PYTHON_VERSION` pinned to `3.11.9`.
5. Ensure the build installs dependencies from `requirements.txt`.

## Runtime notes

- The app exposes `/healthz` for service health checks.
- The scanner never fetches live URLs or opens links.
- All URL content is defanged as `hxxp://example[.]com/...` in stored data.
- The project is safety-focused and uses synthetic data only.

## Deployment verification

After deployment, confirm:

- the service responds at `/healthz`
- the scanner page renders successfully
- the banner states: `Decision support only - not a guarantee of safety.`

## Operational cautions

- Do not use production inboxes, credential stores, or real user data.
- Do not send live messages to external systems from the app.
- Treat all risk scores as advisory only.
