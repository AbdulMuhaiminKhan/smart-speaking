"""Start an RQ worker for the analysis queue: `python -m app.worker.run`."""

import logging
import sys

from rq import SimpleWorker, Worker

from app.services.queue import QUEUE_NAME, get_redis


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # macOS does not allow fork() after some system libraries load, so run jobs
    # in-process there. On Linux (Docker) each job gets a fresh forked process.
    worker_cls = SimpleWorker if sys.platform == "darwin" else Worker
    worker_cls([QUEUE_NAME], connection=get_redis()).work(with_scheduler=False)


if __name__ == "__main__":
    main()
