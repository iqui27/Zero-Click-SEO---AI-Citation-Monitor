"""
Monitor Scheduler Service - Handles CRON-based automated monitoring execution
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from croniter import croniter
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import SessionLocal
from app.models.models import Monitor, MonitorTemplate, PromptTemplate, PromptVersion, Run
from app.services.tasks import enqueue_run
from app.services.engine_registry import ensure_engine

logger = logging.getLogger(__name__)

class MonitorScheduler:
    """
    Automated scheduler for monitors with CRON expressions
    """
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # Check every minute
        
    async def start(self):
        """Start the scheduler loop"""
        self.running = True
        logger.info("Monitor scheduler started")
        
        while self.running:
            try:
                await self._check_and_execute_monitors()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Monitor scheduler stopped")
    
    async def _check_and_execute_monitors(self):
        """Check all active monitors and execute those due for execution"""
        db = SessionLocal()
        try:
            # Get all active monitors with CRON schedules
            monitors = db.query(Monitor).filter(
                and_(
                    Monitor.active == True,
                    Monitor.schedule_cron.isnot(None),
                    Monitor.schedule_cron != ""
                )
            ).all()
            
            current_time = datetime.now(timezone.utc)
            
            for monitor in monitors:
                if self._should_execute_monitor(monitor, current_time, db):
                    # Catch-up: compute how many slots were missed since last run and execute up to a small backlog
                    try:
                        sched = (monitor.schedule_cron or "").strip()
                        cron_part = sched.split(";")[0].strip()
                        exprs = [e.strip() for e in cron_part.split("|") if e.strip()]
                        # Determine last time reference
                        last_run = (
                            db.query(Run)
                            .filter(Run.monitor_id == monitor.id)
                            .order_by(Run.started_at.desc())
                            .first()
                        )
                        ref = last_run.started_at if last_run and last_run.started_at else (current_time - timedelta(minutes=self.check_interval))
                        # Generate next occurrences from ref until now
                        due_slots: list[tuple[datetime, str, int, int]] = []  # (when, slotHHMM, indexToday, totalToday)
                        # Build today's times to compute index/total for each day
                        def _extract_times_from_cron(expr: str) -> list[str]:
                            times: list[str] = []
                            try:
                                fields = [f for f in expr.split() if f]
                                if len(fields) >= 2:
                                    mm = int(fields[0]); hh = int(fields[1])
                                    times.append(f"{hh:02d}:{mm:02d}")
                            except Exception:
                                return []
                            return times
                        # union of times across exprs for a given day will be re-evaluated per occurrence
                        for ex in exprs:
                            try:
                                it = croniter(ex, ref)
                                while True:
                                    nxt = it.get_next(datetime)
                                    if nxt.tzinfo is None:
                                        nxt = nxt.replace(tzinfo=timezone.utc)
                                    if nxt > current_time:
                                        break
                                    # derive slot and index for that day
                                    hh = f"{nxt.hour:02d}"; mm = f"{nxt.minute:02d}"
                                    slot = f"{hh}:{mm}"
                                    # compute total/index for the date of nxt
                                    day_times: list[str] = []
                                    for ex2 in exprs:
                                        try:
                                            # walk through ex2 within the same UTC day
                                            it2 = croniter(ex2, datetime(nxt.year, nxt.month, nxt.day, tzinfo=timezone.utc))
                                            t2 = it2.get_next(datetime)
                                            # advance until next day
                                            while t2.date() == nxt.date():
                                                day_times.append(f"{t2.hour:02d}:{t2.minute:02d}")
                                                t2 = it2.get_next(datetime)
                                        except Exception:
                                            continue
                                    # unique + sort
                                    day_times = sorted(sorted(set(day_times)))
                                    total_today = len(day_times) or None
                                    idx_today = (day_times.index(slot) + 1) if (slot in day_times) else None
                                    due_slots.append((nxt, slot, idx_today, total_today))
                            except Exception:
                                continue
                        # sort by time asc and cap backlog
                        due_slots.sort(key=lambda x: x[0])
                        max_backlog = 5
                        for when, slot, idx, tot in due_slots[-max_backlog:]:
                            await self._execute_monitor(monitor, db, schedule_slot=slot, idx_today=idx, total_today=tot, schedule_date=when.replace(hour=0, minute=0, second=0, microsecond=0))
                    except Exception:
                        # Fallback: at least execute once
                        await self._execute_monitor(monitor, db)
                    
        except Exception as e:
            logger.error(f"Error checking monitors: {e}")
        finally:
            db.close()
    
    def _should_execute_monitor(self, monitor: Monitor, current_time: datetime, db: Session) -> bool:
        """Check if a monitor should be executed based on its schedule.

        Supports:
        - Single CRON expression (legacy)
        - Multiple CRON expressions separated by '|' (e.g., "0 8 * * * | 0 12 * * *")
        - Optional expiry using suffix "; until=YYYY-MM-DD" (UTC date end-of-day)
        """
        try:
            sched = (monitor.schedule_cron or "").strip()
            if not sched:
                return False

            # Parse optional options after ';'
            cron_part = sched
            until_dt: Optional[datetime] = None
            if ";" in sched:
                parts = [p.strip() for p in sched.split(";")]
                cron_part = parts[0].strip()
                # parse key=value options
                for opt in parts[1:]:
                    if not opt:
                        continue
                    kv = [x.strip() for x in opt.split("=", 1)]
                    if len(kv) == 2 and kv[0].lower() == "until":
                        try:
                            # Interpret as UTC date end-of-day
                            y, m, d = [int(x) for x in kv[1].split("-")]
                            until_dt = datetime(y, m, d, 23, 59, 59, tzinfo=timezone.utc)
                        except Exception:
                            until_dt = None

            # If expired, do not execute
            if until_dt is not None and current_time > until_dt:
                return False

            # Split possible multiple CRON expressions by '|'
            cron_exprs = [c.strip() for c in cron_part.split("|") if c.strip()]
            if not cron_exprs:
                return False

            # Get the last execution time for this monitor
            last_run = (
                db.query(Run)
                .filter(Run.monitor_id == monitor.id)
                .order_by(Run.started_at.desc())
                .first()
            )

            # If no previous runs: check if any cron would have triggered within the last interval
            if not last_run:
                for expr in cron_exprs:
                    try:
                        cron = croniter(expr, current_time)
                        prev_time = cron.get_prev(datetime)
                        time_diff = (current_time - prev_time).total_seconds()
                        if 0 <= time_diff <= self.check_interval:
                            return True
                    except Exception:
                        # ignore bad expressions, continue
                        continue
                return False

            # With a previous run: compute the earliest next schedule across all expressions
            next_times: List[datetime] = []
            for expr in cron_exprs:
                try:
                    cron = croniter(expr, last_run.started_at)
                    nxt = cron.get_next(datetime)
                    # Normalize naive datetimes to UTC if needed
                    if nxt.tzinfo is None:
                        nxt = nxt.replace(tzinfo=timezone.utc)
                    next_times.append(nxt)
                except Exception:
                    continue

            if not next_times:
                return False

            next_scheduled = min(next_times)
            return current_time >= next_scheduled

        except Exception as e:
            logger.error(f"Error checking monitor schedule for {monitor.id}: {e}")
            return False
    
    async def _execute_monitor(self, monitor: Monitor, db: Session, *, schedule_slot: str | None = None, idx_today: int | None = None, total_today: int | None = None, schedule_date: datetime | None = None):
        """Execute a monitor by running all its associated templates with all engines"""
        try:
            logger.info(f"Executing monitor {monitor.id} ({monitor.name})")
            
            # Get all templates associated with this monitor
            monitor_templates = db.query(MonitorTemplate).filter(
                MonitorTemplate.monitor_id == monitor.id
            ).all()
            
            if not monitor_templates:
                logger.warning(f"Monitor {monitor.id} has no templates attached")
                return
            
            # Parse engines configuration
            engines_config = monitor.engines_json.get('engines', []) if monitor.engines_json else []
            if not engines_config:
                logger.warning(f"Monitor {monitor.id} has no engines configured")
                return
            
            # Derive schedule metadata for today from schedule_cron
            def _extract_times_from_cron(expr: str) -> list[str]:
                times: list[str] = []
                try:
                    cron_part = expr.split(';')[0].strip()
                    parts = [p.strip() for p in cron_part.split('|') if p.strip()]
                    for p in parts:
                        fields = [f for f in p.split() if f]
                        if len(fields) >= 2:
                            try:
                                mm = int(fields[0])
                                hh = int(fields[1])
                                times.append(f"{hh:02d}:{mm:02d}")
                            except Exception:
                                continue
                except Exception:
                    return []
                # sort by day time ascending
                try:
                    times.sort(key=lambda t: int(t.split(':')[0])*60 + int(t.split(':')[1]))
                except Exception:
                    pass
                return times

            now_utc = datetime.now(timezone.utc)
            if schedule_slot is None or idx_today is None or total_today is None:
                times_today = _extract_times_from_cron(monitor.schedule_cron or "")
                total_today = len(times_today) if times_today else None
                idx_today = None
                slot = None
                if times_today:
                    cur_min = now_utc.hour * 60 + now_utc.minute
                    diffs = []
                    for i, t in enumerate(times_today):
                        try:
                            hh, mm = [int(x) for x in t.split(':')]
                            m = hh*60 + mm
                            diffs.append((abs(cur_min - m), i))
                        except Exception:
                            continue
                    if diffs:
                        diffs.sort(key=lambda x: x[0])
                        idx_today = diffs[0][1] + 1
                        slot = times_today[diffs[0][1]]
            else:
                slot = schedule_slot

            created_runs = []
            
            # Execute each template with each engine
            for mt in monitor_templates:
                template = db.get(PromptTemplate, mt.template_id)
                if not template:
                    continue

                # Create a Prompt and a first PromptVersion from this template (same path as manual run)
                prompt = None
                try:
                    from app.models.models import Prompt  # local import to avoid cycles
                    prompt = Prompt(
                        project_id=monitor.project_id,
                        name=f"Run: {template.name}",
                        text=template.text,
                        intent=template.intent,
                        persona=template.persona,
                    )
                    db.add(prompt)
                    db.commit()
                    db.refresh(prompt)
                except Exception as e:
                    logger.error(f"Failed to create Prompt for template {template.id}: {e}")
                    continue

                pv = None
                try:
                    pv = PromptVersion(prompt_id=prompt.id, version=1, text=template.text)
                    db.add(pv)
                    db.commit()
                    db.refresh(pv)
                except Exception as e:
                    logger.error(f"Failed to create PromptVersion for template {template.id}: {e}")
                    continue

                # Create runs for each engine
                for engine_config in engines_config:
                    try:
                        canonical_engine, override = ensure_engine(
                            db=db,
                            project_id=monitor.project_id,
                            name=engine_config.get('name'),
                            region=engine_config.get('region'),
                            device=engine_config.get('device'),
                            requested_config=engine_config.get('config_json') or {},
                        )

                        # Create run
                        run = Run(
                            project_id=monitor.project_id,
                            prompt_version_id=pv.id,
                            engine_id=canonical_engine.id,
                            subproject_id=(template.subproject_id or monitor.subproject_id),
                            monitor_id=monitor.id,
                            status="queued",
                            cycles_total=1,
                            schedule_source="monitor",
                            schedule_date=(schedule_date or now_utc.replace(hour=0, minute=0, second=0, microsecond=0)),
                            schedule_slot=slot,
                            schedule_index_today=idx_today,
                            schedule_total_today=total_today,
                            engine_override_json=override,
                        )
                        db.add(run)
                        db.commit()
                        db.refresh(run)

                        # Enqueue the run for execution
                        enqueue_run(run.id, cycles=1)
                        created_runs.append(run.id)

                        logger.info(
                            f"Created run {run.id} for monitor {monitor.id}, template {template.name}, engine {canonical_engine.name}"
                        )

                    except Exception as e:
                        logger.error(
                            f"Error creating run for monitor {monitor.id}, template {template.id}, engine {engine_config}: {e}"
                        )
                        continue
            
            logger.info(f"Monitor {monitor.id} executed successfully. Created {len(created_runs)} runs: {created_runs}")
            
        except Exception as e:
            logger.error(f"Error executing monitor {monitor.id}: {e}")

# Global scheduler instance
_scheduler_instance: Optional[MonitorScheduler] = None

def get_scheduler() -> MonitorScheduler:
    """Get the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = MonitorScheduler()
    return _scheduler_instance

async def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    await scheduler.start()

def stop_scheduler():
    """Stop the global scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
