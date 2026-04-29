import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, Base


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_openapi_docs_accessible():
    response = client.get("/docs")
    assert response.status_code == 200


def test_datasets_empty_on_fresh_db():
    response = client.get("/api/v1/datasets/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0


def test_experiments_empty_on_fresh_db():
    response = client.get("/api/v1/experiments/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 0
