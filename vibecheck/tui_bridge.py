from __future__ import annotations

import inspect
from typing import Any, Callable

class TuiBridge:
    """Adapts SessionBridge events to a Textual-style event handler."""

    def __init__(
        self,
        event_handler: Any,
        *,
        loading_state_getter: Callable[[], bool] | None = None,
        loading_widget_getter: Callable[[], Any] | None = None,
    ) -> None:
        self._event_handler = event_handler
        self._loading_state_getter = loading_state_getter or (lambda: False)
        self._loading_widget_getter = loading_widget_getter or (lambda: None)

    async def _dispatch(self, event: object) -> None:
        handle_event = getattr(self._event_handler, "handle_event", None)
        if not callable(handle_event):
            raise TypeError("event_handler must define a callable handle_event(event, **kwargs)")

        maybe_awaitable = handle_event(
            event,
            loading_active=self._loading_state_getter(),
            loading_widget=self._loading_widget_getter(),
        )
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    async def on_bridge_event(self, event: object) -> None:
        await self._dispatch(event)

    async def on_bridge_raw_event(self, event: object) -> None:
        await self._dispatch(event)
