"""
Helper functions and decorators for service layer tasks:
progress tracking, logging, and error handling.
"""
import asyncio
import logging
from typing import Any, Callable, Optional

from ..utils.progress import update_progress

logger = logging.getLogger(__name__)

async def run_stage(
    rec_id: str,
    stage: str,
    func,
    *args,
    to_thread: bool = False,
    log_result: Optional[Callable[[Any], str]] = None,
) -> Any:
    """
    Run a service stage: update progress, log start/end, and execute the function.

    Args:
        rec_id: record ID for progress tracking and logging.
        stage: name of the pipeline stage.
        func: the sync or async function to execute.
        *args: positional args to pass to func.
        to_thread: whether to invoke func via asyncio.to_thread.
        log_result: optional function(result) -> str for result logging.

    Returns:
        The return value from func.

    Raises:
        Any exception raised by func is propagated after logging.
    """
    update_progress(rec_id, stage)
    logger.info(f"[{rec_id}] Starting stage '{stage}'")
    try:
        if to_thread:
            result = await asyncio.to_thread(func, *args)
        else:
            result = await func(*args)
        if log_result:
            logger.info(f"[{rec_id}] Stage '{stage}' result: {log_result(result)}")
        else:
            logger.info(f"[{rec_id}] Completed stage '{stage}'")
        return result
    except Exception:
        logger.exception(f"[{rec_id}] Exception in stage '{stage}'")
        raise

def with_fallback(fallback_func):
    """
    Decorator for service functions that fall back to a default on exception.

    Args:
        fallback_func: call with same args to generate fallback result.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception(f"Service '{func.__name__}' failed, using fallback")
                return fallback_func(*args, **kwargs)

        return wrapper

    return decorator