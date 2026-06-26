CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS customers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  segment VARCHAR(100),
  account_owner VARCHAR(255),
  health_status VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS issues (
  id SERIAL PRIMARY KEY,
  customer_id INT REFERENCES customers(id),
  title VARCHAR(255) NOT NULL,
  severity VARCHAR(50),
  status VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS issue_updates (
  id SERIAL PRIMARY KEY,
  issue_id INT REFERENCES issues(id),
  update_text TEXT NOT NULL,
  updated_by VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS next_actions (
  id SERIAL PRIMARY KEY,
  issue_id INT REFERENCES issues(id),
  action_text TEXT NOT NULL,
  owner VARCHAR(255),
  due_date DATE,
  status VARCHAR(50) DEFAULT 'proposed',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL,
  role_name VARCHAR(100) NOT NULL
);

-- ── Performance indexes for scale ────────────────────────────────────────────
-- GIN trigram index: accelerates pg_trgm fuzzy customer name search
CREATE INDEX IF NOT EXISTS idx_customers_name_trgm
  ON customers USING GIN (name gin_trgm_ops);

-- B-tree on account_owner: RLS filter (WHERE account_owner = :owner)
CREATE INDEX IF NOT EXISTS idx_customers_account_owner
  ON customers (account_owner);

-- Functional indexes on issues: status/severity filters become index scans
CREATE INDEX IF NOT EXISTS idx_issues_status
  ON issues (LOWER(status));

CREATE INDEX IF NOT EXISTS idx_issues_severity
  ON issues (LOWER(severity));

-- Composite index for the common filter: customer + status
CREATE INDEX IF NOT EXISTS idx_issues_customer_status
  ON issues (customer_id, LOWER(status));

-- issue_updates: history fetch is ORDER BY created_at per issue_id
CREATE INDEX IF NOT EXISTS idx_issue_updates_issue_created
  ON issue_updates (issue_id, created_at);

-- next_actions: lookup per issue is always ordered by created_at
CREATE INDEX IF NOT EXISTS idx_next_actions_issue_created
  ON next_actions (issue_id, created_at);
