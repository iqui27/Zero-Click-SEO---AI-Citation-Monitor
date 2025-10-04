from types import SimpleNamespace

from app.api.analytics_routes import _build_semantic_snapshot


class FakeQuery:
    def __init__(self, data):
        self._data = data

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._data


class FakeSession:
    def __init__(self, insights):
        self._insights = insights

    def query(self, _model):
        return FakeQuery(self._insights)


def make_run(run_id: str, category: str | None) -> SimpleNamespace:
    return SimpleNamespace(id=run_id, perceived_value_category=category)


def test_build_semantic_snapshot_basic():
    runs = [
        make_run("run1", "inovacao"),
        make_run("run2", "custo"),
        make_run("run3", "inovacao"),
    ]

    payload = {
        "entities": [
            {"name": "Banco do Brasil", "roles": ["brand"], "confidence": 0.9},
            {"name": "Nubank", "roles": ["competitor"], "confidence": 0.7},
        ],
        "keywords": [
            {"token": "conta digital", "weight": 0.8, "brands": ["Banco do Brasil"]},
            {"token": "anuidade zero", "weight": 0.6, "competitors": ["Nubank"]},
        ],
        "competitors": [
            {"name": "Nubank", "mentions": 2, "score": 1.5},
        ],
        "perception": {"primary_category": "inovacao", "confidence": 0.8},
    }

    insights = [SimpleNamespace(run_id="run1", payload=payload)]
    session = FakeSession(insights)

    snapshot = _build_semantic_snapshot(runs, session)

    assert snapshot["runs_analyzed"] == 1
    assert snapshot["perception_distribution"][0]["category"] == "inovacao"
    assert snapshot["brand_ranking"][0]["name"] == "Banco do Brasil"
    assert snapshot["top_keywords"][0]["token"] == "conta digital"
    assert snapshot["competitors"][0]["name"] == "Nubank"
