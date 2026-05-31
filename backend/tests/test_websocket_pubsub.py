import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from websocket_app.manager import ConnectionManager

@pytest.mark.asyncio
async def test_broadcast_to_channel_with_redis():
    """Verify that when Redis is connected, broadcast_to_channel publishes ticks to the Pub/Sub backplane."""
    manager = ConnectionManager()
    
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()
    
    # Register dummy user (use pure AsyncMock without spec restrictions)
    manager.active_connections["client-123"] = AsyncMock()
    manager.subscribe("client-123", "market")
    
    with patch("infrastructure.redis_client.redis_client.redis", mock_redis):
        message = {"type": "market_update", "ticker": "AAPL", "price": 180.0}
        await manager.broadcast_to_channel("market", message)
        
        # Verify message was published to Redis channel
        mock_redis.publish.assert_called_once()
        called_args, _ = mock_redis.publish.call_args
        assert called_args[0] == "pubsub:market:ticks"
        
        # Verify message format contains envelope channel and raw message
        payload = json.loads(called_args[1])
        assert payload["channel"] == "market"
        assert payload["message"] == message

@pytest.mark.asyncio
async def test_broadcast_to_channel_fallback():
    """Verify that when Redis is offline, broadcast_to_channel falls back to direct local delivery."""
    manager = ConnectionManager()
    
    # Setup local active mock WebSocket using pure AsyncMock
    mock_ws = AsyncMock()
    manager.active_connections["client-123"] = mock_ws
    manager.subscribe("client-123", "market")
    
    # Ensure redis is None (offline)
    with patch("infrastructure.redis_client.redis_client.redis", None):
        message = {"type": "market_update", "ticker": "AAPL", "price": 180.0}
        await manager.broadcast_to_channel("market", message)
        
        # Verify direct local broadcast succeeded
        mock_ws.send_text.assert_called_once()
        sent_payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent_payload["ticker"] == "AAPL"
        assert sent_payload["price"] == 180.0

@pytest.mark.asyncio
async def test_pubsub_listener_message_routing():
    """Verify that the background listener pulls messages from Redis and routes them locally."""
    manager = ConnectionManager()
    
    # Mock WebSocket subscriber using pure AsyncMock
    mock_ws = AsyncMock()
    manager.active_connections["client-123"] = mock_ws
    manager.subscribe("client-123", "ticker:AAPL")
    
    # Mock Redis pubsub interface
    mock_pubsub = AsyncMock()
    
    # Mock a single tick message envelope returned by Redis
    redis_message = {
        "type": "message",
        "data": json.dumps({
            "channel": "ticker:AAPL",
            "message": {"ticker": "AAPL", "price": 185.5}
        })
    }
    
    # Return the message once, then return None to simulate idle/no new ticks
    mock_pubsub.get_message = AsyncMock(side_effect=[redis_message, None, None, None, None])
    
    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub
    
    with patch("infrastructure.redis_client.redis_client.redis", mock_redis):
        # Run listener with a short timeout to let it process the message and then exit
        try:
            await asyncio.wait_for(manager.start_pubsub_listener(), timeout=0.3)
        except asyncio.TimeoutError:
            pass
            
        # Verify local WebSocket received the routed message
        mock_ws.send_text.assert_called_once()
        received_data = json.loads(mock_ws.send_text.call_args[0][0])
        assert received_data["price"] == 185.5
        assert received_data["ticker"] == "AAPL"
