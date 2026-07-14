"""Background continuous scanner using APScheduler."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from pokebargain.logging import get_logger
from pokebargain.pipeline.scan import ScanPipeline

log = get_logger(__name__)


class BackgroundScanner:
    def __init__(self, pipeline: ScanPipeline, interval_seconds: int) -> None:
        self._pipeline = pipeline
        self._interval = interval_seconds
        self._scheduler = BackgroundScheduler()

    def start(self) -> None:
        self._scheduler.add_job(
            self._safe_run,
            "interval",
            seconds=self._interval,
            id="ebay_scan",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.start()
        log.info("Background scanner started (every %ss)", self._interval)

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def _safe_run(self) -> None:
        try:
            counts = self._pipeline.run()
            log.info("Scan complete: %s", counts)
        except Exception:
            log.exception("Background scan failed")
