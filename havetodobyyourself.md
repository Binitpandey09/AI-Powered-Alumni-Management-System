# THINGS YOU HAVE TO DO MANUALLY

This file lists every single thing that won't work out of the box and requires
your manual action — with exact steps on how to do each one.

---

## 1. FILL IN YOUR .env FILE

Your current `.env` is missing critical keys. Open `.env` and fill these in:

### OpenAI API Key (REQUIRED for all 4 AI tools)
```
OPENAI_API_KEY=sk-...
```
How to get it:
- Go to https://platform.openai.com/api-keys
- Click "Create new secret key"
- Copy and paste it into .env
- The project uses `gpt-4o-mini` — costs roughly $0.15 per 1M input tokens
- Without this: Resume Scorer, Resume Builder, AI Mock Interview, Skill Gap Analyzer all fail

### Razorpay Keys (REQUIRED for all payments)
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_here
```
How to get it:
- Go to https://razorpay.com and create an account
- Dashboard → Settings → API Keys → Generate Test Key
- Use test keys for development, live keys for production
- Without this: Session bookings, AI tool payments, referral boosts all fail

### Gemini API Key (already filled in your .env but it's exposed)
```
GEMINI_API_KEY=AIzaSy...
```
Your current key `[REDACTED_GEMINI_KEY]` is committed to the
repo and must be regenerated immediately.
- Go to https://aistudio.google.com/apikey
- Delete the old key, generate a new one
- Update .env with the new key
- Used for: CV parsing and AI profile summary generation

### Email Password (already filled but exposed)
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
```
Your current Gmail app password `[REDACTED_EMAIL_PASSWORD]` is exposed in the repo.
- Go to https://myaccount.google.com/apppasswords
- Revoke the old app password
- Generate a new one (select "Mail" + "Other device")
- Update .env with the new password
- Used for: OTP emails during registration and login

---

## 2. REGENERATE EXPOSED SECRETS IMMEDIATELY

Your `.env` file has been committed with real credentials. Do this right now:

1. Revoke your Gmail app password at https://myaccount.google.com/apppasswords
2. Revoke your Gemini API key at https://aistudio.google.com/apikey
3. Generate new ones and update .env
4. Add `.env` to `.gitignore` if not already there (it is, but double-check)
5. If you pushed this to GitHub, rotate all keys — they are compromised

---

## 3. SET UP POSTGRESQL DATABASE

The project requires PostgreSQL, not SQLite.

### For local development:
1. Install PostgreSQL from https://www.postgresql.org/download/
2. Open psql and run:
```sql
CREATE DATABASE alumni_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE alumni_db TO postgres;
```
3. Your .env already has these defaults set correctly for local dev
4. Run migrations:
```bash
python manage.py migrate
```
5. Create the admin and dev users:
```bash
python manage.py create_roles
python manage.py create_dev_users
```
Dev user credentials after running the command:
- Student: dev.student@college.ac.in / DevPass@123
- Alumni: dev.alumni@techcompany.com / DevPass@123
- Faculty: dev.faculty@college.ac.in / DevPass@123
- Admin: dev.admin@alumniai.com / DevPass@123

---

## 4. SET UP REDIS

Redis is required for Celery (async tasks) and WebSocket notifications.

### For local development (Windows):
Option A — Use WSL:
```bash
wsl --install
# inside WSL:
sudo apt install redis-server
sudo service redis-server start
```

Option B — Use Docker just for Redis:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

Option C — Download Redis for Windows:
- https://github.com/microsoftarchive/redis/releases
- Download and run `redis-server.exe`

Verify it works:
```bash
redis-cli ping
# should return: PONG
```

Without Redis: Celery tasks won't run, WebSocket notifications won't work,
but the app will still start (Celery is set to eager mode in dev).

---

## 5. RUN CELERY WORKER AND BEAT (for async tasks)

In dev mode `CELERY_TASK_ALWAYS_EAGER = True` so tasks run synchronously.
But for production or to test real async behavior, you need to run these
in separate terminals:

Terminal 1 — Worker:
```bash
celery -A alumni_platform worker --loglevel=info
```

Terminal 2 — Beat scheduler (for periodic tasks):
```bash
celery -A alumni_platform beat --loglevel=info
```

Periodic tasks that need this:
- Session reminders — every 30 minutes
- Process pending payments — every 15 minutes
- Cleanup old notifications — daily at 2 AM

---

## 6. CREATE MIGRATIONS FOR AI TOOLS APP

