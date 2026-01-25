Duo / Duo Mobile MFA integration

Overview

This project has been migrated from SMTP OTP to Duo Push as the primary MFA method for admin roles (COLLEGE_ADMIN, ACADEMIC_COORDINATOR).

Setup

1. Install the Duo Python client and python-dotenv for local env files:

   pip install duo_client python-dotenv

2. For local development you can create a `.env` file at the project root using `.env.example` as a template. This file is ignored by git to prevent accidental commits of secrets.

2. Add the required environment variables (recommended to set in production environment, for local dev set in your shell/IDE):

   - DUO_INTEGRATION_KEY: Duo integration key (IKEY)
   - DUO_SECRET_KEY: Duo secret key (SKEY)
   - DUO_API_HOST: Duo API hostname (e.g. api-xxxxxxxx.duosecurity.com)
   - (Optional) DUO_API_TIMEOUT: HTTP timeout in seconds (default: 10)

3. Make sure users who will use Duo have `duo_username` populated on their `User` record.
   This should match how users are provisioned in Duo (username or internal id depending on your Duo setup).

4. Database migration:

   After pulling the code changes, run:

       python manage.py makemigrations
       python manage.py migrate

   This will add `duo_username` to the `User` model and `duo_txid` / `duo_status` to `MFASession`.

How it works

- Login endpoints for admin roles now call `send_duo_push()` which queues a Duo Push for the user and creates an `MFASession` entry.
- The login response returns `mfa_required: true` and an `mfa_id` which the client can use to poll the verify endpoint.
- The `/admin-verify-otp/` endpoint accepts `mfa_id` and will poll Duo (via `check_duo_status`) to confirm whether the push was approved.

Testing locally

- For unit tests we patch `send_duo_push` and `check_duo_status` to simulate Duo behavior (see `custom_auth/tests.py`).
- For manual testing against Duo, ensure Duo keys are configured correctly and that the user has a Duo device.

Notes

- The previous SMTP OTP flow is still available as `send_otp_email` for fallback but admin login uses Duo push by default.
- If you don't want to install `duo_client` in some environments, the code provides clear error messages and the tests mock Duo functionality.

Webhooks (async verification)

- You can configure Duo to send an async webhook to our app instead of polling. Configure a Duo webhook in the Duo Admin Panel to POST to `/duo/webhook/` on your server.
- Set a shared secret in Duo and also set `DUO_WEBHOOK_SECRET` in your environment so the app can verify incoming requests with HMAC-SHA256. The webhook should include header `X-Duo-Signature: <hex>` which is the HMAC-SHA256 of the raw request body using the shared secret.
- Payload example: `{ "txid": "<duo-txid>", "result": "allow" }` (or `"result": "deny"`). The webhook handler will set `MFASession.duo_status` and mark `is_verified=True` when `allow` is received.
- Tests covering webhook signature verification are included in `custom_auth/tests.py`.

Management command: `duo_pending`

- A management command `duo_pending` lists pending MFASessions that have Duo transactions (filterable by `--status` and limited by `--limit`).
- Use `--poll` to poll Duo for each session and update status immediately (requires Duo keys configured).
- Examples:
  - `python manage.py duo_pending` — list pending sessions
  - `python manage.py duo_pending --poll` — poll Duo for each pending session and update status
  - `python manage.py duo_pending --status pending --limit 100` — list up to 100 sessions with status 'pending'

Security

- Keep Duo keys in a secure place (environment variables, secrets manager).
- Consider restricting DUO_API_HOST to known trusted values.

If you want, I can also add optional webhook-based callbacks (Duo "async" verification) to avoid polling and to support real-time updates; tell me if you'd like that.