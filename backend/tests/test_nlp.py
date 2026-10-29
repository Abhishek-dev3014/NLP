import numpy as np
import pytest
from app.ml.preprocessing import clean_text
from app.ml.classifier import load_classifier, BaselineClassifier
from app.core.config import ROOT
from app.schemas.analysis import TextInput, Prediction
from app.services.linguistics import analyze_language


def test_cleaning_preserves_negation_unicode_and_entities():
    assert (
        clean_text("<p>  The budget is NOT final &amp;  Ａ </p><script>bad()</script>")
        == "The budget is NOT final & A"
    )


@pytest.mark.parametrize("text", ["", "short text", "   <p></p>"])
def test_short_inputs_are_rejected(text):
    with pytest.raises(ValueError):
        TextInput(text=text)


def test_legacy_inference_and_linear_explanation_consistency():
    model = BaselineClassifier(str(ROOT / "artifacts/baseline.joblib"))
    assert model is not None, "Train the baseline before running integration tests."
    text = "The federal government budget increased spending on public education by twenty percent this year."
    prediction = Prediction.model_validate(model.predict(text))
    assert abs(sum(prediction.probabilities.values()) - 1) < 1e-10
    assert prediction.calibrated is False and prediction.features
    x = model.pipeline.named_steps["tfidf"].transform([text])
    weights = model.pipeline.named_steps["classifier"].coef_[0]
    logit = float(
        (x @ weights)[0] + model.pipeline.named_steps["classifier"].intercept_[0]
    )
    assert np.isclose(1 / (1 + np.exp(-logit)), prediction.probabilities["misleading"])
    names = model.pipeline.named_steps["tfidf"].get_feature_names_out()
    for feature in prediction.features:
        idx = list(names).index(feature.term)
        assert abs(feature.contribution - x[0, idx] * weights[idx]) < 1e-6


def test_legacy_out_of_domain_is_not_given_reliable_label():
    result = BaselineClassifier(str(ROOT / "artifacts/baseline.joblib")).predict(
        "A delicious cake with chocolate icing and fresh strawberries was prepared for the celebration today."
    )
    assert result["label"] == "Insufficient Evidence" and result["in_domain"] is False


def test_language_highlights_and_claims_are_exact_offsets():
    text = "Shocking news: the government has guaranteed a 20 percent tax reduction for everyone this year."
    insights, highlights, claims = analyze_language(text)
    assert insights["emotional_indicator"] == 1 and insights["certainty_indicator"] == 2
    for h in highlights:
        assert text[h["start"] : h["end"]] == h["text"]
    assert claims and text[claims[0]["start"] : claims[0]["end"]] == claims[0]["text"]
    assert insights["subjectivity_score"] is None


def test_trained_linguistic_pipeline_preserves_original_spans():
    from app.services.nlp import explore

    text = "Maya visited the city library in London on Monday. She borrowed three books about renewable energy. The library runs a reading group for local students."
    report = explore(text)
    assert report["available"]
    assert any(
        e["text"] == "London" and e["label"] == "GPE" for e in report["entities"]
    )
    assert any(
        t["text"] == "borrowed" and t["lemma"] == "borrow" and t["pos"] == "VERB"
        for t in report["tokens"]
    )
    for collection in ("summary", "entities", "tokens"):
        for item in report[collection]:
            assert text[item["start"] : item["end"]] == item["text"]
    assert report["summary"] and len(report["summary"]) <= 3
    assert any(d["relation"] == "ROOT" for d in report["dependencies"])


def test_long_article_has_an_article_level_prediction():
    text = (
        "The federal government has proposed a new budget for public schools this year. "
        * 20
    )
    result = load_classifier().predict(text)
    assert result["assessment_scope"] == "article_screening"
    assert result["confidence"] is not None and result["probabilities"] is not None
    assert result["factual_status"] == "Not independently verified"
    assert result["features"]


def test_calibrated_challenger_group_scores_reconstruct_probability():
    import joblib
    from app.core.config import ROOT
    from app.ml.calibrated import CalibratedClassifier

    model = CalibratedClassifier(joblib.load(ROOT / "artifacts/v2/model.joblib"))
    result = model.predict(
        "The federal government budget increased spending on public education by twenty percent this year."
    )
    assert result["calibrated"] and result["in_domain"]
    logit = sum(result["score_breakdown"].values())
    assert np.isclose(1 / (1 + np.exp(-logit)), result["probabilities"]["misleading"])
    assert (
        result["score_breakdown"]["semantic"] == 0
    )  # Validation selected a lexical model.
    assert all(
        " " not in f["term"] or len(f["term"].split()) == 2 for f in result["features"]
    )


def test_serving_policy_matches_evaluation_artifact():
    model = load_classifier()
    assert model.metrics["version"] == model.metadata["version"]
    assert (
        model.metadata["threshold"] == model.metrics["confidence_policy"]["threshold"]
    )
    policy = model.metrics["confidence_policy"]
    assert (
        policy["test_count"] / model.metrics["split"]["test"] == policy["test_coverage"]
    )


def test_article_calibrated_contributions_and_confidence_are_real():
    model = load_classifier()
    text = "The city council published its annual transport report on Tuesday. Officials said the document contains spending figures and proposed changes to local bus services. Residents can review the original report before a public meeting scheduled for next month."
    result = Prediction.model_validate(model.predict(text))
    assert result.assessment_scope == "article_screening" and result.calibrated
    logit = sum(result.score_breakdown.values())
    assert np.isclose(1 / (1 + np.exp(-logit)), result.probabilities["misleading"])
    assert np.isclose(result.confidence, max(result.probabilities.values()))
    assert result.factual_status == "Not independently verified"
    assert "Indian news" in result.evaluated_domain


def test_article_short_text_cannot_receive_definitive_class():
    result = load_classifier().predict(
        "The government will increase education funding next year according to a new budget proposal."
    )
    assert result["label"] == "Needs Further Verification"
    assert (
        result["probabilities"] is not None
    )  # Preliminary estimate, explicitly labeled.


def test_article_benchmark_manifest_has_no_group_overlap():
    import json

    manifest = json.loads((ROOT / "artifacts/articles/split-manifest.json").read_text())
    groups = {}
    for row in manifest:
        previous = groups.setdefault(row["group"], row["split"])
        assert previous == row["split"]
    m = load_classifier().metrics
    assert len(manifest) == m["dataset_size"] == sum(m["split"].values())
    assert sum(map(sum, m["confusion_matrix"])) == m["split"]["test"]
    assert m["calibrated"] and m["split"]["calibration"] > 0
