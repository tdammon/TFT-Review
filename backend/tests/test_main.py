from fastapi.testclient import TestClient

def test_read_root(client: TestClient):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to TFT Review API"}

def test_database_connection(client: TestClient):
    """Test the database connection endpoint"""
    response = client.get("/test-db")
    assert response.status_code == 200
    assert response.json()["message"] == "Database connection successful"
    assert response.json()["result"] == 1 