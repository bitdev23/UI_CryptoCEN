# Velank / Mantraj AI — GCP VM Deployment

Production deployment does NOT use Docker.

Live stack:
- Ubuntu VM on GCP
- Python virtualenv
- `gunicorn` on port `5050`
- `systemd` for long-running services
- `nginx` reverse proxy with Let's Encrypt SSL

## Server

- VM: `mantraj-server`
- Region/zone: `us-east1-b`
- OS: Ubuntu 22.04.5 LTS
- Public IP: `34.75.246.129`
- App URL: `https://app.velank.io`

## SSH

```bash
ssh -i ~/.ssh/id_ed25519 bhavikk_vala@34.75.246.129
sudo su - mantraj
```

## App location

```text
/home/mantraj/mantraj
```

## Runtime model

- API service: `mantraj-api`
- Worker service: `mantraj-worker`
- Nginx forwards `443 -> 127.0.0.1:5050`
- `worker.py` handles Redis/RQ KB jobs

## systemd services

Templates are committed in:
- [deploy/systemd/mantraj-api.service](deploy/systemd/mantraj-api.service)
- [deploy/systemd/mantraj-worker.service](deploy/systemd/mantraj-worker.service)

Common commands:

```bash
sudo systemctl status mantraj-api mantraj-worker
sudo systemctl restart mantraj-api mantraj-worker
sudo journalctl -u mantraj-api -f
sudo journalctl -u mantraj-worker -f
```

## nginx

Template is committed in:
- [deploy/nginx/mantraj.conf](deploy/nginx/mantraj.conf)

After edits:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Deployment flow

Local:

```bash
git add .
git commit -m "describe change"
git push
```

Server:

```bash
ssh -i ~/.ssh/id_ed25519 bhavikk_vala@34.75.246.129
sudo su - mantraj
cd /home/mantraj/mantraj
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart mantraj-api mantraj-worker
```

## Important notes

- `Dockerfile` is legacy and not used in production.
- `docker-compose.yml` is not used in production.
- App port is always `5050` on the VM.
- Keep all production secrets in `/home/mantraj/mantraj/.env`.
- Google OAuth + Supabase redirect URLs must include `https://app.velank.io/auth/callback`.