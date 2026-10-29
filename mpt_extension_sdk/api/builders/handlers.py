from inspect import isawaitable


async def resolve_handler_result(handler_result: object) -> object:
    """Return the handler result, awaiting it when the handler is a coroutine."""
    if isawaitable(handler_result):
        return await handler_result
    return handler_result
