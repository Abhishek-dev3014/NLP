from fastapi.testclient import TestClient
from app.main import app

ARTICLE = {
    "headline": "Federal spending claim",
    "text": "The federal government spends more money on public education than on national defense. The proposed budget will increase education funding by twenty percent next year, according to the statement.",
}


def test_submission_retrieval_dashboard_and_deletion(client):
    response = client.post("/api/analyze/text", json=ARTICLE)
    assert response.status_code == 200, response.text
    report = response.json()
    assert (
        report["prediction"]["probabilities"]
        and report["evidence"]["status"] == "unconfigured"
    )
    assert client.get(f"/api/analyses/{report['id']}").json() == report
    assert client.get("/api/analyses").json()["total"] == 1
    stats = client.get("/api/dashboard/stats").json()
    assert stats["total"] == 1 and sum(i["value"] for i in stats["distribution"]) == 1
    assert stats["activity"][0]["count"] == 1
    assert client.delete(f"/api/analyses/{report['id']}").status_code == 204
    assert client.get("/api/analyses").json()["total"] == 0
    assert client.get(f"/api/analyses/{report['id']}").status_code == 404


def test_history_is_session_isolated(client):
    report = client.post("/api/analyze/text", json=ARTICLE).json()
    with TestClient(app) as stranger:
        assert stranger.get("/api/analyses").json()["total"] == 0
        assert stranger.get(f"/api/analyses/{report['id']}").status_code == 404
        assert stranger.delete(f"/api/analyses/{report['id']}").status_code == 404
        assert stranger.delete("/api/analyses").status_code == 204
    assert client.get("/api/analyses").json()["total"] == 1


def test_invalid_language_empty_and_long_input(client):
    assert client.post("/api/analyze/text", json={"text": ""}).status_code == 422
    assert (
        client.post("/api/analyze/text", json={"text": "a " * 31000}).status_code == 422
    )
    assert (
        client.post(
            "/api/analyze/text",
            json={
                "text": "Le gouvernement annonce une nouvelle politique pour les citoyens et les entreprises du pays. Les habitants demandent des informations supplémentaires sur cette décision importante."
            },
        ).status_code
        == 422
    )


def test_untrained_mode_is_honest(client):
    classifier = app.state.classifier
    app.state.classifier = None
    try:
        result = client.post("/api/analyze/text", json=ARTICLE).json()
        assert result["prediction"]["label"] == "Insufficient Evidence"
        assert (
            result["prediction"]["confidence"] is None
            and result["prediction"]["features"] == []
        )
    finally:
        app.state.classifier = classifier


def test_file_validation_and_extraction(client):
    assert (
        client.post(
            "/api/extract/file",
            files={
                "file": ("article.exe", b"not a document", "application/octet-stream")
            },
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/extract/file",
            files={"file": ("article.pdf", b"not a pdf", "application/pdf")},
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/extract/file",
            files={"file": ("article.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain")},
        ).status_code
        == 413
    )
    extracted = client.post(
        "/api/extract/file",
        files={"file": ("article.txt", ARTICLE["text"].encode(), "text/plain")},
    )
    assert extracted.status_code == 200 and extracted.json()["text"] == ARTICLE["text"]
    result = client.post(
        "/api/analyze/file",
        files={"file": ("article.txt", ARTICLE["text"].encode(), "text/plain")},
    )
    assert result.status_code == 200 and result.json()["input_type"] == "file"


def test_filter_and_clear_history(client):
    client.post("/api/analyze/text", json=ARTICLE)
    assert client.get("/api/analyses?search=Federal").json()["total"] == 1
    assert client.get("/api/analyses?search=Unrelated").json()["total"] == 0
    assert client.get("/api/analyses?search=%25").json()["total"] == 0
    assert client.get("/api/analyses?page=0").status_code == 422
    assert client.delete("/api/analyses").status_code == 204
    assert client.get("/api/dashboard/stats").json()["total"] == 0


def test_metrics_are_from_evaluation(client):
    m = client.get("/api/model/metrics").json()
    assert m["available"] and sum(map(sum, m["confusion_matrix"])) == m["split"]["test"]
    assert 0 <= m["accuracy"] <= 1


def test_wrong_origin_and_cookie_tampering(client):
    assert (
        client.post(
            "/api/analyze/text",
            json=ARTICLE,
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    report = client.post("/api/analyze/text", json=ARTICLE).json()
    client.cookies.clear()
    client.cookies.set("verifact_session", "a" * 48 + ".tampered")
    assert client.get(f"/api/analyses/{report['id']}").status_code == 404


def test_streamed_body_limit(client):
    chunks = (b"x" * (1024 * 1024) for _ in range(6))
    response = client.post(
        "/api/analyze/text",
        content=chunks,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413, response.text


def test_valid_text_pdf_extraction(client):
    from io import BytesIO
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 11 Tf 40 700 Td (" + ARTICLE["text"] + ") Tj ET").encode())
    page[NameObject("/Contents")] = stream
    buffer = BytesIO()
    writer.write(buffer)
    response = client.post(
        "/api/extract/file",
        files={"file": ("article.pdf", buffer.getvalue(), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    assert "federal government" in response.json()["text"]


def test_nlp_lab_does_not_persist_an_analysis(client):
    before = client.get("/api/analyses").json()["total"]
    response = client.post("/api/nlp/explore", json=ARTICLE)
    assert response.status_code == 200 and response.json()["available"]
    assert response.json()["tokens"] and response.json()["summary"]
    assert client.get("/api/analyses").json()["total"] == before


def test_missing_model_does_not_serve_stale_metrics(client):
    classifier = app.state.classifier
    app.state.classifier = None
    try:
        assert client.get("/api/model/metrics").json()["available"] is False
    finally:
        app.state.classifier = classifier
