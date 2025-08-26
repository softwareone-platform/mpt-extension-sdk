from functools import wraps

from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def dynamic_trace_span(name_fn):
    """Dynamically create a trace span."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name_fn(*args, **kwargs)
            with tracer.start_as_current_span(span_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
