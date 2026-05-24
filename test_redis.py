import asyncio
import redis.asyncio as redis
async def t():
    try:
        r = redis.from_url('redis://127.0.0.1:6379/0')
        await r.ping()
        print('ok')
    except Exception as e:
        print(f'error: {e}')

if __name__ == '__main__':
    asyncio.run(t())
