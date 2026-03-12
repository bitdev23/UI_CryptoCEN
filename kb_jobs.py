import json
import logging
import os
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from rq import Queue, get_current_job
from rq.job import Job

load_dotenv()

logger = logging.getLogger("contentai.kb_jobs")

QUEUE_NAME = os.getenv("KB_QUEUE_NAME", "kb_training")
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
DEFAULT_JOB_TIMEOUT = int(os.getenv("KB_JOB_TIMEOUT", "1800"))
KB_CHUNK_SIZE = int(os.getenv("KB_CHUNK_SIZE", "1800"))
KB_CHUNK_OVERLAP = int(os.getenv("KB_CHUNK_OVERLAP", "200"))
KB_MAX_CHUNKS_PER_FILE = int(os.getenv("KB_MAX_CHUNKS_PER_FILE", "250"))


def get_user_pdf_dir(user_id: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "data", "pdfs", user_id)


def resolve_local_kb_path(storage_path: str, filename: str, user_id: str) -> str:
    user_dir = os.path.abspath(get_user_pdf_dir(user_id))
    if storage_path and isinstance(storage_path, str) and storage_path.startswith("local/"):
        rel_path = storage_path[len("local/"):].lstrip("/").replace("\\", "/")
        candidate = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", rel_path))
        if candidate.startswith(user_dir + os.sep):
            return candidate
    return os.path.join(user_dir, filename)


def _current_key(user_id: str) -> str:
    return f"kb:training:current:{user_id}"


def _status_key(user_id: str) -> str:
    return f"kb:training:status:{user_id}"


def get_redis_connection() -> Redis:
    return Redis.from_url(
        DEFAULT_REDIS_URL,
        decode_responses=False,
        socket_connect_timeout=2,
        socket_timeout=5,
        health_check_interval=30,
    )


