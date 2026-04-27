import pytest
from unittest.mock import MagicMock, patch
from auth import sign_up, sign_in, sign_out

@pytest.fixture
def mock_supabase():
    with patch('auth.supabase') as mock:
        yield mock

@pytest.mark.asyncio
async def test_signup_calls_supabase_auth(mock_supabase):
    email = "test@example.com"
    password = "password123"
    full_name = "Test User"
    
    # Mocking the response
    mock_supabase.auth.sign_up.return_value = MagicMock(user=MagicMock(id="uuid"), error=None)
    
    await sign_up(email, password, full_name)
    
    mock_supabase.auth.sign_up.assert_called_once_with({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}}
    })

@pytest.mark.asyncio
async def test_login_calls_supabase_auth(mock_supabase):
    email = "test@example.com"
    password = "password123"
    
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(session=MagicMock(), error=None)
    
    await sign_in(email, password)
    
    mock_supabase.auth.sign_in_with_password.assert_called_once_with({
        "email": email,
        "password": password
    })

@pytest.mark.asyncio
async def test_signout_calls_supabase_auth(mock_supabase):
    await sign_out()
    mock_supabase.auth.sign_out.assert_called_once()
