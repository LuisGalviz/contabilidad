from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthRegister:
    async def test_register_creates_user_and_returns_tokens(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Juan Contador",
                "email": "juan@contaflow.com",
                "password": "seguro1234",
                "tenant_name": "Estudio Contable Juan",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {
            "name": "Ana",
            "email": "ana@test.com",
            "password": "seguro1234",
            "tenant_name": "Estudio Ana",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    async def test_register_short_password_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"name": "A", "email": "a@b.com", "password": "123", "tenant_name": "T"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthLogin:
    async def test_login_with_valid_credentials(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test",
                "email": "test@login.com",
                "password": "password123",
                "tenant_name": "Test Tenant",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@login.com", "password": "password123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test",
                "email": "fail@login.com",
                "password": "correct123",
                "tenant_name": "T",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "fail@login.com", "password": "wrong"},
        )
        assert response.status_code == 401

    async def test_me_returns_user_info(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Me User",
                "email": "me@test.com",
                "password": "password123",
                "tenant_name": "My Firm",
            },
        )
        token = reg.json()["access_token"]
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["email"] == "me@test.com"
