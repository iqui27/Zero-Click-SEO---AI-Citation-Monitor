# SEO Analyzer - Monitoring and Maintenance Guide

## Quick Reference

### Service Monitoring Commands

```bash
# Check service status
cd /opt/seo-analyzer
./scripts/monitor-services.sh status

# Follow all logs
./scripts/monitor-services.sh logs

# Follow specific service logs
./scripts/monitor-services.sh logs-backend
./scripts/monitor-services.sh logs-frontend
./scripts/monitor-services.sh logs-db

# Run health check
./scripts/monitor-services.sh health
```

### Basic Docker Compose Commands

```bash
cd /opt/seo-analyzer

# Check running services
docker compose -f docker-compose.prod.yml --env-file .env ps

# Follow logs
docker compose -f docker-compose.prod.yml --env-file .env logs -f

# Restart all services
docker compose -f docker-compose.prod.yml --env-file .env restart

# Restart specific service
docker compose -f docker-compose.prod.yml --env-file .env restart backend
```

## Maintenance Tasks

### 1. Application Updates

Use the automated update script:
```bash
cd /opt/seo-analyzer
./scripts/update-app.sh
```

Or manual process:
```bash
ssh root@198.211.98.85
cd /opt/seo-analyzer
git pull && npm --prefix frontend ci && npm --prefix frontend run build
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

### 2. Database Backups

#### Automated Daily Backups
Backups are scheduled daily at 2:30 AM via cron. To set up:
```bash
sudo cp /opt/seo-analyzer/scripts/seo-analyzer-cron /etc/cron.d/
sudo systemctl reload cron
```

#### Manual Backup
```bash
# Local backup (from Docker container)
./scripts/backup-database.sh local

# Remote backup (direct database connection)
./scripts/backup-database.sh remote
```

#### Backup Locations
- Local backups: `/opt/seo-analyzer/backups/`
- Retention: 30 days (configurable in backup script)
- Format: `seo_analyzer_backup_YYYYMMDD_HHMMSS.sql.gz`

### 3. DigitalOcean Droplet Snapshots

#### Manual Snapshot
```bash
# Using doctl CLI
doctl compute droplet-action snapshot 512874238 --snapshot-name "seo-analyzer-$(date +%Y%m%d)"

# Or via web interface at https://cloud.digitalocean.com/droplets
```

#### Automated Snapshots
Consider setting up automated snapshots in the DigitalOcean control panel:
1. Go to your droplet settings
2. Enable automated backups (weekly)
3. Or schedule snapshots via API/scripts

## Monitoring Setup

### 1. DigitalOcean Monitoring

#### CPU Usage Alert
- **Metric**: CPU Usage > 80%
- **Window**: 5 minutes
- **Action**: Email notification + investigate

#### Memory Usage Alert
- **Metric**: Memory Usage > 85%
- **Window**: 5 minutes
- **Action**: Email notification + check for memory leaks

#### Disk Usage Alert
- **Metric**: Disk Usage > 90%
- **Window**: 10 minutes
- **Action**: Email notification + cleanup old logs/backups

### 2. External Uptime Monitoring

Set up external monitoring services:

#### Option A: UptimeRobot (Free)
1. Sign up at https://uptimerobot.com
2. Add HTTP monitor for: `http://198.211.98.85/api/healthz`
3. Set check interval: 5 minutes
4. Configure email/SMS alerts

#### Option B: BetterStack (Recommended)
1. Sign up at https://betterstack.com
2. Add HTTP monitor for: `http://198.211.98.85/api/healthz`
3. Configure multiple check locations
4. Set up incident management

#### Option C: StatusCake
1. Sign up at https://statuscake.com
2. Add Uptime Test for: `http://198.211.98.85/api/healthz`
3. Configure alert contacts

### 3. Log Monitoring

