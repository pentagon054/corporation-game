"""Body limits at ASGI receive boundary, including chunked requests."""
from starlette.responses import JSONResponse

class BodyLimitMiddleware:
    def __init__(self, app, limit=65536):self.app,self.limit=app,limit
    async def __call__(self, scope, receive, send):
        if scope['type']!='http' or not scope['path'].startswith('/api/'):
            return await self.app(scope,receive,send)
        chunks=[];total=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            total+=len(message.get('body',b''))
            if total>self.limit:
                return await JSONResponse({'detail':'Request body too large'},status_code=413)(scope,receive,send)
            chunks.append(message)
            if not message.get('more_body',False):break
        async def replay():
            if chunks:return chunks.pop(0)
            return await receive()
        await self.app(scope,replay,send)
