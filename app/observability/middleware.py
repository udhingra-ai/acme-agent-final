import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from observability.logging_utils import log_event

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id  # expose to route handlers for agent pipeline
        start = time.time()
        response = await call_next(request)
        elapsed_ms = round((time.time() - start) * 1000, 2)
        response.headers['X-Trace-Id'] = trace_id
        log_event('request_trace', {'path': request.url.path, 'method': request.method, 'trace_id': trace_id, 'status_code': response.status_code, 'elapsed_ms': elapsed_ms})
        return response
