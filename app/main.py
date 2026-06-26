import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.routes import router
from observability.middleware import TraceMiddleware
from services.rate_limiter import limiter


def _run_migrations():
    """
    Idempotent migrations: extensions, schema additions, indexes, CDC triggers,
    and autonomous-agent tables. Safe to run on every startup.
    """
    try:
        from sqlalchemy import text
        from core.db import SessionLocal
        with SessionLocal() as db:
            # ── Extensions ────────────────────────────────────────────────────
            db.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
            db.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))

            # ── Schema additions ──────────────────────────────────────────────
            db.execute(text(
                'ALTER TABLE issues ADD COLUMN IF NOT EXISTS embedding vector(1536)'
            ))

            # ── Performance indexes ───────────────────────────────────────────
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS issues_customer_id_idx ON issues (customer_id)'
            ))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS issues_status_lower_idx ON issues ((LOWER(status)))'
            ))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS customers_account_owner_idx ON customers (account_owner)'
            ))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS customers_health_idx ON customers (health_status)'
            ))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS next_actions_issue_id_idx ON next_actions (issue_id)'
            ))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS customers_name_trgm_idx '
                'ON customers USING gin (LOWER(name) gin_trgm_ops)'
            ))

            # ── Query cache (two-layer: Redis exact + pgvector semantic) ────────
            db.execute(text('''
                CREATE TABLE IF NOT EXISTS query_cache (
                  id               SERIAL PRIMARY KEY,
                  query_hash       VARCHAR(64) UNIQUE,
                  query_text       TEXT,
                  query_embedding  vector(1536),
                  cache_scope      VARCHAR(255),
                  answer_text      TEXT,
                  plan_summary     TEXT,
                  hit_count        INT DEFAULT 0,
                  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_hit_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS query_cache_embedding_idx '
                'ON query_cache USING hnsw (query_embedding vector_cosine_ops) '
                'WITH (m = 16, ef_construction = 64)'
            ))

            # ── Cross-session persistent memory ──────────────────────────────
            db.execute(text('''
                CREATE TABLE IF NOT EXISTS persistent_memory (
                  id         SERIAL PRIMARY KEY,
                  scope      VARCHAR(255) NOT NULL,
                  key        VARCHAR(255) NOT NULL,
                  value      TEXT NOT NULL,
                  source     VARCHAR(50)  DEFAULT 'auto_extracted',
                  confidence FLOAT        DEFAULT 0.8,
                  expires_at TIMESTAMP,
                  created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE (scope, key)
                )
            '''))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS persistent_memory_scope_idx '
                'ON persistent_memory (scope, expires_at)'
            ))

            # ── Autonomous agent tables ───────────────────────────────────────
            db.execute(text('''
                CREATE TABLE IF NOT EXISTS briefings (
                  id               SERIAL PRIMARY KEY,
                  customer_name    VARCHAR(255) NOT NULL,
                  account_owner    VARCHAR(255),
                  health_status    VARCHAR(50),
                  open_issues      INT DEFAULT 0,
                  risk_level       VARCHAR(50),
                  risk_summary     TEXT,
                  recommended_action TEXT,
                  urgency          VARCHAR(50),
                  source           VARCHAR(50),
                  trigger_issue_id INT,
                  acknowledged     BOOLEAN DEFAULT FALSE,
                  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS briefings_owner_unacked_idx '
                'ON briefings (account_owner, acknowledged, created_at DESC)'
            ))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS briefings_unacked_idx '
                'ON briefings (acknowledged, created_at DESC)'
            ))
            db.execute(text('''
                CREATE TABLE IF NOT EXISTS health_snapshots (
                  customer_name VARCHAR(255) PRIMARY KEY,
                  health_status VARCHAR(50) NOT NULL,
                  captured_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # ── Durable write audit log ───────────────────────────────────────
            # Redis holds a 24h trace; this table provides permanent audit compliance.
            # Queried via GET /audit (admin only) for SOC2 / compliance review.
            db.execute(text('''
                CREATE TABLE IF NOT EXISTS write_audit (
                  id        SERIAL PRIMARY KEY,
                  trace_id  VARCHAR(64),
                  tool      VARCHAR(100),
                  label     VARCHAR(100),
                  username  VARCHAR(255),
                  roles     VARCHAR(255),
                  args      TEXT,
                  ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.execute(text(
                'CREATE INDEX IF NOT EXISTS write_audit_user_ts_idx '
                'ON write_audit (username, ts DESC)'
            ))

            # ── CDC triggers — real-time NOTIFY on issue changes ──────────────
            db.execute(text('''
                CREATE OR REPLACE FUNCTION notify_issue_change() RETURNS trigger AS $$
                BEGIN
                  PERFORM pg_notify(
                    'issue_updated',
                    json_build_object('id', NEW.id, 'op', TG_OP)::text
                  );
                  RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            '''))
            db.execute(text('DROP TRIGGER IF EXISTS issue_cdc ON issues'))
            db.execute(text('''
                CREATE TRIGGER issue_cdc
                  AFTER INSERT OR UPDATE ON issues
                  FOR EACH ROW EXECUTE FUNCTION notify_issue_change()
            '''))

            db.execute(text('''
                CREATE OR REPLACE FUNCTION notify_issue_note_added() RETURNS trigger AS $$
                BEGIN
                  PERFORM pg_notify(
                    'issue_note_added',
                    json_build_object('issue_id', NEW.issue_id, 'id', NEW.id)::text
                  );
                  RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            '''))
            db.execute(text('DROP TRIGGER IF EXISTS issue_note_cdc ON issue_updates'))
            db.execute(text('''
                CREATE TRIGGER issue_note_cdc
                  AFTER INSERT ON issue_updates
                  FOR EACH ROW EXECUTE FUNCTION notify_issue_note_added()
            '''))

            db.commit()
    except Exception as e:
        from observability.logging_utils import log_event
        log_event('migration_error', {'error': str(e)[:200]})  # Non-fatal — app degrades gracefully


def _run_hnsw_index():
    """Build HNSW index once embeddings exist (requires at least one non-NULL row)."""
    try:
        from sqlalchemy import text
        from core.db import SessionLocal
        with SessionLocal() as db:
            count = db.execute(
                text('SELECT COUNT(*) FROM issues WHERE embedding IS NOT NULL')
            ).scalar()
            if count and count > 0:
                db.execute(text(
                    'CREATE INDEX IF NOT EXISTS issues_embedding_hnsw '
                    'ON issues USING hnsw (embedding vector_cosine_ops) '
                    'WITH (m = 16, ef_construction = 64)'
                ))
                db.commit()
    except Exception as exc:
        from observability.logging_utils import log_event
        log_event('startup_warn', {'action': 'hnsw_index', 'error': str(exc)[:200]})


def _backfill():
    """Embed any issues lacking embeddings; build HNSW index after."""
    try:
        from services.embedding_service import backfill_issue_embeddings
        backfill_issue_embeddings()
        _run_hnsw_index()
    except Exception as exc:
        from observability.logging_utils import log_event
        log_event('startup_warn', {'action': 'embedding_backfill', 'error': str(exc)[:200]})


def _start_embedding_worker():
    """
    Daemon: polls every 5 minutes for new un-embedded issues.
    Handles incremental data: any issue inserted after startup is embedded
    via CDC (sub-second) AND this fallback (≤5 min) for resilience.
    """
    def _worker():
        while True:
            time.sleep(300)
            _backfill()

    threading.Thread(target=_worker, daemon=True, name='embedding-backfill').start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    _backfill()
    _start_embedding_worker()

    # CDC: real-time embed on INSERT/UPDATE + escalation trigger
    from services.cdc_listener import start_cdc_listener
    start_cdc_listener()

    # Autonomous: health sweep every 15 min, churn signal daily
    from services.autonomous_agent import start_autonomous_scheduler
    start_autonomous_scheduler()

    yield


app = FastAPI(title='Acme Operations Agentic Assistant', lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
templates = Jinja2Templates(directory="templates")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
