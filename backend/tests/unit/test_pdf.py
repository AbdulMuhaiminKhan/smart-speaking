import pytest

from app.schemas.metrics import TimePoint
from app.services import charts, pdf
from tests.unit.test_report_llm import TEXT, base_report


def test_line_chart_breaks_on_missing_values() -> None:
    pts = [
        TimePoint(t=0, value=1),
        TimePoint(t=1, value=2),
        TimePoint(t=2, value=None),
        TimePoint(t=3, value=3),
        TimePoint(t=4, value=2),
    ]
    svg = charts.line_chart(pts)
    assert svg is not None and svg.count("<path") == 2


def test_line_chart_needs_two_points() -> None:
    assert charts.line_chart([TimePoint(t=0, value=1)]) is None


def test_radar_lists_every_category() -> None:
    svg = charts.radar([("Voice", 80), ("Pacing", None), ("Language", 50)])
    assert svg.count("<text") == 6 and "–" in svg


def _weasyprint_ok() -> bool:
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True


def test_report_html_and_pdf() -> None:
    html = pdf.render_html(
        base_report(),
        title="My <pitch>",
        created="6 Nov 2026",
        duration_s=65,
        transcript_text=TEXT,
        pacing={"wpm_series": [{"t": 10, "value": 140}, {"t": 15, "value": 150}]},
    )
    assert "My &lt;pitch&gt;" in html  # escaped
    assert "Cut filler words" in html
    assert "Pace" in html and "<svg" in html
    if not _weasyprint_ok():
        pytest.skip("Pango libraries not on the library path (on macOS: make test sets it)")
    data = pdf.render_pdf(html)
    assert data.startswith(b"%PDF") and len(data) > 5000


def test_pdf_endpoint_not_ready(client) -> None:  # type: ignore[no-untyped-def]
    import io

    sid = client.post(
        "/api/sessions", files={"file": ("a.mp4", io.BytesIO(b"x"), "video/mp4")}
    ).json()["id"]
    res = client.get(f"/api/sessions/{sid}/report.pdf")
    assert res.status_code == 404 and res.json()["code"] == "not_ready"
