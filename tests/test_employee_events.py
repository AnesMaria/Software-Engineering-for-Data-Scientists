"""Database, API and dashboard regression checks."""
from pathlib import Path
import sqlite3
import numpy as np
import pytest
from employee_events import Employee, Team, QueryBase

project_root = Path(__file__).resolve().parents[1]


@pytest.fixture
def db_path():
    return project_root / "python-package" / "employee_events" / "employee_events.db"


@pytest.fixture
def db_conn(db_path):
    connection = sqlite3.connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def table_names(db_conn):
    return [row[0] for row in db_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]


def test_db_exists(db_path):
    assert db_path.is_file()


def test_employee_table_exists(table_names):
    assert "employee" in table_names


def test_team_table_exists(table_names):
    assert "team" in table_names


def test_employee_events_table_exists(table_names):
    assert "employee_events" in table_names


@pytest.mark.parametrize("model", [Employee(), Team()])
def test_queries_match_sql(model, db_conn):
    entity_id = model.names()[0][1]
    assert model.username(entity_id)
    assert isinstance(model, QueryBase)
    events = model.event_counts(entity_id)
    expected = db_conn.execute(
        f"SELECT SUM(positive_events), SUM(negative_events) FROM employee_events WHERE {model.name}_id = ?",
        (entity_id,),
    ).fetchone()
    assert tuple(events[["positive_events", "negative_events"]].sum()) == expected
    assert events.event_date.is_monotonic_increasing
    expected_notes = db_conn.execute(
        f"SELECT COUNT(*) FROM notes WHERE {model.name}_id = ?", (entity_id,),
    ).fetchone()[0]
    assert len(model.notes(entity_id)) == expected_notes
    assert list(model.model_data(entity_id).columns) == ["positive_events", "negative_events"]


def test_parameterized_queries():
    assert Employee().username("1 OR 1=1") == []
    assert Team().event_counts("1 OR 1=1").empty


def test_team_features_are_employee_totals():
    team_id = Team().names()[0][1]
    data = Team().model_data(team_id)
    totals = Team().event_counts(team_id)[["positive_events", "negative_events"]].sum()
    np.testing.assert_array_equal(data.sum().to_numpy(), totals.to_numpy())


@pytest.fixture
def client():
    from starlette.testclient import TestClient
    from report.dashboard import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("path,title", [("/", "Employee Performance"), ("/employee/2", "Employee Performance"), ("/team/2", "Team Performance")])
def test_dashboard(client, path, title):
    response = client.get(path)
    assert response.status_code == 200
    assert title in response.text
    assert response.text.count("data:image/png;base64") == 2
    assert "Manager Notes" in response.text


def test_filters_and_errors(client):
    response = client.get("/update_dropdown", params={"profile_type": "Team"})
    assert response.status_code == 200
    assert "Bravo Team" in response.text
    response = client.post("/update_data", data={"profile_type": "Team", "user-selection": "2"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/team/2"
    assert client.get("/employee/99999").status_code == 404
    assert client.get("/update_dropdown?profile_type=invalid").status_code == 400
    assert client.post("/update_data", data={"profile_type": "Team", "user-selection": "bad"}).status_code == 400
    assert client.get("/assets/report.css").status_code == 200


def test_team_prediction_is_mean_of_individual_probabilities():
    from report.dashboard import BarChart
    from unittest.mock import patch
    data = Team().model_data(2)
    expected = BarChart.predictor.predict_proba(data)[:, 1].mean()
    with patch("matplotlib.axes.Axes.barh") as bar:
        BarChart()(2, Team())
    assert bar.call_args.args[1][0] == pytest.approx(expected)