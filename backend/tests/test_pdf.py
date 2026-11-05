from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.services.pdf_report import generate_report_pdf


def test_pdf_generation():
    # Fake user data
    user = SimpleNamespace(
        full_name="Test User",
        email="test@example.com",
        skin_type="Oily",
    )

    # Fake skin analysis data
    analysis = SimpleNamespace(
        predicted_condition="Acne, Oily Skin",
        confidence_score=91.5,
        severity_level="Moderate",
        explanation="Test analysis explanation.",
        created_at=datetime.now(timezone.utc),
    )

    report_id = "unit-test-report"

    # Run the actual project PDF generation function
    file_path = generate_report_pdf(
        user=user,
        report_id=report_id,
        title="Unit Test Skin Health Report",
        analysis=analysis,
        progress=None,
    )

    pdf_file = Path(file_path)

    # Verify that a path was returned
    assert file_path is not None

    # Verify that the PDF exists
    assert pdf_file.exists()

    # Verify that the file is not empty
    assert pdf_file.stat().st_size > 0

    # Verify that it is actually a PDF
    with open(pdf_file, "rb") as file:
        header = file.read(4)

    assert header == b"%PDF"

    # Clean up the test-generated PDF
    if pdf_file.exists():
        pdf_file.unlink()