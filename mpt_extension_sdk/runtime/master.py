import logging
import os
import signal
import threading
import time
from pathlib import Path

from watchfiles import watch
from watchfiles.filters import PythonFilter
from watchfiles.run import start_process

from mpt_extension_sdk.runtime.workers import start_event_consumer, start_gunicorn

logger = logging.getLogger(__name__)


HANDLED_SIGNALS = (signal.SIGINT, signal.SIGTERM)
PROCESS_CHECK_INTERVAL_SECS = int(os.environ.get("PROCESS_CHECK_INTERVAL_SECS", "5"))


def _display_path(path):  # pragma: no cover
    try:
        return f'"{path.relative_to(Path.cwd())}"'
    except ValueError:
        return f'"{path}"'


class Master:
    """Master process for managing worker processes."""
    def __init__(self, options, settings):
        self.workers = {}
        self.options = options
        self.settings = settings
        self.stop_event = threading.Event()
        self.monitor_event = threading.Event()
        self.watch_filter = PythonFilter(ignore_paths=None)
        self.watcher = watch(
            Path.cwd(),
            watch_filter=self.watch_filter,
            stop_event=self.stop_event,
            yield_on_timeout=True,
        )
        self.monitor_thread = None
        self.setup_signals_handler()

        match self.options["component"]:
            case "all":
                self.proc_targets = {
                    "event-consumer": start_event_consumer,
                    "gunicorn": start_gunicorn,
                }
            case "api":
                self.proc_targets = {
                    "gunicorn": start_gunicorn,
                }
            case "consumer":
                self.proc_targets = {"event-consumer": start_event_consumer}
            case _:
                self.proc_targets = {
                    "event-consumer": start_event_consumer,
                    "gunicorn": start_gunicorn,
                }

    def setup_signals_handler(self):
        """Setup signal handlers for termination signals."""
        for sig in HANDLED_SIGNALS:
            signal.signal(sig, self.handle_signal)

    def handle_signal(self, *args, **kwargs):
        """Handle termination signals."""
        self.stop_event.set()

    def start(self):
        """Start all worker processes."""
        for worker_type, target in self.proc_targets.items():
            self.start_worker_process(worker_type, target)
        self.monitor_thread = threading.Thread(target=self.monitor_processes)
        self.monitor_event.set()
        self.monitor_thread.start()

    def start_worker_process(self, worker_type, target):
        """Start a worker process."""
        worker_proc = start_process(target, "function", (self.options,), {})
        self.workers[worker_type] = worker_proc
        logger.info("%s worker pid: %s", worker_type.capitalize(), worker_proc.pid)

    def monitor_processes(self):  # pragma: no cover
        """Monitor the status of worker processes."""
        while self.monitor_event.is_set():
            exited_workers = []
            for worker_type, worker_proc in self.workers.items():
                if not worker_proc.is_alive():
                    if worker_proc.exitcode == 0:
                        exited_workers.append(worker_type)
                        logger.info("%s worker exited", worker_type.capitalize())
                    else:
                        logger.info(
                            "Process of type %s is dead, restart it", worker_type
                        )
                        self.start_worker_process(
                            worker_type, self.proc_targets[worker_type]
                        )
            if exited_workers == list(self.workers.keys()):
                self.stop_event.set()

            time.sleep(PROCESS_CHECK_INTERVAL_SECS)

    def stop(self):
        """Stop all worker processes."""
        self.monitor_event.clear()
        self.monitor_thread.join()
        for worker_type, process in self.workers.items():
            process.stop(sigint_timeout=5, sigkill_timeout=1)
            logger.info(
                "%s process with pid %s stopped.",
                worker_type.capitalize(),
                process.pid,
            )

    def restart(self):
        """Restart the master process."""
        self.stop()
        self.start()

    def __iter__(self):  # pragma: no cover
        return self

    def __next__(self):  # pragma: no cover
        changes = next(self.watcher)
        if changes:
            return list({Path(change[1]) for change in changes})
        return None

    def run(self):  # pragma: no cover
        """Run the master process."""
        self.start()
        if self.options.get("reload"):
            for files_changed in self:
                if files_changed:
                    logger.warning(
                        "Detected changes in %s. Reloading...",
                        ", ".join(map(_display_path, files_changed)),
                    )
                    self.restart()
        else:
            self.stop_event.wait()
        self.stop()
