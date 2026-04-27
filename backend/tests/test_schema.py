import pytest
import jwt
import os
import asyncio
import uuid
from sqlalchemy import text
from backend.database.connection import engine
from backend.supabase_client import supabase as admin_client
from supabase import create_client

# Mark all tests in this file as integration
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_all_tables_exist():
    async with engine.connect() as conn:
        expected_tables = {
            "profiles", "portfolios", "portfolio_positions", "watchlists", 
            "watchlist_items", "saved_backtests", "saved_signals", 
            "notifications", "price_alerts"
        }
        try:
            res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            actual_tables = {row[0] for row in res}
            assert expected_tables.issubset(actual_tables)
        except Exception as e:
            if "information_schema" in str(e) and "sqlite" in str(engine.url):
                pytest.skip("Skipping PostgreSQL specific test on SQLite")
            raise

@pytest.mark.asyncio
async def test_all_indexes_exist():
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"))
            actual_indexes = {row[0] for row in res}
            assert len(actual_indexes) >= 8
        except Exception as e:
            if "pg_indexes" in str(e) and "sqlite" in str(engine.url):
                pytest.skip("Skipping PostgreSQL specific test on SQLite")
            raise

@pytest.mark.asyncio
async def test_rls_enabled_all_tables():
    async with engine.connect() as conn:
        tables = [
            "profiles", "portfolios", "portfolio_positions", "watchlists", 
            "watchlist_items", "saved_backtests", "saved_signals", 
            "notifications", "price_alerts"
        ]
        try:
            for table in tables:
                res = await conn.execute(text(f"SELECT rowsecurity FROM pg_tables WHERE tablename = '{table}'"))
                row = res.fetchone()
                assert row is not None
                assert row[0] is True, f"RLS not enabled on {table}"
        except Exception as e:
            if "pg_tables" in str(e) and "sqlite" in str(engine.url):
                pytest.skip("Skipping PostgreSQL specific test on SQLite")
            raise

@pytest.mark.asyncio
async def test_trigger_exists():
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT trigger_name FROM information_schema.triggers WHERE trigger_name = 'on_auth_user_created'"))
            assert res.fetchone() is not None
        except Exception as e:
            if "information_schema.triggers" in str(e) and "sqlite" in str(engine.url):
                pytest.skip("Skipping PostgreSQL specific test on SQLite")
            raise

@pytest.mark.asyncio
async def test_notifications_type_constraint():
    async with engine.connect() as conn:
        with pytest.raises(Exception):
            await conn.execute(text("INSERT INTO notifications (user_id, type, title, body) VALUES ('00000000-0000-0000-0000-000000000000', 'invalid', 'test', 'test')"))
            await conn.commit()

@pytest.mark.asyncio
async def test_price_alerts_condition_constraint():
    async with engine.connect() as conn:
        with pytest.raises(Exception):
            await conn.execute(text("INSERT INTO price_alerts (user_id, ticker, condition, target_price) VALUES ('00000000-0000-0000-0000-000000000000', 'AAPL', 'neither', 150)"))
            await conn.commit()

@pytest.mark.asyncio
async def test_portfolio_positions_shares_positive():
    async with engine.connect() as conn:
        with pytest.raises(Exception):
            await conn.execute(text("INSERT INTO portfolio_positions (portfolio_id, ticker, shares, avg_cost_price) VALUES ('00000000-0000-0000-0000-000000000000', 'AAPL', -1, 150)"))
            await conn.commit()

def create_user_client(user_id, email):
    secret = os.getenv("SUPABASE_JWT_SECRET")
    token = jwt.encode({"sub": user_id, "email": email, "role": "authenticated"}, secret, algorithm="HS256")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    client = create_client(url, key)
    client.postgrest.auth(token)
    return client

@pytest.mark.asyncio
async def test_rls_user_cannot_read_others_portfolio():
    unique_id = str(uuid.uuid4())[:8]
    email_a = f"user_a_{unique_id}@example.com"
    email_b = f"user_b_{unique_id}@example.com"
    
    # Create real users in auth.users via admin API
    user_a = admin_client.auth.admin.create_user({"email": email_a, "password": "password123", "email_confirm": True})
    user_b = admin_client.auth.admin.create_user({"email": email_b, "password": "password123", "email_confirm": True})
    
    user_a_id = user_a.user.id
    user_b_id = user_b.user.id
    
    try:
        client_b = create_user_client(user_b_id, email_b)
        
        # User A creates a portfolio (admin client bypasses RLS to setup)
        admin_client.table("portfolios").insert({"user_id": user_a_id, "name": "User A Portfolio"}).execute()
        
        # User B queries portfolios
        res_b = client_b.table("portfolios").select("*").execute()
        
        # Assert User B sees nothing belonging to User A
        portfolios_b = [p for p in res_b.data if p['user_id'] == user_a_id]
        assert len(portfolios_b) == 0
    finally:
        # Cleanup
        admin_client.table("portfolios").delete().eq("user_id", user_a_id).execute()
        admin_client.auth.admin.delete_user(user_a_id)
        admin_client.auth.admin.delete_user(user_b_id)

@pytest.mark.asyncio
async def test_rls_notifications_isolated():
    unique_id = str(uuid.uuid4())[:8]
    email_a = f"user_a3_{unique_id}@example.com"
    email_b = f"user_b4_{unique_id}@example.com"
    
    user_a = admin_client.auth.admin.create_user({"email": email_a, "password": "password123", "email_confirm": True})
    user_b = admin_client.auth.admin.create_user({"email": email_b, "password": "password123", "email_confirm": True})
    
    user_a_id = user_a.user.id
    user_b_id = user_b.user.id
    
    try:
        client_a = create_user_client(user_a_id, email_a)
        
        # Setup notifications
        admin_client.table("notifications").insert([{"user_id": user_a_id, "type": "signal", "title": f"A{i}", "body": "msg"} for i in range(5)]).execute()
        admin_client.table("notifications").insert([{"user_id": user_b_id, "type": "signal", "title": f"B{i}", "body": "msg"} for i in range(3)]).execute()
        
        # User A queries
        res_a = client_a.table("notifications").select("*").execute()
        # User A should only see their 5 notifications
        assert len(res_a.data) == 5
        for n in res_a.data:
            assert n['user_id'] == user_a_id
    finally:
        # Cleanup
        admin_client.table("notifications").delete().eq("user_id", user_a_id).execute()
        admin_client.table("notifications").delete().eq("user_id", user_b_id).execute()
        admin_client.auth.admin.delete_user(user_a_id)
        admin_client.auth.admin.delete_user(user_b_id)

