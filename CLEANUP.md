# 🧹 SEO Analyzer - Cleanup Guide

## Overview

The SEO Analyzer deployment includes automated and manual cleanup procedures to keep your server disk free from old Docker images, builder cache, and backups.

## Automatic Cleanup

### During GitHub Actions Deployment

The GitHub Actions workflow automatically cleans up after each deployment:

1. **Keep last 5 backups** - Old backups are automatically removed
2. **Prune Docker builder cache** - Unused build layers
3. **Remove unused images** - Images older than 72 hours
4. **Remove dangling volumes** - Unused Docker volumes
5. **Final system cleanup** - System-wide Docker cleanup for items older than 7 days

### Weekly Cron Job

A scheduled weekly cleanup runs every **Sunday at 2:00 AM UTC**:

- Removes backups older than the last 5
- Cleans Docker builder cache (older than 30 days)
- Removes unused images (older than 7 days)
- Prunes dangling volumes
- Cleans Python `__pycache__` directories
- Cleans NPM cache

**Setup the cron job:**
```bash
./setup-cleanup-cron.sh
```

**View logs:**
```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 tail -f /var/log/seo-analyzer-cleanup.log
```

## Manual Cleanup

### One-time Full Cleanup

```bash
./cleanup-cache.sh
```

This will:
- Display disk usage before/after
- Clean all items above (backups, cache, images, volumes, etc.)
- Show detailed progress

### Disk Usage Check

```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "df -h / && echo '' && sudo du -sh /var/lib/docker"
```

## What Gets Cleaned

### Backups
- **Keep:** Last 5 deployments
- **Remove:** Older backups in `/opt/seo-analyzer/backups/`

### Docker Images
- **Keep:** Currently used images
- **Remove:** Unused images older than 7 days

### Docker Builder Cache
- **Keep:** Recent build layers
- **Remove:** Build cache older than 30 days

### Dangling Resources
- **Remove:** Unused volumes, networks, containers

### Application Cache
- **Remove:** Python `__pycache__` directories
- **Remove:** NPM cache (`.cache` folders)

## Disk Space Estimates

**Typical usage per deployment:**
- Docker images: 500MB - 2GB (depending on base images)
- Backups: 200MB - 500MB per backup
- Builder cache: 100MB - 500MB

**Example cleanup savings:**
- Removing 10 old backups: ~2-5GB
- Cleaning Docker cache: ~1-2GB
- Removing unused images: ~500MB - 1GB

## Removing the Cron Job

If you want to disable automatic cleanups:

```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 sudo crontab -e
```

Then delete the line containing `seo-analyzer-weekly-cleanup`.

## Troubleshooting

### Cron job not running

Check if the script is executable:
```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "ls -la /usr/local/bin/seo-analyzer-weekly-cleanup.sh"
```

Check cron logs (on Ubuntu):
```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "sudo tail -f /var/log/syslog | grep CRON"
```

### Disk still full

1. Check what's taking space: `sudo du -sh /var/lib/docker/*`
2. Check old images: `sudo docker image ls --format "table {{.Repository}} {{.Size}}"`
3. Manually remove specific images: `sudo docker image rm <IMAGE_ID>`

### Emergency cleanup

If disk is critically low:
```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "
  sudo docker system prune -af  # Removes ALL unused resources
  sudo docker volume prune -f
"
```

**⚠️ WARNING:** This removes all unused data, not just old items. Make sure no services need the data being removed.

## Integration with Deployment

The cleanup steps in the GitHub Actions workflow are:

1. **During deployment:** Clean old backups (steps 1-7)
2. **At end of deployment:** Final Docker cleanup

This ensures that each successful deployment cleans up the previous build artifacts.

## Performance Impact

- **Cleanup time:** 2-10 minutes depending on Docker storage
- **Disk freed:** 2-10GB per cleanup cycle
- **When to run:** After multiple deployments or when disk is >80% full

## Next Steps

1. **Setup automatic weekly cleanup:**
   ```bash
   ./setup-cleanup-cron.sh
   ```

2. **Monitor disk usage:**
   ```bash
   ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "watch -n 30 'df -h / && echo && sudo du -sh /var/lib/docker'"
   ```

3. **Manual cleanup when needed:**
   ```bash
   ./cleanup-cache.sh
   ```