def _decode_redis_value(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _set_status(connection: Redis, user_id: str, payload: Dict) -> None:
    payload = {
        **payload,
        "updated_at": int(time.time()),
    }
    connection.set(_status_key(user_id), json.dumps(payload), ex=86400)


def _get_status(connection: Redis, user_id: str) -> Dict:
    raw = connection.get(_status_key(user_id))
    if not raw:
        return {}
    try:
        raw_text = _decode_redis_value(raw)
        return json.loads(raw_text)
    except Exception:
        return {}


def _is_job_running(job: Optional[Job]) -> bool:
    if not job:
        return False
    return job.get_status() in {"queued", "deferred", "started"}


def enqueue_kb_training_job(user_id: str, mode: str, filepaths: Optional[List[str]] = None) -> Dict:
    if mode not in {"full", "incremental"}:
        return {
            "success": False,
            "message": "Invalid training mode"
        }

    try:
        connection = get_redis_connection()
        connection.ping()

        current_job_id = _decode_redis_value(connection.get(_current_key(user_id)))
        if current_job_id:
            job = Job.fetch(current_job_id, connection=connection)
            if _is_job_running(job):
                return {
                    "success": False,
                    "already_running": True,
                    "job_id": current_job_id,
                    "message": "Training is already in progress. Please wait and refresh status."
                }
            connection.delete(_current_key(user_id))

        queue = Queue(QUEUE_NAME, connection=connection, default_timeout=DEFAULT_JOB_TIMEOUT)
        job = queue.enqueue(
            process_kb_training_job,
            user_id,
            mode,
            filepaths or [],
            job_timeout=DEFAULT_JOB_TIMEOUT,
            result_ttl=86400,
            failure_ttl=86400,
        )

        connection.set(_current_key(user_id), job.id, ex=max(DEFAULT_JOB_TIMEOUT * 2, 1800))
        _set_status(connection, user_id, {
            "in_progress": True,
            "status": "queued",
            "error": None,
            "job_id": job.id,
            "mode": mode,
            "started_at": int(time.time()),
            "finished_at": None,
        })

        return {
            "success": True,
            "job_id": job.id,
            "message": "Training queued"
        }
    except RedisConnectionError as e:
        logger.warning("KB queue unavailable: %s", e)
        return {
            "success": False,
            "message": f"Queue unavailable: {str(e)}"
        }
    except Exception as e:
        logger.exception("Failed to enqueue KB training job")
        return {
            "success": False,
            "message": f"Queue unavailable: {str(e)}"
        }


def get_kb_training_status(user_id: str) -> Dict:
    default = {
        "in_progress": False,
        "status": "idle",
        "error": None,
        "job_id": None,
        "started_at": None,
        "finished_at": None,
        "queue_available": True,
    }

    try:
        connection = get_redis_connection()
        connection.ping()

        status = {**default, **_get_status(connection, user_id)}
        current_job_id = _decode_redis_value(connection.get(_current_key(user_id)))

        if current_job_id:
            status["job_id"] = current_job_id
            try:
                job = Job.fetch(current_job_id, connection=connection)
                job_status = job.get_status()
                if job_status in {"queued", "deferred", "started"}:
                    status["in_progress"] = True
                    status["status"] = "running" if job_status == "started" else "queued"
                elif job_status == "finished":
                    status["in_progress"] = False
                    status["status"] = "completed"
                    connection.delete(_current_key(user_id))
                elif job_status in {"failed", "stopped", "canceled"}:
                    status["in_progress"] = False
                    status["status"] = "failed"
                    status["error"] = status.get("error") or f"Job {job_status}"
                    connection.delete(_current_key(user_id))
            except Exception:
                connection.delete(_current_key(user_id))

        return status
    except Exception as e:
        return {
            **default,
            "status": "queue_unavailable",
            "error": str(e),
            "queue_available": False,
        }


def process_kb_training_job(user_id: str, mode: str = "full", filepaths: Optional[List[str]] = None) -> Dict:
    connection = get_redis_connection()
    job = get_current_job()
    job_id = job.id if job else None

    _set_status(connection, user_id, {
        "in_progress": True,
        "status": "running",
        "error": None,
        "job_id": job_id,
        "mode": mode,
        "started_at": int(time.time()),
        "finished_at": None,
    })

    try:
        from rag_system_pgvector import RAGStore
        from pdf_processor import load_document, chunk_text

        rag = RAGStore(user_id=user_id)

        if mode == "full":
            existing_records = rag.db.list_kb_files(user_id)
            paths_to_process = []
            for record in existing_records:
                filepath = resolve_local_kb_path(
                    record.get("storage_path") or "",
                    record.get("filename") or "",
                    user_id,
                )
                if filepath and os.path.isfile(filepath):
                    paths_to_process.append(filepath)

            for existing in existing_records:
                rag.db.delete_kb_file(existing["id"])
        else:
            paths_to_process = [p for p in (filepaths or []) if p and os.path.isfile(p)]

        indexed_files = 0
        total_chunks = 0
        failed_files: List[str] = []

        for filepath in paths_to_process:
            filename = os.path.basename(filepath)
            try:
                file_size = os.path.getsize(filepath)
                file_type = "docx" if filename.lower().endswith(".docx") else "pdf"

                if mode == "incremental":
                    existing_records = [
                        row for row in rag.db.list_kb_files(user_id)
                        if row.get("filename") == filename
                    ]
                    for record in existing_records:
                        rag.db.delete_kb_file(record["id"])

                file_record = rag.db.create_kb_file(user_id, {
                    "filename": filename,
                    "file_size_bytes": file_size,
                    "file_type": file_type,
                    "storage_path": f"local/pdfs/{user_id}/{filename}",
                    "upload_status": "processing",
                })

                source, text = load_document(filepath)
                if not text or not text.strip():
                    rag.db.update_kb_file(file_record["id"], {
                        "upload_status": "failed",
                        "error_message": "No text could be extracted from document",
                    })
                    failed_files.append(filename)
                    continue

                chunks = chunk_text(text, chunk_size=KB_CHUNK_SIZE, overlap=KB_CHUNK_OVERLAP)
                if len(chunks) > KB_MAX_CHUNKS_PER_FILE:
                    chunks = chunks[:KB_MAX_CHUNKS_PER_FILE]

                docs_for_rag = [
                    (source, chunk, {"filename": filename, "chunk_number": idx + 1})
                    for idx, chunk in enumerate(chunks)
                ]

                if rag.build_from_documents(docs_for_rag, file_record["id"]):
                    indexed_files += 1
                    total_chunks += len(chunks)
                else:
                    failed_files.append(filename)
            except Exception:
                logger.exception("KB worker failed on file %s", filename)
                failed_files.append(filename)

        final_payload = {
            "in_progress": False,
            "status": "completed" if not failed_files else ("failed" if indexed_files == 0 else "completed"),
            "error": None if indexed_files > 0 or not failed_files else "All files failed during training",
            "job_id": job_id,
            "mode": mode,
            "indexed_files": indexed_files,
            "total_chunks": total_chunks,
            "failed_files": failed_files,
            "finished_at": int(time.time()),
        }
        _set_status(connection, user_id, final_payload)

        current_job_value = _decode_redis_value(connection.get(_current_key(user_id)))
        if current_job_value == job_id:
            connection.delete(_current_key(user_id))

        return final_payload
    except Exception as e:
        logger.exception("KB worker job crashed")
        _set_status(connection, user_id, {
            "in_progress": False,
            "status": "failed",
            "error": str(e),
            "job_id": job_id,
            "mode": mode,
            "finished_at": int(time.time()),
        })
        current_job_value = _decode_redis_value(connection.get(_current_key(user_id)))
        if current_job_value == job_id:
            connection.delete(_current_key(user_id))
        raise
