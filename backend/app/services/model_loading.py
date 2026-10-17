"""One lock for every lazy ML model load.

Importing sentence_transformers / transformers and building a model are not safe to do from two threads
at once, even for two different models (errors like "cannot import name ... from 'transformers'" or
"Cannot copy out of meta tensor"). Questions answered in parallel hit exactly that on a cold start.
"""
import threading

load_lock = threading.Lock()


def preimport_ml_libraries() -> None:
    """Import torch and sentence_transformers once, under the lock, right after startup.

    The models themselves still load on first use (they are the big memory cost); only the library imports
    are done early, so that no request has to be the one that performs them while another thread is
    importing too.
    """
    import logging

    log = logging.getLogger(__name__)
    try:
        with load_lock:
            import torch  # noqa: F401
            import sentence_transformers  # noqa: F401
        log.info("ML libraries imported")
    except Exception as exc:  # missing locally; the first request will report it properly
        log.warning("Could not pre-import ML libraries: %s", exc)
