from __future__ import annotations

import time


class RedisJobQueue:
    def __init__(self, redis_url: str, queue_name: str = "ai-cut:jobs"):
        import redis

        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.queue_name = queue_name

    def enqueue(self, task_id: str) -> None:
        self._redis.rpush(self.queue_name, task_id)

    def dequeue(self, timeout_seconds: int = 5) -> str | None:
        item = self._redis.blpop(self.queue_name, timeout=timeout_seconds)
        if not item:
            return None
        _, task_id = item
        return task_id


class TaskWorker:
    def __init__(self, service, job_queue=None, poll_interval_seconds: int = 2):
        self.service = service
        self.job_queue = job_queue
        self.poll_interval_seconds = poll_interval_seconds

    def run_once(self) -> int:
        task_ids = self.service.list_pending_task_ids(limit=10)
        for task_id in task_ids:
            self.service.process_task(task_id)
        return len(task_ids)

    def run_forever(self) -> None:
        if self.job_queue is not None:
            self._run_queue_loop()
            return
        self._run_poll_loop()

    def _run_queue_loop(self) -> None:
        while True:
            task_id = self.job_queue.dequeue(timeout_seconds=self.poll_interval_seconds)
            if task_id:
                self.service.process_task(task_id)

    def _run_poll_loop(self) -> None:
        while True:
            count = self.run_once()
            if count == 0:
                time.sleep(self.poll_interval_seconds)
