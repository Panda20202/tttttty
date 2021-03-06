import asyncio
from itertools import islice
from typing import Sequence, Tuple, List, TypeVar

from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, Window, ConditionalMargin, ScrollbarMargin
from prompt_toolkit.widgets import CheckboxList
from prompt_toolkit.widgets.base import E

_T = TypeVar("_T")

PAGE_SIZE = 10


async def aislice(iterator, limit):
    items = []
    i = 0
    async for value in iterator:
        if i > limit:
            break
        i += 1
        items.append(value)
    return items


class IterableCheckboxList(CheckboxList):
    def __init__(self, values: Sequence[Tuple[_T, AnyFormattedText]]) -> None:
        pass

    async def _init(self, values: Sequence[Tuple[_T, AnyFormattedText]]) -> None:
        started_values = await aislice(values, 10)

        # started_values = await aislice(values, PAGE_SIZE)
        if not started_values:
            raise IndexError('Values is empty.')
        self.values = started_values
        # current_values will be used in multiple_selection,
        # current_value will be used otherwise.
        self.current_values: List[_T] = []
        self.current_value: _T = started_values[0][0]
        self._selected_index = 0

        async def handler(event):
            if self._selected_index + 1 >= len(self.values):
                self.values.extend(await aislice(values, PAGE_SIZE))
            self._selected_index = min(len(self.values) - 1, self._selected_index + 1)

        async def async_handler(event):
            if handler:
                await handler(event)

            # Tell the application to redraw. We need to do this,
            # because the below event handler won't be able to
            # wait for the task to finish.
            event.app.invalidate()

        # Key bindings.
        kb = KeyBindings()

        @kb.add("up")
        def _up(event: E) -> None:
            self._selected_index = max(0, self._selected_index - 1)

        @kb.add("down")
        def _down(event: E) -> None:
            # if self._selected_index + 1 >= len(self.values):
            #     self.values.extend(islice(values, PAGE_SIZE))
            # self._selected_index = min(len(self.values) - 1, self._selected_index + 1)
            asyncio.get_event_loop().create_task(async_handler(event))

        @kb.add("pageup")
        def _pageup(event: E) -> None:
            w = event.app.layout.current_window
            if w.render_info:
                self._selected_index = max(
                    0, self._selected_index - len(w.render_info.displayed_lines)
                )

        @kb.add("pagedown")
        def _pagedown(event: E) -> None:
            w = event.app.layout.current_window
            if self._selected_index + len(w.render_info.displayed_lines) >= len(self.values):
                self.values.extend(islice(values, PAGE_SIZE))
            if w.render_info:
                self._selected_index = min(
                    len(self.values) - 1,
                    self._selected_index + len(w.render_info.displayed_lines),
                )

        # @kb.add("enter")
        @kb.add(" ")
        def _click(event: E) -> None:
            self._handle_enter()

        # Control and window.
        self.control = FormattedTextControl(
            self._get_text_fragments, key_bindings=kb, focusable=True
        )

        self.window = Window(
            content=self.control,
            style=self.container_style,
            right_margins=[
                ConditionalMargin(
                    margin=ScrollbarMargin(display_arrows=True),
                    filter=Condition(lambda: self.show_scrollbar),
                ),
            ],
            dont_extend_height=True,
        )
