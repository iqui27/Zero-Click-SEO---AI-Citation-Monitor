# SEO Analyzer - Monitoring & Maintenance Scripts

This directory contains scripts and configurations for monitoring and maintaining your SEO Analyzer application.

## 📋 Files Overview

### Scripts
- **`monitor-services.sh`** - Monitor Docker services, view logs, and run health checks
- **`update-app.sh`** - Automated application update with backup and rollback
- **`backup-database.sh`** - Create and manage database backups
- **`setup-monitoring.sh`** - Initial setup script for server-side monitoring

### Configuration
- **`seo-analyzer-cron`** - Cron job configuration for automated tasks

## 🚀 Quick Setup

### 1. Upload Scripts to Server
```bash
# Copy scripts to your server
scp -r scripts/ root@198.211.98.85:/opt/seo-analyzer/

# SSH to server and run setup
ssh root@198.211.98.85
cd /opt/seo-analyzer
./scripts/setup-monitoring.sh
```

### 2. Verify Installation
```bash
# Check if cron jobs are active
crontab -l
cat /etc/cron.d/seo-analyzer-cron

# Test monitoring script
./scripts/monitor-services.sh health

# Test backup script
./scripts/backup-database.sh local
```

## 🔧 Usage

### Service Monitoring
```bash
# Check all services status
./scripts/monitor-services.sh status

# Follow all logs in real-time
./scripts/monitor-services.sh logs

# Follow specific service logs
./scripts/monitor-services.sh logs-backend
./scripts/monitor-services.sh logs-frontend
./scripts/monitor-services.sh logs-db

# Run health check
./scripts/monitor-services.sh health
```

### Application Updates
```bash
# Automated update with backup and health checks
./scripts/update-app.sh

# This will:
# 1. Create database backup
# 2. Pull latest code
# 3. Build frontend
# 4. Restart containers
# 5. Verify health
# 6. Rollback if issues occur
```

### Database Backups
```bash
# Local backup (from Docker container)
./scripts/backup-database.sh local

# Remote backup (direct connection)
./scripts/backup-database.sh remote

# Backups are stored in: /opt/seo-analyzer/backups/
# Format: seo_analyzer_backup_YYYYMMDD_HHMMSS.sql.gz
# Retention: 30 days (configurable)
```

## ⏰ Automated Tasks

The following tasks are automated via cron:

### Daily Database Backup
- **Time**: 2:30 AM daily
- **Command**: `backup-database.sh local`
- **Log**: `/var/log/seo-analyzer-backup.log`

### Weekly Health Check
- **Time**: 3:00 AM every Sunday
- **Command**: `monitor-services.sh health`
- **Log**: `/var/log/seo-analyzer-health.log`

### Monthly Log Cleanup
- **Time**: 4:00 AM on the 1st of each month
- **Action**: Remove logs older than 30 days

## 📊 External Monitoring Setup

Set up external uptime monitoring for `/api/healthz`:

### UptimeRobot (Free Option)
1. Sign up at https://uptimerobot.com
2. Create HTTP monitor for: `http://198.211.98.85/api/healthz`
3. Set interval: 5 minutes
4. Configure email alerts

### BetterStack (Recommended)
1. Sign up at https://betterstack.com
2. Create uptime check for: `http://198.211.98.85/api/healthz`
3. Configure multiple locations
4. Set up incident management

### StatusCake
1. Sign up at https://statuscake.com
2. Add uptime test for: `http://198.211.98.85/api/healthz`
3. Configure alert contacts

## 🚨 DigitalOcean Monitoring

### Set Up Alerts
1. Go to https://cloud.digitalocean.com/monitoring
2. Click "Create Alert"
3. Configure the following alerts:

#### CPU Usage Alert
- **Resource**: Your droplet (zero-click - 512874238)
- **Metric**: CPU Percentage
- **Threshold**: Greater than 80%
- **Duration**: 5 minutes
- **Notifications**: Email

#### Memory Usage Alert
- **Resource**: Your droplet (zero-click - 512874238)
- **Metric**: Memory Percentage
- **Threshold**: Greater than 85%
- **Duration**: 5 minutes
- **Notifications**: Email

#### Disk Usage Alert
- **Resource**: Your droplet (zero-click - 512874238)
- **Metric**: Disk Percentage
- **Threshold**: Greater than 90%
- **Duration**: 10 minutes
- **Notifications**: Email

