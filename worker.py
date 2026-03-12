import os
import time
import logging

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from rq import Connection, SimpleWorker, Worker

from kb_jobs import QUEUE_NAME


logger = logging.getLogger("contentai.worker")
logging.basicConfig(level=logging.INFO)


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
                worker = worker_class([QUEUE_NAME])
                worker.work(with_scheduler=False)

            logger.warning("Worker exited cleanly; restarting in %ss", backoff_sec)
        except (RedisConnectionError, RedisTimeoutError, OSError) as e:
            logger.warning("Worker lost Redis connection (%s). Restarting in %ss", e, backoff_sec)
        except Exception as e:
            logger.exception("Worker crashed unexpectedly: %s", e)

        time.sleep(backoff_sec)
        backoff_sec = min(backoff_sec * 2, 30)
