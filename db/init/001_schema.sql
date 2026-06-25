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
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
