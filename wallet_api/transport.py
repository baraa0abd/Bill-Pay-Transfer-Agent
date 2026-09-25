"""In-process HTTP boundary for the mock service; no network server needed."""
import asyncio
import httpx


class LocalWalletTransport:
    def __init__(self,app): self.app=app

    def request(self,method,path,**kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://mock-wallet') as client:
                return await client.request(method,path,**kwargs)
        return asyncio.run(send())

    def get(self,path,**kwargs): return self.request('GET',path,**kwargs)
    def post(self,path,**kwargs): return self.request('POST',path,**kwargs)
