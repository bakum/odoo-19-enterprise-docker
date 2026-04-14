# Odoo 19 Docker Dev Environment

## Quick start

1. Start Docker Desktop.
2. From this folder run:
   - `docker compose up -d --build`
3. Open:
   - `http://localhost:8019`

## Useful commands

- Start/update services: `docker compose up -d --build`
- Stop services: `docker compose down`
- Stop and remove data: `docker compose down -v`
- View logs: `docker compose logs -f odoo`

## Project structure

- `docker-compose.yml` - services (`odoo`, `postgres`)
- `Dockerfile` - custom Odoo image for extra Python deps
- `requirements.txt` - Python dependencies for custom modules
- `addons/` - local custom addons
- `config/odoo.conf` - Odoo runtime config
- `data/` - persisted PostgreSQL and filestore data
