class LLMClient:
    def __init__(self, *args, **kwargs): pass
    async def chat(self, *a, **kw): return type('R',(),{'content':'','tool_calls':()})()
    async def chat_stream(self, *a, **kw):
        yield {'type':'token','data':''}
