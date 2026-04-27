# MongoDB Settings — local-llm-server

## Local Development (docker-compose.yml)

| Setting | Value |
|---------|-------|
| Connection String | `mongodb://mongo:27017` |
| Container | `mongo:7` |
| Container Name | `llm-server-mongo` |
| Host Port | `27017` |
| Volume | `mongo_data` mounted at `/data/db` |
| Database Name | `llm_wiki_dashboard` (set in render.yaml / proxy env) |

### Services that connect to local MongoDB:
- **proxy** (`MONGO_URL=mongodb://mongo:27017`)
- **dashboard-backend** (`MONGO_URL=mongodb://mongo:27017`)

---

## Render Deployment (render.yaml)

| Setting | Value / Status |
|---------|----------------|
| Connection String | `MONGO_URL` — **must be set manually in Render dashboard** |
| Database Name | `llm_wiki_dashboard` |
| Sync Type | `sync: false` (not auto-synced; set via Render dashboard) |

> **Action required:** Create a free M0 cluster at https://cloud.mongodb.com and paste the connection URI into the Render dashboard as `MONGO_URL`.

---

## MongoDB Environment Variables Summary

```bash
# Local
MONGO_URL=mongodb://mongo:27017
DB_NAME=llm_wiki_dashboard

# Render (set in dashboard)
MONGO_URL=<your-atlas-connection-string>
DB_NAME=llm_wiki_dashboard
```

