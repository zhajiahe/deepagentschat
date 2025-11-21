import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestFilesAPI:
    @pytest.mark.asyncio
    async def test_upload_file(self, client: TestClient, auth_headers: dict):
        # Prepare a temporary file
        filename = "test_upload.txt"
        content = b"Hello world"
        files = {"file": (filename, content, "text/plain")}

        response = client.post("/api/v1/files/upload", files=files, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["filename"] == filename
        assert data["size"] == len(content)

    @pytest.mark.asyncio
    async def test_list_files(self, client: TestClient, auth_headers: dict):
        # Ensure we have at least one file (upload first)
        filename = "test_list.txt"
        content = b"List me"
        client.post("/api/v1/files/upload", files={"file": (filename, content, "text/plain")}, headers=auth_headers)

        response = client.get("/api/v1/files/list", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data["files"]) >= 1
        filenames = [f["filename"] for f in data["files"]]
        assert filename in filenames

    @pytest.mark.asyncio
    async def test_read_file(self, client: TestClient, auth_headers: dict):
        filename = "test_read.txt"
        content = b"Read me"
        client.post("/api/v1/files/upload", files={"file": (filename, content, "text/plain")}, headers=auth_headers)

        response = client.get(f"/api/v1/files/read/{filename}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["content"] == content.decode()

    @pytest.mark.asyncio
    async def test_delete_file(self, client: TestClient, auth_headers: dict):
        filename = "test_delete.txt"
        content = b"Delete me"
        client.post("/api/v1/files/upload", files={"file": (filename, content, "text/plain")}, headers=auth_headers)

        response = client.delete(f"/api/v1/files/{filename}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

        # Verify deletion
        response = client.get("/api/v1/files/list", headers=auth_headers)
        filenames = [f["filename"] for f in response.json()["data"]["files"]]
        assert filename not in filenames
