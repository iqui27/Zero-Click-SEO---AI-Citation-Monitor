#!/usr/bin/env python3
"""
Script to manually trigger semantic insights processing for a run.
This will recalculate GEO metrics.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.tasks import process_semantic_insights

# Run ID from the test
RUN_ID = "run_8052f107"

print(f"=" * 80)
print(f"Triggering semantic insights processing for run: {RUN_ID}")
print(f"=" * 80)

try:
    # Enqueue the task
    result = process_semantic_insights.delay(RUN_ID)
    print(f"\n✓ Task enqueued successfully!")
    print(f"  Task ID: {result.id}")
    print(f"  Run ID: {RUN_ID}")
    print(f"\nMonitor worker logs with:")
    print(f"  docker compose logs -f worker | grep -E '(GEO|geo_metrics|{RUN_ID})'")
    print("=" * 80)

except Exception as e:
    print(f"\n✗ Failed to enqueue task")
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
