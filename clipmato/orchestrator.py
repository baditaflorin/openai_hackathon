"""Pipeline orchestration framework for Clipmato:
Defines a Step interface and Pipeline class so stages are pluggable components.
"""
import asyncio
from typing import Any, Callable, Sequence, Union

from .services.service_utils import run_stage


class Step:
    """
    A single pipeline stage wrapping a service function with progress tracking.
    """

    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        input_keys: Sequence[str],
        output_keys: Union[str, Sequence[str]],
        to_thread: bool = False,
        log_result: Callable[[Any], str] | None = None,
    ):
        self.name = name
        self.func = func
        self.input_keys = list(input_keys)
        if isinstance(output_keys, (list, tuple)):
            self.output_keys = list(output_keys)
        else:
            self.output_keys = [output_keys]
        self.to_thread = to_thread
        self.log_result = log_result

    async def run(self, ctx: dict[str, Any]) -> None:
        args = [ctx[key] for key in self.input_keys]
        result = await run_stage(
            ctx["rec_id"],
            self.name,
            self.func,
            *args,
            to_thread=self.to_thread,
            log_result=self.log_result,
        )
        if len(self.output_keys) == 1:
            ctx[self.output_keys[0]] = result
        else:
            for key, val in zip(self.output_keys, result):
                ctx[key] = val


class Pipeline:
    """
    Orchestrates a sequence of Step instances.
    """

    def __init__(self, steps: list[Step]):
        self.steps = steps

    async def run(self, ctx: dict[str, Any]) -> dict[str, Any]:
        for step in self.steps:
            await step.run(ctx)
        return ctx