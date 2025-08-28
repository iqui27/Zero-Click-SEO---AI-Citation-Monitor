"""
Monitor Scheduler Service - Handles CRON-based automated monitoring execution
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from croniter import croniter
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import SessionLocal
from app.models.models import Monitor, MonitorTemplate, PromptTemplate, PromptVersion, Engine, Run
from app.services.tasks import enqueue_run

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
                    await self._execute_monitor(monitor, db)
                    
        except Exception as e:
            logger.error(f"Error checking monitors: {e}")
        finally:
            db.close()
    
    def _should_execute_monitor(self, monitor: Monitor, current_time: datetime, db: Session) -> bool:
        """Check if a monitor should be executed based on its CRON schedule"""
        try:
            if not monitor.schedule_cron:
                return False
            
            # Get the last execution time for this monitor
            last_run = db.query(Run).filter(
                Run.monitor_id == monitor.id
            ).order_by(Run.started_at.desc()).first()
            
            # If no previous runs, check if it's time to run
            if not last_run:
                cron = croniter(monitor.schedule_cron, current_time)
                next_run = cron.get_prev(datetime)
                # If the previous scheduled time was within the last check interval, execute
                time_diff = (current_time - next_run).total_seconds()
                return 0 <= time_diff <= self.check_interval
            
            # Check if enough time has passed since last run based on CRON schedule
            cron = croniter(monitor.schedule_cron, last_run.started_at)
            next_scheduled = cron.get_next(datetime)
            
            return current_time >= next_scheduled
            
        except Exception as e:
            logger.error(f"Error checking monitor schedule for {monitor.id}: {e}")
            return False
    
    async def _execute_monitor(self, monitor: Monitor, db: Session):
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
            
            created_runs = []
            
            # Execute each template with each engine
            for mt in monitor_templates:
                template = db.get(PromptTemplate, mt.template_id)
                if not template:
                    continue
                
                # Get the latest prompt version for this template
                prompt_version = db.query(PromptVersion).join(
                    PromptTemplate, PromptTemplate.prompt_id == PromptVersion.prompt_id
                ).filter(
                    PromptTemplate.id == template.id
                ).order_by(PromptVersion.version.desc()).first()
                
                if not prompt_version:
                    logger.warning(f"No prompt version found for template {template.id}")
                    continue
                
                # Create runs for each engine
                for engine_config in engines_config:
                    try:
                        # Find or create engine
                        engine = db.query(Engine).filter(
                            and_(
                                Engine.project_id == monitor.project_id,
                                Engine.name == engine_config.get('name'),
                                Engine.region == engine_config.get('region'),
                                Engine.device == engine_config.get('device')
                            )
                        ).first()
                        
                        if not engine:
                            engine = Engine(
                                project_id=monitor.project_id,
                                name=engine_config.get('name'),
                                region=engine_config.get('region'),
                                device=engine_config.get('device'),
                                config_json=engine_config.get('config_json', {})
                            )
                            db.add(engine)
                            db.commit()
                            db.refresh(engine)
                        
                        # Create run
                        run = Run(
                            project_id=monitor.project_id,
                            prompt_version_id=prompt_version.id,
                            engine_id=engine.id,
                            subproject_id=monitor.subproject_id,
                            monitor_id=monitor.id,
                            status="queued",
                            cycles_total=1
                        )
                        db.add(run)
                        db.commit()
                        db.refresh(run)
                        
                        # Enqueue the run for execution
                        enqueue_run(run.id, cycles=1)
                        created_runs.append(run.id)
                        
                        logger.info(f"Created run {run.id} for monitor {monitor.id}, template {template.name}, engine {engine.name}")
                        
                    except Exception as e:
                        logger.error(f"Error creating run for monitor {monitor.id}, template {template.id}, engine {engine_config}: {e}")
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