### Enable Droplet Monitoring
If not already enabled:
1. Go to your droplet settings
2. Click "Enable Monitoring"
3. Metrics will be available in 5-10 minutes

## 🔄 Backup Strategy

### Automated Backups
- **Daily**: Database backup at 2:30 AM
- **Weekly**: Consider enabling DigitalOcean snapshots
- **Monthly**: Full system backup (manual)

### Backup Locations
1. **Local**: `/opt/seo-analyzer/backups/` (30-day retention)
2. **DigitalOcean Snapshots**: Droplet-level backups
3. **Optional**: Off-site backup to AWS S3, Google Cloud, etc.

### Recovery Testing
- Test database recovery monthly
- Verify backup integrity
- Document recovery procedures

## 🛠️ Troubleshooting

### Services Not Responding
```bash
# Check Docker status
systemctl status docker

# Check container logs
docker compose -f docker-compose.prod.yml logs

# Restart services
docker compose -f docker-compose.prod.yml restart

# Full rebuild if needed
./scripts/update-app.sh
```

### High Resource Usage
```bash
# Check system resources
df -h && free -h

# Check container resource usage
docker stats

# Check application metrics
./scripts/monitor-services.sh health
```

### Backup Issues
```bash
# Check backup logs
tail -f /var/log/seo-analyzer-backup.log

# Check disk space
df -h

# Manual backup test
./scripts/backup-database.sh local
```

## 📝 Log Files

Important log files to monitor:
- `/var/log/seo-analyzer-backup.log` - Backup operations
- `/var/log/seo-analyzer-health.log` - Health check results
- `/var/log/seo-analyzer-update.log` - Update operations
- Docker logs: `docker compose logs`

## 🔐 Security Notes

- Scripts run with appropriate permissions
- Database backups are compressed and include timestamps
- Cron jobs run as root but can be modified for lower privileges
- Consider encrypting backups for sensitive data
- Regularly update system packages and Docker images

## 📞 Support

For issues:
1. Check logs first: `tail -f /var/log/seo-analyzer-*.log`
2. Run health check: `./scripts/monitor-services.sh health`
3. Check system resources: `df -h && free -h`
4. Contact system administrator or check MAINTENANCE.md

## 🔄 Azure SQL Data Migration

Use the migration helper to copy data between two Azure SQL (SQL Server) databases using the project's SQLAlchemy models. This preserves IDs and respects foreign keys.

### 1) Prepare connection URLs
- Always URL-encode special characters in passwords (e.g., `@` -> `%40`, `!` -> `%21`).
- Format:

```bash
mssql+pyodbc://USERNAME:PASSWORD@HOST:1433/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
```

- Example TARGET (provided by infra):

```bash
mssql+pyodbc://usrMonumenta:Monu%402025%21@db-aigeo.database.windows.net:1433/db-ai-geo-hml?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
```

- SOURCE should be your current production Azure SQL URL.
  Replace with your real values and encode the password if needed.

### 2) Run the migration locally (recommended)

```bash
# From the repo root
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt

export SOURCE_DATABASE_URL="mssql+pyodbc://<user>:<pass_enc>@<old-host>:1433/<old-db>?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
export TARGET_DATABASE_URL="mssql+pyodbc://usrMonumenta:Monu%402025%21@db-aigeo.database.windows.net:1433/db-ai-geo-hml?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"

python scripts/migrate_azure_sql.py
```

The script will:
- Create the target schema if missing (`Base.metadata.create_all`).
- Copy tables in FK-safe order, skipping rows that already exist by primary key.
- Handle `monitor_templates` specially (identity PK) to avoid conflicts.

### 3) Point the app to the new database

Update your `.env` used by Docker Compose with:

```env
DATABASE_URL=mssql+pyodbc://usrMonumenta:Monu%402025%21@db-aigeo.database.windows.net:1433/db-ai-geo-hml?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
```

Then restart services:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Notes
- Ensure outbound traffic to port 1433 is allowed from your server.
- Avoid committing `.env` or secrets to version control. Rotate old credentials if they were exposed.
- If you previously relied on `extra_hosts` for DNS, update it to the new DB host if necessary.

---

**Last Updated**: $(date)
**Server**: 198.211.98.85 (zero-click droplet)
**Application**: SEO Analyzer
**Environment**: Production
