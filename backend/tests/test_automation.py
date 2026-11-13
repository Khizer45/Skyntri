"""Automation: API keys, signed webhooks, SSRF protection, agents, posts."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.db.models import Appointment, ClinicPost, SkinAnalysis, WebhookEndpoint
from app.services import agents, automation, http_client, scheduler
from tests.conftest import register
from tests.test_clinic import _book, _doctor


class Inbox:
    """Collects webhook requests instead of sending them."""

    def __init__(self, status=200):
        self.requests, self.status = [], status

    def send(self, method, url, *, headers=None, json_body=None, form=None, data=None, timeout=15.0):
        self.requests.append({"url": url, "headers": headers, "body": json.loads(data)})
        return http_client.HttpResponse(self.status, b"{}")

    def events(self):
        return [r["body"]["event"] for r in self.requests]


@pytest.fixture
def admin_api(api, monkeypatch):
    client, SessionLocal = api
    inbox = Inbox()
    monkeypatch.setattr(http_client, "send", inbox.send)
    monkeypatch.setattr(settings, "admin_emails", "boss@test.com")
    admin = register(client, "boss@test.com")
    return client, SessionLocal, admin, inbox


def _hook(client, admin, **extra):
    body = {"name": "n8n", "url": "https://n8n.example.com/webhook/skyntri", **extra}
    created = client.post("/admin/automation/webhooks", json=body, headers=admin)
    assert created.status_code == 201, created.text
    return created.json()


def _key(client, admin, scopes):
    created = client.post("/admin/automation/api-keys", json={"name": "n8n", "scopes": scopes}, headers=admin)
    assert created.status_code == 201, created.text
    return created.json()


def test_automation_admin_endpoints_require_admin(admin_api):
    client, _, admin, _ = admin_api
    user = register(client, "u@test.com")
    for method, path in [("get", "/admin/automation"), ("post", "/admin/automation/api-keys"),
                         ("post", "/admin/automation/webhooks"), ("get", "/admin/posts"),
                         ("post", "/admin/automation/agents/daily_report/run")]:
        assert getattr(client, method)(path).status_code == 401
        assert getattr(client, method)(path, headers=user).status_code == 403
    overview = client.get("/admin/automation", headers=admin).json()
    assert "appointment.created" in overview["events"] and len(overview["agents"]) == 3


def test_api_key_is_shown_once_hashed_scoped_and_revocable(admin_api):
    client, SessionLocal, admin, _ = admin_api
    assert client.post("/admin/automation/api-keys", json={"name": "bad", "scopes": ["root"]},
                       headers=admin).status_code == 400
    created = _key(client, admin, ["read:summary"])
    key = created["key"]
    assert key.startswith("sky_") and len(key) > 40

    listed = client.get("/admin/automation", headers=admin).json()["api_keys"][0]
    assert "key" not in listed and listed["prefix"] == key[:10]
    with SessionLocal() as db:  # only the hash is stored
        from app.db.models import ApiKey
        row = db.query(ApiKey).one()
        assert key not in (row.key_hash, row.prefix) and row.key_hash == automation.hash_api_key(key)

    url = "/automation/v1/summary/daily"
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"X-API-Key": "sky_wrong"}).status_code == 401
    assert client.get(url, headers={"X-API-Key": key}).status_code == 200
    assert client.get(url, headers={"Authorization": f"Bearer {key}"}).status_code == 200
    # A session token is not an API key, and the key has only its own scope.
    assert client.get(url, headers=admin).status_code == 401
    assert client.get("/automation/v1/appointments", headers={"X-API-Key": key}).status_code == 403
    assert client.post("/automation/v1/agents/daily_post/run", headers={"X-API-Key": key}).status_code == 403
    # An API key does not open the normal application either.
    assert client.get("/admin/automation", headers={"X-API-Key": key}).status_code == 401

    assert client.delete(f"/admin/automation/api-keys/{created['id']}", headers=admin).status_code == 204
    assert client.get(url, headers={"X-API-Key": key}).status_code == 401


def test_webhook_receives_signed_events_without_medical_details(admin_api):
    client, _, admin, inbox = admin_api
    plain = _hook(client, admin, events=["appointment.created", "appointment.updated"])
    with_contact = _hook(client, admin, name="reminders", url="https://hooks.example.com/b", include_contact=True)
    assert plain["secret"].startswith("whsec_") and plain["secret"] != with_contact["secret"]

    doctor, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com", name="Sara Patient")
    client.put("/profile", json={"phone": "+923001234567"}, headers=patient)
    appointment = _book(client, patient, doctor_id).json()

    created = [r for r in inbox.requests if r["body"]["event"] == "appointment.created"]
    assert {r["url"] for r in created} == {plain["url"], with_contact["url"]}
    first = next(r for r in created if r["url"] == plain["url"])

    # Signature: HMAC-SHA256 over "<timestamp>.<raw body>" with the endpoint's secret.
    raw = json.dumps(first["body"]).encode()
    timestamp = first["headers"]["X-Skyntri-Timestamp"]
    assert first["headers"]["X-Skyntri-Signature"] == automation.sign(plain["secret"], timestamp, raw)
    assert first["headers"]["X-Skyntri-Signature"] != automation.sign(with_contact["secret"], timestamp, raw)
    assert first["headers"]["X-Skyntri-Event"] == "appointment.created"

    data = first["body"]["data"]
    assert data["appointment_id"] == appointment["id"] and data["status"] == "requested"
    text = json.dumps(first["body"])
    # No reason for the visit, and no contact details unless switched on for that endpoint.
    assert "Acne" not in text and "pat@test.com" not in text and "contact" not in data
    second = next(r for r in created if r["url"] == with_contact["url"])
    assert second["body"]["data"]["contact"] == {"name": "Sara Patient", "email": "pat@test.com",
                                                 "phone": "+923001234567"}
    assert "Acne" not in json.dumps(second["body"])

    # The subscribed endpoint does not get events it did not ask for.
    assert "doctor.applied" not in [r["body"]["event"] for r in inbox.requests if r["url"] == plain["url"]]
    client.patch(f"/doctor/appointments/{appointment['id']}", json={"status": "confirmed"}, headers=doctor)
    assert inbox.events().count("appointment.updated") == 2


def test_failing_webhook_is_recorded_and_switched_off(admin_api, monkeypatch):
    client, SessionLocal, admin, inbox = admin_api
    hook = _hook(client, admin)
    inbox.status = 500
    monkeypatch.setattr(automation, "MAX_CONSECUTIVE_FAILURES", 2)

    result = client.post(f"/admin/automation/webhooks/{hook['id']}/test", headers=admin).json()
    assert result == {"ok": False, "status_code": 500, "error": "HTTP 500"}
    client.post(f"/admin/automation/webhooks/{hook['id']}/test", headers=admin)
    detail = client.get(f"/admin/automation/webhooks/{hook['id']}", headers=admin).json()
    assert detail["is_active"] is False and detail["failure_count"] == 2 and len(detail["deliveries"]) == 2

    # A broken receiver never breaks the application.
    def explode(*args, **kwargs):
        raise http_client.HttpError("down")

    monkeypatch.setattr(http_client, "send", explode)
    client.put(f"/admin/automation/webhooks/{hook['id']}", headers=admin,
               json={"name": "n8n", "url": hook["url"], "is_active": True})
    assert register(client, "still-works@test.com")
    with SessionLocal() as db:
        assert db.query(WebhookEndpoint).one().failure_count == 0


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/admin", "https://localhost/x", "https://169.254.169.254/latest/meta-data",
    "https://10.0.0.5/hook", "https://[::1]/hook", "http://example.com/hook", "ftp://example.com/x",
    "https://user:pass@example.com/hook", "not a url",
])
def test_private_and_unsafe_webhook_urls_are_refused_in_production(url, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(automation.UnsafeWebhookUrl):
        automation.validate_webhook_url(url)


def test_allowed_hosts_and_development_mode(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "automation_allowed_hosts", "n8n, internal.example")
    assert automation.validate_webhook_url("http://n8n:5678/webhook/x") == "http://n8n:5678/webhook/x"
    monkeypatch.setattr(settings, "environment", "development")
    assert automation.validate_webhook_url("http://localhost:5678/webhook/x")
    with pytest.raises(automation.UnsafeWebhookUrl):
        automation.validate_webhook_url("https://user:pass@example.com/hook")


def test_webhook_url_is_checked_when_saved(admin_api, monkeypatch):
    client, _, admin, _ = admin_api
    monkeypatch.setattr(settings, "environment", "production")
    bad = client.post("/admin/automation/webhooks", headers=admin,
                      json={"name": "x1", "url": "https://127.0.0.1/hook"})
    assert bad.status_code == 400 and "private" in bad.json()["detail"]
    assert client.post("/admin/automation/webhooks", headers=admin,
                       json={"name": "x1", "url": "https://n8n.example.com/h", "events": ["nope"]}).status_code == 400


def test_agents_report_remind_and_post(admin_api):
    client, SessionLocal, admin, inbox = admin_api
    _hook(client, admin, include_contact=True)
    doctor, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com", name="Sara Patient")
    appointment = _book(client, patient, doctor_id).json()
    client.patch(f"/doctor/appointments/{appointment['id']}", json={"status": "confirmed"}, headers=doctor)

    with SessionLocal() as db:
        row = db.get(Appointment, appointment["id"])
        row.starts_at = datetime.now(timezone.utc) + timedelta(hours=3)
        row.ends_at = row.starts_at + timedelta(minutes=30)
        for _ in range(3):
            db.add(SkinAnalysis(user_id=row.patient_id, predicted_condition="Acne, Dark Spots",
                                confidence_score=80.0, severity_level="Low"))
        db.add(SkinAnalysis(user_id=row.patient_id, predicted_condition="No specific visible condition detected",
                            confidence_score=80.0, severity_level="Low"))
        db.commit()

    run = lambda name: client.post(f"/admin/automation/agents/{name}/run", headers=admin).json()  # noqa: E731

    reminders = run("appointment_reminders")
    assert reminders["status"] == "ok" and reminders["details"]["reminders"] == 1
    reminder = next(r for r in inbox.requests if r["body"]["event"] == "appointment.reminder")
    assert reminder["body"]["data"]["contact"]["email"] == "pat@test.com"
    assert run("appointment_reminders")["details"]["reminders"] == 0  # never reminded twice

    report = run("daily_report")
    assert report["status"] == "ok" and "report.daily" in inbox.events()
    assert report["details"]["top_concerns"][0] == {"label": "Acne", "count": 3}
    assert "pat@test.com" not in json.dumps(report)  # totals only

    post = run("daily_post")
    assert post["details"]["topic"] == "Acne" and post["details"]["status"] == "draft"
    # Drafts are not visible to users and not announced; publishing does both.
    assert client.get("/posts", headers=patient).json() == []
    assert "post.published" not in inbox.events()
    client.patch(f"/admin/posts/{post['details']['post_id']}", json={"publish": True}, headers=admin)
    feed = client.get("/posts", headers=patient).json()
    assert len(feed) == 1 and "acne" in feed[0]["title"].lower()
    assert inbox.events().count("post.published") == 1
    assert client.get("/posts").status_code == 401

    assert client.post("/admin/automation/agents/nope/run", headers=admin).status_code == 404
    assert len(client.get("/admin/automation", headers=admin).json()["runs"]) == 4


def test_daily_post_can_auto_publish(admin_api):
    client, SessionLocal, admin, inbox = admin_api
    _hook(client, admin)
    client.put("/admin/settings", json={"key": "agent_posts_auto_publish", "value": True}, headers=admin)
    client.post("/admin/automation/agents/daily_post/run", headers=admin)
    with SessionLocal() as db:
        assert db.query(ClinicPost).one().status == "published"
    assert "post.published" in inbox.events()


def test_automation_api_for_external_tools(admin_api):
    client, _, admin, inbox = admin_api
    key = {"X-API-Key": _key(client, admin, list(automation.SCOPES))["key"]}
    doctor, doctor_id = _doctor(client, admin)
    patient = register(client, "pat@test.com", name="Sara Patient")
    appointment = _book(client, patient, doctor_id).json()

    listed = client.get("/automation/v1/appointments", params={"status": "all", "hours_ahead": 240}, headers=key).json()
    assert listed["count"] == 1 and listed["appointments"][0]["contact"]["name"] == "Sara Patient"
    assert "reason" not in listed["appointments"][0]

    url = f"/automation/v1/appointments/{appointment['id']}/status"
    assert client.post(url, json={"status": "confirmed"}, headers=key).json()["status"] == "confirmed"
    assert client.post(url, json={"status": "confirmed"}, headers=key).status_code == 409
    assert client.get(f"/appointments/{appointment['id']}", headers=patient).json()["status"] == "confirmed"
    assert client.post("/automation/v1/appointments/unknown/status", json={"status": "confirmed"},
                       headers=key).status_code == 404

    post = client.post("/automation/v1/posts", headers=key, json={
        "title": "Clinic closed on Friday", "body": "We are closed this Friday for a public holiday.",
        "kind": "announcement", "publish": True})
    assert post.status_code == 201 and post.json()["source"] == "api"
    assert client.get("/posts", headers=patient).json()[0]["title"] == "Clinic closed on Friday"

    # An external scheduler can start an agent at most once per day.
    first = client.post("/automation/v1/agents/daily_report/run", params={"once_per": "day"}, headers=key).json()
    assert first["status"] == "ok"
    again = client.post("/automation/v1/agents/daily_report/run", params={"once_per": "day"}, headers=key).json()
    assert again["skipped"] is True
    assert client.get("/automation/v1/summary/daily", headers=key).json()["summary"] == first["summary"]

    actions = [e["action"] for e in client.get("/admin/audit", headers=admin).json()]
    assert "appointment.confirmed" in actions and "api_key.created" in actions


def test_scheduler_runs_each_period_once(api, monkeypatch):
    _, SessionLocal = api
    monkeypatch.setattr(settings, "agent_daily_hour", 8)
    early = datetime(2026, 11, 10, 7, 30)
    morning = datetime(2026, 11, 10, 8, 5)

    assert scheduler.tick(SessionLocal, early) == ["appointment_reminders:2026-11-10T07"]
    assert set(scheduler.tick(SessionLocal, morning)) == {
        "appointment_reminders:2026-11-10T08", "daily_report:2026-11-10", "daily_post:2026-11-10"}
    assert scheduler.tick(SessionLocal, morning) == []  # nothing runs twice
    assert agents.due_runs(datetime(2026, 11, 11, 9, 0))[1] == ("daily_report", "daily_report:2026-11-11")
