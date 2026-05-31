import asyncio
import time
from datetime import datetime, timezone
import httpx
from core.logger import logger

# Global calibrated clock offset in seconds (network_time - local_time)
CLOCK_OFFSET = 0.0

async def calibrate_time_offset() -> float:
    """
    Queries public time APIs to calculate the system clock drift offset.
    Updates the global CLOCK_OFFSET variable.
    """
    global CLOCK_OFFSET
    urls = [
        "http://worldtimeapi.org/api/timezone/Etc/UTC",
        "https://cloudflare.com/cdn-cgi/trace", # Fast fallback
        "https://www.google.com" # Ultimate fallback using Date header
    ]
    
    timeout = httpx.Timeout(3.0)
    
    for url in urls:
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=timeout) as client:
                if "worldtimeapi" in url:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        # worldtimeapi returns unixtime as a float/int
                        network_time = float(data["unixtime"])
                        # Adjust for round-trip time approximation
                        rtt = time.time() - start_time
                        calibrated_network_time = network_time + (rtt / 2.0)
                        local_time = time.time()
                        CLOCK_OFFSET = calibrated_network_time - local_time
                        logger.info(f"[TimeSync] Calibrated offset via WorldTimeAPI: {CLOCK_OFFSET:+.4f}s (RTT: {rtt:.4f}s)")
                        return CLOCK_OFFSET
                elif "cloudflare" in url:
                    # Cloudflare trace endpoint doesn't directly give timestamp in simple JSON,
                    # but we can do a HEAD request and read the 'Date' header.
                    response = await client.head("https://cloudflare.com")
                    date_str = response.headers.get("Date")
                    if date_str:
                        # e.g., "Sat, 30 May 2026 08:00:00 GMT"
                        network_time = email_date_to_timestamp(date_str)
                        rtt = time.time() - start_time
                        calibrated_network_time = network_time + (rtt / 2.0)
                        local_time = time.time()
                        CLOCK_OFFSET = calibrated_network_time - local_time
                        logger.info(f"[TimeSync] Calibrated offset via Cloudflare Date Header: {CLOCK_OFFSET:+.4f}s (RTT: {rtt:.4f}s)")
                        return CLOCK_OFFSET
                else:
                    # Fallback HEAD request to Google
                    response = await client.head(url)
                    date_str = response.headers.get("Date")
                    if date_str:
                        network_time = email_date_to_timestamp(date_str)
                        rtt = time.time() - start_time
                        calibrated_network_time = network_time + (rtt / 2.0)
                        local_time = time.time()
                        CLOCK_OFFSET = calibrated_network_time - local_time
                        logger.info(f"[TimeSync] Calibrated offset via Google Date Header: {CLOCK_OFFSET:+.4f}s (RTT: {rtt:.4f}s)")
                        return CLOCK_OFFSET
        except Exception as e:
            logger.warning(f"[TimeSync] Failed to query time service {url}: {e}")
            
    logger.warning("[TimeSync] All time calibration endpoints failed. Using 0.0 offset.")
    CLOCK_OFFSET = 0.0
    return CLOCK_OFFSET

def email_date_to_timestamp(date_str: str) -> float:
    """Helper to parse RFC 2822 date formats from HTTP headers to a Unix timestamp."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.timestamp()
    except Exception:
        # Fallback manual parsing if needed
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT")
        return dt.replace(tzinfo=timezone.utc).timestamp()

def offset_calibrated_now() -> float:
    """Returns the calibrated atomic epoch time in seconds."""
    return time.time() + CLOCK_OFFSET

def offset_calibrated_datetime() -> datetime:
    """Returns the calibrated atomic datetime in UTC timezone."""
    return datetime.fromtimestamp(offset_calibrated_now(), tz=timezone.utc)
