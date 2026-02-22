# WESTSEAL Website

Django project for WESTSEAL (hydraulic & pneumatic seals). Includes:
- Separate pages per section
- Admin-managed content, catalogs and media
- User cabinet with requests + support chat
- RU/EN language switch
- Quick lead modal form for fast conversion
- Chat attachments (images/videos/files)
- Live chat polling in widget (Telegram-like updates every few seconds)
- SEO basics: sitemap, robots, canonical, FAQ schema, breadcrumbs schema
- Analytics hooks for GA4 and Yandex Metrika
- Admin-managed FAQ / case studies / testimonials on homepage
- Seal catalog with product cards, search, and detailed product page

## Quick start (local)

1. Create venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Database

- If `POSTGRES_HOST` is set, PostgreSQL is used.
- Otherwise SQLite is used by default.

Example Postgres env:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_DB=westseal
export POSTGRES_USER=westseal
export POSTGRES_PASSWORD=westseal
```

Optional env vars:

```bash
export SITE_URL=https://your-domain.ru
export GA4_ID=G-XXXXXXXXXX
export YANDEX_METRIKA_ID=12345678
export DEFAULT_TO_EMAIL=westseal@mail.ru
export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export EMAIL_HOST=smtp.your-provider.ru
export EMAIL_PORT=587
export EMAIL_HOST_USER=your_login
export EMAIL_HOST_PASSWORD=your_password
export EMAIL_USE_TLS=1
```

3. Migrate and create admin:

```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Seed catalog PDFs (after downloading):

```bash
python manage.py seed_catalogs
```

5. Run server:

```bash
python manage.py runserver
```

## Import seal catalog (mkt-rti.ru)

Example:

```bash
python manage.py import_mkt_rti --category uplotnenija_porshnja --limit 50
```

Options:
- `--category` top category slug from mkt-rti (e.g. `uplotnenija_porshnja`)
- `--limit` limit total products
- `--max-pages` limit pages per category
- `--no-images` skip image download

## Download catalogs

```bash
python scripts/download_catalogs.py
```

Notes:
- Some external hosts may block automated downloads. Those entries are flagged in `data/catalogs/sources.json`.
- Add/replace catalogs by editing `data/catalogs/sources.json` and re-running the script.

## Telegram support integration

Set env vars:

```bash
export TELEGRAM_BOT_TOKEN=... 
export TELEGRAM_WEBHOOK_SECRET=... 
```

Webhook URL:
`/support/telegram/webhook/?secret=YOUR_SECRET`

Add `telegram_chat_id` for a support thread in admin to enable message forwarding.
