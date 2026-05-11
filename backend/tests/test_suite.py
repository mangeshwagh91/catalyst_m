import pytest
from fastapi.testclient import TestClient

# Import the fixture client from conftest
@pytest.fixture
def client_fixture(client):
    return client

# ------------------- Reactions Tests -------------------

def test_create_and_get_reaction(client_fixture):
    # Create a new reaction
    reaction_data = {
        "name": "Test Reaction",
        "reactants": ["H2", "O2"],
        "products": ["H2O"],
        "temperature": 298.15,
        "pressure": 1.0,
        "solvent": "water",
        "description": "Combustion test"
    }
    response = client_fixture.post("/api/reactions/", json=reaction_data)
    assert response.status_code == 200
    created = response.json()
    assert created["name"] == reaction_data["name"]
    reaction_id = created["id"]

    # Retrieve the created reaction
    get_resp = client_fixture.get(f"/api/reactions/{reaction_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == reaction_id
    assert fetched["name"] == reaction_data["name"]

def test_list_reactions(client_fixture):
    resp = client_fixture.get("/api/reactions/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "reactions" in data
    assert "total" in data

# ------------------- Catalysts Tests -------------------

def test_retrieve_and_generate_catalysts(client_fixture):
    # Retrieve known catalysts for a dummy reaction
    retrieve_payload = {
        "reaction_id": "dummy-reaction",
        "reactants": ["H2", "O2"],
        "products": ["H2O"],
        "limit": 5
    }
    ret_resp = client_fixture.post("/api/catalysts/retrieve", json=retrieve_payload)
    assert ret_resp.status_code == 200
    ret_data = ret_resp.json()
    assert ret_data["reaction_id"] == "dummy-reaction"
    assert isinstance(ret_data["catalysts"], list)

    # Generate catalyst variants
    gen_payload = {
        "base_catalyst": "CuZnAl",
        "num_variants": 3,
        "optimization_target": "activity",
        "reaction_id": "dummy-reaction"
    }
    gen_resp = client_fixture.post("/api/catalysts/generate", json=gen_payload)
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["num_variants"] == 3
    assert isinstance(gen_data["variants"], list)
    assert "model_version" in gen_data
    assert "vae" in gen_data["model_version"].lower()

# ------------------- Predictions Tests -------------------

def test_rank_and_predict_single(client_fixture):
    # Prepare dummy catalyst list
    catalysts = [
        {"id": "cat1", "name": "Cat A", "composition": "CuZn"},
        {"id": "cat2", "name": "Cat B", "composition": "FeNi"}
    ]
    rank_payload = {
        "catalysts": catalysts,
        "reaction_conditions": {"temperature": 300, "pressure": 1, "solvent": "water"},
        "reaction_id": "dummy-reaction",
        "weights": {"activity": 0.5, "selectivity": 0.3, "stability": 0.2}
    }
    rank_resp = client_fixture.post("/api/predictions/rank", json=rank_payload)
    assert rank_resp.status_code == 200
    rank_data = rank_resp.json()
    assert rank_data["total_catalysts"] == len(catalysts)
    assert isinstance(rank_data["predictions"], list)

    # Predict a single catalyst
    single_payload = {
        "catalyst": {"id": "cat1", "name": "Cat A", "composition": "CuZn"},
        "reaction_conditions": {"temperature": 300, "pressure": 1, "solvent": "water"},
        "reaction_id": "dummy-reaction"
    }
    single_resp = client_fixture.post("/api/predictions/predict-single", json=single_payload)
    assert single_resp.status_code == 200
    single_data = single_resp.json()
    assert single_data["catalyst_id"] == "cat1"

# ------------------- Visualization Tests -------------------

def test_performance_plot_and_dashboard_summary(client_fixture):
    # Dummy predictions list
    preds = [
        {"catalyst_id": "cat1", "catalyst_name": "Cat A", "composition": "CuZn", "source": "known", "activity": 80, "selectivity": 85, "stability": 90, "combined_score": 85, "uncertainty": 0.05},
        {"catalyst_id": "cat2", "catalyst_name": "Cat B", "composition": "FeNi", "source": "generated", "activity": 70, "selectivity": 75, "stability": 80, "combined_score": 75, "uncertainty": 0.1}
    ]
    plot_resp = client_fixture.post("/api/visualization/performance-plot", json={"predictions": preds})
    assert plot_resp.status_code == 200
    plot_data = plot_resp.json()
    assert plot_data["type"] == "plotly"
    assert "plot" in plot_data

    summary_resp = client_fixture.post(
        "/api/visualization/dashboard-summary",
        json={"reaction_id": "dummy-reaction", "predictions": preds},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert isinstance(summary, dict)
    assert "total_catalysts" in summary or "top_5_recommendations" in summary

# ------------------- Experiments Tests -------------------

def test_log_experimental_results_and_export(client_fixture):
    log_payload = {
        "reaction_id": "dummy-reaction",
        "catalyst_id": "cat1",
        "measured_properties": {"activity": 78, "selectivity": 80, "stability": 85},
        "predicted_properties": {"activity": 80, "selectivity": 85, "stability": 90},
        "researcher_name": "Test Scientist",
        "notes": "Initial test"
    }
    log_resp = client_fixture.post("/api/experiments/log-results", json=log_payload)
    assert log_resp.status_code == 200
    log_data = log_resp.json()
    assert log_data["success"] is True
    assert "experiment" in log_data

    export_payload = {
        "reaction_id": "dummy-reaction",
        "catalyst_ids": ["cat1", "cat2"],
        "export_format": "json"
    }
    export_resp = client_fixture.post("/api/experiments/export", json=export_payload)
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["success"] is True
    assert export_data["export"]["export_format"] == "json"
