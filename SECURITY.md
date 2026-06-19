# Security Policy

## Supported Versions

The default branch is the supported development target.

## Reporting a Vulnerability

Please do not open a public issue for secrets exposure, authentication bypasses, remote code execution, data leaks, or other security-sensitive findings.

Use GitHub private vulnerability reporting if it is enabled for the repository. If it is not enabled, contact the maintainers through the project community channel and ask for a private disclosure path.

## Local Secrets

Do not commit `config/model/providers.secrets.yml`, `.env`, database files, generated media, or storage contents. Use the checked-in example files as templates:

- `.env.dev.example`
- `.env.prod.example`
- `config/model/providers.secrets.example.yml`

Per-user model provider API keys stored in `sys_user_model_credential.encrypted_api_key` are encrypted at rest with a key derived from `JIANDOU_SECRET_KEY`. Rotating `JIANDOU_SECRET_KEY` requires re-saving those user credentials. Platform-wide keys in `config/model/providers.secrets.yml` are local deployment secrets and must remain outside version control.

## Sessions And Roles

JWT cookies identify the session subject, but protected backend APIs re-check `sys_user.status` and `sys_user.role` from the database on each request. Disabling or demoting a user should therefore revoke the old cookie's effective permissions immediately.

State-changing `/api/` requests with an `Origin` header are accepted only from the request host, `JIANDOU_WEB_ORIGIN`, or comma-separated `JIANDOU_TRUSTED_ORIGINS`. Configure these values when serving the frontend through a custom domain or reverse proxy.

Authentication entrypoints have an in-process sliding-window rate limit by client IP. Tune `JIANDOU_AUTH_LOGIN_RATE_LIMIT`, `JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT`, and `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS` for your deployment. Multi-instance deployments should put a shared rate limiter at the reverse proxy or gateway layer as well.

The API sets baseline browser security headers on every response: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`. When `JIANDOU_COOKIE_SECURE=true`, it also sends `Strict-Transport-Security`.
