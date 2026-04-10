import json
import os
import time
import logging
import traceback

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from rq import Connection, SimpleWorker, Worker, Queue

from kb_jobs import QUEUE_NAME


logger = logging.getLogger("contentai.worker")
logging.basicConfig(level=logging.INFO)

DEAD_LETTER_QUEUE = os.getenv("DEAD_LETTER_QUEUE", "dead_letter")
# How long to keep dead-letter entries in Redis (default 7 days)
DLQ_TTL_SEC = int(os.getenv("DLQ_TTL_SEC", str(7 * 86400)))


def _dead_letter_handler(job, exc_type, exc_value, tb):
    """Custom RQ exception handler: log the failure and push a summary into
    the dead-letter queue so ops can inspect / retry later.

    Returning *True* tells RQ we've handled the exception and it should NOT
    move the job to the default FailedJobRegistry (avoids double-tracking).
    Returning *False* would let RQ do its default handling as well.
    """
    job_id = getattr(job, 'id', 'unknown')
    func_name = getattr(job, 'func_name', 'unknown')
    job_args = getattr(job, 'args', ())

    logger.error(
        "Job %s (%s) failed — moving to dead-letter queue '%s'. Error: %s",
        job_id, func_name, DEAD_LETTER_QUEUE, exc_value,
    )

    try:
        conn = job.connection
        dlq_entry = json.dumps({
            'job_id': job_id,
            'func_name': func_name,
            'args': [str(a) for a in job_args],
            'error_type': exc_type.__name__ if exc_type else 'Unknown',
            'error_message': str(exc_value),
            'traceback': traceback.format_exception(exc_type, exc_value, tb)[-3:],
            'failed_at': int(time.time()),
        })
        # Use a Redis list as the DLQ; each entry auto-expires via a per-key TTL
        # on a hash (lists don't support per-element TTL, so we use a sorted set
        # with score = timestamp so old entries can be pruned).
        conn.zadd(
            f"rq:dlq:{DEAD_LETTER_QUEUE}",
            {dlq_entry: time.time()},
        )
        # Prune entries older than DLQ_TTL_SEC
        cutoff = time.time() - DLQ_TTL_SEC
        conn.zremrangebyscore(f"rq:dlq:{DEAD_LETTER_QUEUE}", 0, cutoff)
    except Exception as dlq_err:
        logger.exception("Failed to write to dead-letter queue: %s", dlq_err)

    # Return False so RQ also records the failure in its FailedJobRegistry
    # (belt-and-suspenders — the DLQ is for ops visibility, the registry for
    # programmatic retries via `rq requeue`).
    return False


if __name__ == "__main__":
    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))

    socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
    health_check_interval = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))

    # macOS fork() safety: use non-forking worker to avoid objc initialize crash.
    # Linux/production keeps standard Worker unless overridden.
    use_simple_worker = os.getenv("RQ_SIMPLE_WORKER", "").lower() in {"1", "true", "yes"}
    if os.getenv("RQ_SIMPLE_WORKER", "") == "" and os.uname().sysname.lower() == "darwin":
        use_simple_worker = True

    worker_class = SimpleWorker if use_simple_worker else Worker

    backoff_sec = 2

    while True:
        connection: Redis = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=None,
            socket_keepalive=True,
            health_check_interval=health_check_interval,
        )

        try:
            connection.ping()
            logger.info(
                "Starting RQ worker on %s:%s db=%s queue=%s class=%s",
                redis_host,
                redis_port,
                redis_db,
                QUEUE_NAME,
                worker_class.__name__,
            )

            with Connection(connection):
                worker = worker_class(
                    [QUEUE_NAME],
                    exception_handlers=[_dead_letter_handler],
                )
                worker.work(with_scheduler=False)

            logger.warning("Worker exited cleanly; restarting in %ss", backoff_sec)
        except (RedisConnectionError, RedisTimeoutError, OSError) as e:
            logger.warning("Worker lost Redis connection (%s). Restarting in %ss", e, backoff_sec)
        except Exception as e:
            logger.exception("Worker crashed unexpectedly: %s", e)

        time.sleep(backoff_sec)
        backoff_sec = min(backoff_sec * 2, 30)
