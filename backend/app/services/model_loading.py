"""One lock for every lazy ML model load.

Importing sentence_transformers / transformers and building a model are not safe to do from two threads
at once, even for two different models (errors like "cannot import name ... from 'transformers'" or
"Cannot copy out of meta tensor"). Questions answered in parallel hit exactly that on a cold start.
"""
import threading

load_lock = threading.Lock()
