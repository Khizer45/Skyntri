"""Helpers to remove a user's private files when the account is deleted."""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.db.models import User
from app.services.uploads import delete_upload


def collect_user_file_refs(user: User) -> list[str]:
    refs: list[str] = []

    if user.avatar_url:
        refs.append(user.avatar_url)

    refs.extend(a.image_url for a in user.analyses if a.image_url)
    refs.extend(s.image_url for s in user.scans if s.image_url)

    for check in user.progress_checks:
        refs.extend([check.before_image_url, check.after_image_url])

    refs.extend(f"report-file:{r.file_path}" for r in user.reports if r.file_path)
    refs.extend(m.image_url for m in user.chat_messages if m.image_url)

    return refs


def remove_files(refs: list[str]) -> None:
    reports_root = (settings.upload_path / "reports").resolve()

    for ref in refs:
        if not ref:
            continue

        if ref.startswith("report-file:"):
            path = Path(ref.removeprefix("report-file:")).resolve()
            try:
                path.relative_to(reports_root)
            except ValueError:
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            continue

        delete_upload(ref)