The `apps/ai_tools` app has models (AIToolUsage is in `apps/payments/models.py`
so that's fine) but the `apps/ai_tools/migrations/` folder only has `__init__.py`.

Check if there are any models in `apps/ai_tools/models.py` that need migrations:
```bash
python manage.py makemigrations ai_tools
python manage.py migrate
```

If it says "No changes detected" you're fine. If it creates a migration, run it.

---

## 7. RAZORPAY WEBHOOK SETUP (for production reliability)

Currently the project only verifies payments via signature on the frontend callback.
This means if a user closes the browser after payment but before the callback fires,
the payment is lost.

For production, set up a Razorpay webhook:
1. Go to Razorpay Dashboard → Settings → Webhooks
2. Add webhook URL: `https://yourdomain.com/api/payments/webhook/`
3. Select events: `payment.captured`, `payment.failed`
4. Copy the webhook secret

Then add to .env:
```
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

You'll need to write the webhook view yourself in `apps/payments/views.py`:
```python
class RazorpayWebhookView(APIView):
    permission_classes = []  # No auth — Razorpay calls this

    def post(self, request):
        import hmac, hashlib
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        signature = request.headers.get('X-Razorpay-Signature', '')
        body = request.body

        expected = hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return Response({'error': 'Invalid signature'}, status=400)

        payload = request.data
        event = payload.get('event')

        if event == 'payment.captured':
            payment_id = payload['payload']['payment']['entity']['id']
            order_id = payload['payload']['payment']['entity']['order_id']
            # Find and complete the transaction
            Transaction.objects.filter(
                razorpay_order_id=order_id
            ).update(status='completed', razorpay_payment_id=payment_id)

        return Response({'status': 'ok'})
```

Add to `apps/payments/urls.py`:
```python
path('webhook/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
```

---

## 8. ENABLE SSL IN PRODUCTION

In `alumni_platform/settings/prod.py`, these lines are commented out:
```python
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
```

After you get an SSL certificate on your production server, uncomment all of them.
If you're on Render.com or Railway, SSL is automatic — uncomment these right away.

---

## 9. PRODUCTION DEPLOYMENT SETUP

### Option A — Docker Compose (self-hosted VPS):
1. Copy `.env.production.example` to `.env` on your server
2. Fill in all production values
3. Run:
```bash
docker-compose up -d
```
This starts: PostgreSQL, Redis, Django (gunicorn), Celery worker, Celery beat

### Option B — Render.com (easiest):
1. Push code to GitHub
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Set environment variables from `.env.production.example`
5. Build command: `pip install -r requirements.txt`
6. Start command: `gunicorn --config gunicorn.conf.py alumni_platform.wsgi:application`
7. Add a Redis instance (Render has free Redis)
8. Add a PostgreSQL database (Render has free Postgres)
9. Set `DATABASE_URL` and `REDIS_URL` from Render's dashboard
10. Set `DJANGO_SETTINGS_MODULE=alumni_platform.settings.prod`

### Option C — Railway:
1. Push to GitHub
2. Connect repo on https://railway.app
3. Add PostgreSQL and Redis plugins
4. Set env vars
5. Deploy

---

## 10. ADMIN USER IN PRODUCTION

After deploying, create the admin user:
```bash
python manage.py create_roles
```
This creates: admin@alumniconnect.com with a default password.
Change the password immediately after first login via Django admin or:
```bash
python manage.py changepassword admin@alumniconnect.com
```

---

## 11. PAYOUT PROCESSING IS MANUAL

The payout system collects withdrawal requests but does NOT automatically
transfer money. You (the admin) have to manually process each payout:

1. Log in as admin
2. Go to Admin Dashboard → Payouts
3. See pending payout requests with user bank details
4. Manually transfer money via your bank / Razorpay Payout API
5. Mark the payout as "processed" with the transaction reference number

If you want to automate this, you need Razorpay Payouts API:
- Enable Payouts in your Razorpay dashboard (requires KYC)
- Get Payout API keys (different from payment keys)
- Add `RAZORPAY_PAYOUT_KEY_ID` and `RAZORPAY_PAYOUT_KEY_SECRET` to .env
- Implement the payout API call in `apps/payments/views.py` AdminPayoutManageView

---

## 12. ALUMNI VERIFICATION IS MANUAL

When an alumni submits their LinkedIn/document for verification:
1. Log in as admin
2. Go to Admin Dashboard → Verification
3. Review the submitted LinkedIn URL or document
4. Click Approve or Reject (with a note)

There is no automated verification — you review each one manually.

---

## 13. WEBSOCKET NOTIFICATIONS — DAPHNE/ASGI REQUIRED

The real-time notification system uses Django Channels over WebSocket.
In development, run with Daphne instead of the normal dev server:
```bash
daphne -p 8000 alumni_platform.asgi:application
```
Or just use the normal dev server — it will fall back to polling.

In production, the `gunicorn.conf.py` already uses `uvicorn.workers.UvicornWorker`
which supports WebSockets, so no extra setup needed there.

---

## 14. STATIC FILES IN PRODUCTION

Run this before deploying (or it runs automatically in Docker):
```bash
python manage.py collectstatic --noinput
```
Static files are served by WhiteNoise — no Nginx needed for static files.
Media files (uploads) need persistent storage in production:
- On Docker: the `media_files` volume handles this
- On Render: use a Render Disk or AWS S3 (see below)

---

## 15. MEDIA FILE STORAGE FOR PRODUCTION (optional but recommended)

By default media files are stored on disk. On platforms like Render.com,
the disk is ephemeral — files are lost on redeploy.

To use AWS S3 for media storage:
1. Create an S3 bucket on AWS
2. Create an IAM user with S3 access
3. Add to .env:
```
USE_S3=True
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=ap-south-1
```
4. In `alumni_platform/settings/prod.py`, add:
```python
if config('USE_S3', default=False, cast=bool):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-south-1')
    AWS_S3_FILE_OVERWRITE = False
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/'
```
5. Install: `pip install django-storages boto3`

---

## 16. OPENAI RATE LIMITS AND COSTS

The AI tools use `gpt-4o-mini`. Be aware:
- Free tier: $5 credit on new accounts
- After that: pay-as-you-go
- Each AI tool call costs roughly $0.001–$0.005 depending on input size
- If you hit rate limits, users will see "AI service temporarily unavailable"
- Monitor usage at https://platform.openai.com/usage

---

## 17. GEMINI RATE LIMITS

The CV parser uses Gemini 2.0 Flash:
- Free tier: ~50 requests/day
- If you exceed this, users get a "daily quota exceeded" error
- The code already handles this gracefully with a clear error message
- To increase limits: upgrade at https://aistudio.google.com/apikey

---

## 18. EMAIL DELIVERABILITY IN PRODUCTION

Gmail SMTP works fine for low volume (< 500 emails/day).
For higher volume or better deliverability, switch to:
- SendGrid: https://sendgrid.com (free tier: 100 emails/day)
- Mailgun: https://mailgun.com (free tier: 5000 emails/month)

To switch to SendGrid:
```
EMAIL_BACKEND=anymail.backends.sendgrid.EmailBackend
SENDGRID_API_KEY=SG.xxxx
```
Install: `pip install django-anymail`

---

## 19. CHANGE THE DEFAULT SECRET KEY FOR PRODUCTION

Your current `SECRET_KEY` in .env is `django-insecure-dev-key-for-local-development-only-change-in-production`.

Generate a proper one:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output and set it as `SECRET_KEY` in your production .env.

---

## 20. CORS CONFIGURATION FOR PRODUCTION

In `alumni_platform/settings/base.py`, CORS is configured for localhost.
For production, update `CORS_ALLOWED_ORIGINS` to include your actual domain:
```python
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
```

---

## QUICK START CHECKLIST (local dev)

Do these in order to get the project running locally:

- [ ] Fill in `OPENAI_API_KEY` in .env
- [ ] Fill in `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in .env
- [ ] Regenerate and update `GEMINI_API_KEY` in .env (current one is exposed)
- [ ] Regenerate and update `EMAIL_HOST_PASSWORD` in .env (current one is exposed)
- [ ] Install and start PostgreSQL, create `alumni_db` database
- [ ] Install and start Redis
- [ ] Run `python manage.py migrate`
- [ ] Run `python manage.py create_roles`
- [ ] Run `python manage.py create_dev_users`
- [ ] Run `python manage.py runserver` (or `daphne` for WebSocket support)
- [ ] Open http://localhost:8000

## QUICK START CHECKLIST (production)

- [ ] Generate new SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Set ALLOWED_HOSTS to your domain
- [ ] Set DATABASE_URL to production PostgreSQL
- [ ] Set REDIS_URL to production Redis
- [ ] Fill in all API keys (OpenAI, Gemini, Razorpay live keys)
- [ ] Fill in production email credentials
- [ ] Run `python manage.py migrate`
- [ ] Run `python manage.py create_roles`
- [ ] Run `python manage.py collectstatic`
- [ ] Uncomment SSL headers in prod.py after SSL is active
- [ ] Set up Razorpay webhook
- [ ] Start Celery worker and beat processes