Important log files to monitor:
```bash
# Application logs
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs frontend

# System logs
/var/log/seo-analyzer-backup.log
/var/log/seo-analyzer-health.log
/var/log/seo-analyzer-update.log

# Nginx/proxy logs (if using)
/var/log/nginx/access.log
/var/log/nginx/error.log
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check container logs
docker compose -f docker-compose.prod.yml logs backend

# Check disk space
df -h

# Check memory usage
free -h

# Restart services
docker compose -f docker-compose.prod.yml restart
```

#### High CPU/Memory Usage
```bash
# Check container resource usage
docker stats

# Check system processes
top
htop

# Check application-specific metrics
./scripts/monitor-services.sh health
```

#### Database Connection Issues
```bash
# Check PostgreSQL container
docker compose -f docker-compose.prod.yml logs postgres

# Connect to database directly
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d seo_analyzer

# Check database connections
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT * FROM pg_stat_activity;"
```

#### Disk Space Issues
```bash
# Check disk usage
df -h

# Find large files
find /opt/seo-analyzer -size +100M -ls

# Clean up old logs
find /opt/seo-analyzer -name "*.log" -mtime +7 -delete

# Clean up old backups
find /opt/seo-analyzer/backups -name "*.sql.gz" -mtime +30 -delete

# Clean up Docker
docker system prune -f
```

## Security Considerations

### Firewall Configuration
Your DigitalOcean firewall should already be configured to:
- Allow SSH (port 22) from your IP only
- Allow HTTP (port 80) from anywhere
- Allow HTTPS (port 443) from anywhere
- Block all other ports

### Regular Security Updates
```bash
# Update system packages
apt update && apt upgrade -y

# Update Docker images
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### SSL Certificate Renewal
If using Let's Encrypt:
```bash
# Check certificate expiry
certbot certificates

# Renew certificates
certbot renew --dry-run
certbot renew
```

## Performance Optimization

### Database Maintenance
```bash
# Analyze database statistics
docker compose exec postgres psql -U postgres -d seo_analyzer -c "ANALYZE;"

# Vacuum database
docker compose exec postgres psql -U postgres -d seo_analyzer -c "VACUUM;"

# Check database size
docker compose exec postgres psql -U postgres -d seo_analyzer -c "SELECT pg_size_pretty(pg_database_size('seo_analyzer'));"
```

### Log Rotation
Set up log rotation for application logs:
```bash
# Create logrotate config
sudo tee /etc/logrotate.d/seo-analyzer << EOF
/var/log/seo-analyzer-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
EOF
```

## Emergency Procedures

### Complete Service Failure
1. Check system resources: `df -h && free -h`
2. Check Docker daemon: `systemctl status docker`
3. Restart Docker if needed: `systemctl restart docker`
4. Restart application: `docker compose -f docker-compose.prod.yml up -d`
5. Check logs: `docker compose -f docker-compose.prod.yml logs`

### Database Recovery
1. Stop application: `docker compose -f docker-compose.prod.yml down`
2. Restore from backup:
   ```bash
   gunzip -c /opt/seo-analyzer/backups/latest_backup.sql.gz | \
   docker compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d seo_analyzer
   ```
3. Start application: `docker compose -f docker-compose.prod.yml up -d`

### Rollback Deployment
1. Check git commit history: `git log --oneline -10`
2. Rollback to previous commit: `git reset --hard HEAD~1`
3. Rebuild and restart: `./scripts/update-app.sh`

## Contact Information

- **System Admin**: [Your Name]
- **Emergency Contact**: [Your Phone/Email]
- **DigitalOcean Support**: https://cloud.digitalocean.com/support
- **Repository**: [Your Git Repository URL]

## Quick Commands Reference

```bash
# Service status
docker compose -f docker-compose.prod.yml ps

# Logs
docker compose -f docker-compose.prod.yml logs -f

# Update application
./scripts/update-app.sh

# Backup database
./scripts/backup-database.sh

# Health check
./scripts/monitor-services.sh health

# System resources
df -h && free -h && docker stats --no-stream
```
