# Grafana Dashboard Backups

## 📊 Employee Work Analytics
- **File:** `employee-analytics-dashboard.json`
- **UID:** `employee-analytics`
- **URL:** http://192.168.0.2/grafana/d/employee-analytics
- **Version:** 43 (as of 2026-03-14)

### Panels
| ID | Title | Type |
|----|-------|------|
| 1 | 🕐 Last Work Hours | stat |
| 2 | ⬇️ Last Clock In | stat |
| 3 | ⬆️ Last Clock Out | stat |
| 4 | 📅 Last Record Date | stat |
| 5 | 👥 Total Employees | stat |
| 6 | 📋 Total Records | stat |
| 12 | 📈 Daily Work Hours | timeseries |
| 13 | 👥 Daily Employee Count | timeseries |
| 20 | 🔍 Recent Records | table |
| 21 | 📊 Hours by Employee | timeseries |

### Variables
- `$employee` - Employee selector (query variable, multi-select, includes "All")

### Data Source
- **Name:** AttendanceDB
- **Type:** PostgreSQL
- **UID:** cffwff9bf3z7kc
