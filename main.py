import asyncio
from ProxyPool import ProxyPool, create_proxypool

async def main():
    pp = await create_proxypool(
        max_retry_count=1,
        timeout=10,
        max_concurrent_request=100
    )

if __name__ == "__main__":
    asyncio.run(main())
