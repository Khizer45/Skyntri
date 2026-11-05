# Test plan and release checklist

## Automated (backend)

```
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest -q
DATABASE_URL=sqlite:///./tmp-migrate.db alembic upgrade head
```

| Area | Tests |
|---|---|
| Auth, JWT, sessions | `test_auth_integration`, `test_jwt_security`, `test_security_hardening::test_tokens_without_expected_claims_are_rejected`, `…production_refuses_weak_secrets`, `…development_replaces_placeholder_secret` |
| Password reset | `test_security_hardening::test_forgot_password_*`, `test_reset_token_is_single_use`, `test_expired_and_superseded_reset_tokens_fail`, `test_password_reset_disabled_in_production_without_email` |
| Admin / contact | `test_contact_submission_is_public_but_listing_is_admin_only`, `test_role_cannot_be_set_by_client`, `test_contact_submission_is_rate_limited` |
| IDOR / private files | `test_security_integration`, `test_uploads_are_not_publicly_served_and_signed_urls_are_owner_scoped`, `test_signed_urls_expire`, `test_manual_analysis_cannot_reference_another_users_file`, `test_cross_user_access_to_reports_progress_scans_is_blocked`, `test_account_deletion_removes_private_files` |
| Upload abuse | `test_upload_security` (unsupported type, oversize, path traversal, spoofed MIME, corrupt, GIF/SVG, huge dimensions, random names, temp cleanup) |
| Rate limiting | `test_bruteforce_protection`, `test_login_failures_are_throttled_in_the_shared_database` |
| Input gate / abstention | `test_input_gate` (skin accepted; document, screen, dark, over-exposed, flat, tiny rejected; model never called on rejection; Model B unavailable; model-uncertain abstention) |
| Existing features | `test_skin_analysis_integration`, `test_progress_integration`, `test_ingredient_*`, `test_chat_integration`, `test_pdf`, `test_preprocessing`, `test_thresholds`, `test_sql_injection_security` |
| Ops | `test_liveness_and_readiness`, `test_security_headers_and_oversized_requests`, `test_validation_errors_do_not_echo_passwords` |

CI (`.github/workflows/ci.yml`) also runs: frontend build, `pip-audit`, `npm audit`, gitleaks, Docker build + container smoke test.

## Manual checks before each release

- [ ] Sign up, log in, log out, change password, delete account.
- [ ] Password reset e-mail arrives; link works once; expired link fails.
- [ ] Skin analysis with a real face photo → results labelled "Facial skin concerns · AI estimate, not a diagnosis".
- [ ] Photos of a laptop, phone, document, food and room → "This image was not analyzed", no labels.
- [ ] Dark/blurry selfie → retake guidance.
- [ ] "Skin disease screening support" option is shown as not available.
- [ ] Images in history/results load; a copied image link stops working after 15 minutes.
- [ ] Ingredient scan with a real label photo (Tesseract installed).
- [ ] Progress comparison shows the "approximate visual comparison" note.
- [ ] Report PDF downloads only for the owner.
- [ ] Contact form submits; `/contact` list works only for an admin account.

## Release gate (all must be true)

- [ ] No open Critical finding (`docs/01_Security_Audit_Report.md`).
- [ ] Trained skin/non-skin gate evaluated on a held-out hard-negative set; thresholds agreed with the product owner (**open**).
- [ ] Model A metrics reproduced; model card complete (**open**).
- [ ] Production secrets set and rotated; `ENVIRONMENT=production` starts cleanly.
- [ ] SMTP configured (or reset knowingly disabled).
- [ ] Container smoke test, PostgreSQL migration, backup and restore drill done.
- [ ] Memory/latency measured on the target host.
- [ ] Privacy notice covers images, retention, deletion and any LLM provider.
