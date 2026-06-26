-- ──────────────────────────────────────────────────────────────────────────
-- ACME OPS — BFSI DEMO SEED
-- Idempotent: truncates and re-seeds on every run
-- ──────────────────────────────────────────────────────────────────────────
TRUNCATE next_actions, issue_updates, issues, customers RESTART IDENTITY CASCADE;

-- ──────────────────────────────────────────────────────────────────────────
-- CUSTOMERS  (3 red · 4 amber · 3 green)
-- alice.sales owns 7 (the red/amber book — used in main eval cases)
-- james.whitfield owns 3 green customers — proves RLS filters by account_owner
-- ──────────────────────────────────────────────────────────────────────────
INSERT INTO customers (name, segment, account_owner, health_status) VALUES
('Pinnacle Bancorp',           'Enterprise',  'alice.sales',      'red'),
('Apex Clearing Services',     'Mid-Market',  'alice.sales',      'red'),
('Nexus Payments Ltd',         'Mid-Market',  'alice.sales',      'red'),
('Meridian Capital Group',     'Enterprise',  'alice.sales',      'amber'),
('Fortuna Wealth Management',  'Mid-Market',  'alice.sales',      'amber'),
('Sterling Asset Management',  'Enterprise',  'alice.sales',      'amber'),
('Atlas Merchant Bank',        'Enterprise',  'alice.sales',      'amber'),
('Sovereign Life & Annuities', 'Enterprise',  'james.whitfield',  'green'),
('Harborview Credit Union',    'SME',         'james.whitfield',  'green'),
('Dominion Insurance Group',   'Enterprise',  'james.whitfield',  'green');

-- ──────────────────────────────────────────────────────────────────────────
-- ISSUES
-- ──────────────────────────────────────────────────────────────────────────

-- Pinnacle Bancorp (RED) ─────────────────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Core banking EOD batch failure: GL balance posting incomplete', 'critical', 'open'
FROM customers WHERE name = 'Pinnacle Bancorp';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'AML screening queue backlog breaching 4-hour SLA threshold', 'high', 'open'
FROM customers WHERE name = 'Pinnacle Bancorp';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Mobile banking 504 timeouts during morning peak 09:00-11:00 GMT', 'high', 'open'
FROM customers WHERE name = 'Pinnacle Bancorp';

-- Apex Clearing Services (RED) ───────────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'FIX drop-copy session disconnects causing unreported trades at market open', 'critical', 'open'
FROM customers WHERE name = 'Apex Clearing Services';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Margin call mismatch vs prime broker: USD 2.3M variance on GBP-STRAT-004', 'high', 'in_progress'
FROM customers WHERE name = 'Apex Clearing Services';

-- Nexus Payments Ltd (RED) ───────────────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'ISO 20022 pacs.008 rejection rate at 12% following SWIFT cutover', 'critical', 'open'
FROM customers WHERE name = 'Nexus Payments Ltd';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'PSD2 Open Banking API returning HTTP 429 errors to three regulated TPPs', 'high', 'open'
FROM customers WHERE name = 'Nexus Payments Ltd';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Chargeback reconciliation lag: 2,400 unmatched transactions pending over 72 hours', 'high', 'open'
FROM customers WHERE name = 'Nexus Payments Ltd';

-- Meridian Capital Group (AMBER) ─────────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'T+2 settlement reconciliation breaks on multi-leg equity structured trades', 'high', 'open'
FROM customers WHERE name = 'Meridian Capital Group';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'IBOR-to-SOFR: residual GBP LIBOR references in 12 institutional fund fact sheets', 'medium', 'in_progress'
FROM customers WHERE name = 'Meridian Capital Group';

-- Fortuna Wealth Management (AMBER) ──────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'MiFID II transaction reporting: 340 equity trades late-filed to FCA via ARM', 'high', 'open'
FROM customers WHERE name = 'Fortuna Wealth Management';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Client portal P99 latency degraded to 8.2s against 2s contractual SLA', 'medium', 'open'
FROM customers WHERE name = 'Fortuna Wealth Management';

-- Sterling Asset Management (AMBER) ──────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Bloomberg B-PIPE feed drops causing NAV calculation delays on 3 funds', 'high', 'in_progress'
FROM customers WHERE name = 'Sterling Asset Management';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'SFDR PAI report missing 4 mandatory Level 2 indicators: deadline risk', 'medium', 'open'
FROM customers WHERE name = 'Sterling Asset Management';

-- Atlas Merchant Bank (AMBER) ─────────────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'KYC periodic review overdue: 180 corporate accounts beyond 12-month refresh cycle', 'high', 'open'
FROM customers WHERE name = 'Atlas Merchant Bank';

-- ──────────────────────────────────────────────────────────────────────────
-- ISSUE UPDATES
-- ──────────────────────────────────────────────────────────────────────────

-- Core banking EOD batch
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'EOD batch initiated 22:00 UTC. Job step 7 (GL balance aggregation) failed at 23:14 with ORA-12899 column value too large. DBA team engaged; incident bridge opened with 12 participants.',
  'ops.lead'
FROM issues i WHERE i.title = 'Core banking EOD batch failure: GL balance posting incomplete';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Root cause confirmed: GL account code field expanded from 8 to 10 digits in Q4 upgrade; batch ETL configuration was not updated to reflect the new column width. Fix developed and deployed to staging; regression suite running.',
  'dev.lead'
FROM issues i WHERE i.title = 'Core banking EOD batch failure: GL balance posting incomplete';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Business impact: 3,847 accounts showing T-1 stale balances. Interim manual reconciliation file issued to Finance. Emergency change window approved for Saturday 02:00 UTC. CISO and CRO briefed.',
  'ops.manager'
FROM issues i WHERE i.title = 'Core banking EOD batch failure: GL balance posting incomplete';

-- AML screening queue
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Queue depth at 1,240 alerts vs SLA threshold of 400. Overnight batch import of 8,200 cross-border transactions triggered volume spike beyond staffed analyst capacity.',
  'compliance.lead'
FROM issues i WHERE i.title = 'AML screening queue backlog breaching 4-hour SLA threshold';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Additional analyst resource mobilised from the offshore KYC/AML team. Processing rate increased from 85 to 210 alerts per hour. Estimated full queue clearance by 09:00 UTC tomorrow.',
  'ops.manager'
FROM issues i WHERE i.title = 'AML screening queue backlog breaching 4-hour SLA threshold';

-- Mobile banking 504s
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  '504 errors first reported by customers at 09:12 GMT. APM traces confirm p99 latency on account-summary microservice spiking to 18s vs 800ms baseline. Load balancer health checks passing; issue appears downstream.',
  'dev.lead'
FROM issues i WHERE i.title = 'Mobile banking 504 timeouts during morning peak 09:00-11:00 GMT';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Suspected connection pool exhaustion on the PostgreSQL read-replica. Pool limit raised from 200 to 350 as interim measure. Monitoring dashboards confirm error rate dropped from 18% to 3% post-change. Watching for recurrence.',
  'infra.team'
FROM issues i WHERE i.title = 'Mobile banking 504 timeouts during morning peak 09:00-11:00 GMT';

-- FIX drop-copy
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Drop-copy session to Euronext experiencing TCP resets at 08:00:03 CET each morning since Monday. Approximately 340 trades per session going unreported to the CCP, triggering a T+1 reporting obligation breach.',
  'dev.lead'
FROM issues i WHERE i.title = 'FIX drop-copy session disconnects causing unreported trades at market open';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Network team identified MTU mismatch (1500 vs 1480) between clearing gateway and co-location switch following last week''s firewall firmware upgrade. MTU alignment fix applied in co-lo at 14:00 CET. Session monitoring active.',
  'infra.team'
FROM issues i WHERE i.title = 'FIX drop-copy session disconnects causing unreported trades at market open';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Session remained stable for 4 hours post-fix then recurred at market close 17:30 CET. Packet captures collected and sent to Euronext network engineering for joint root-cause analysis.',
  'ops.lead'
FROM issues i WHERE i.title = 'FIX drop-copy session disconnects causing unreported trades at market open';

-- Margin call mismatch
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'USD 2.3M discrepancy identified on morning margin run for portfolio GBP-STRAT-004 versus Goldman Sachs prime broker statement. Margin call formally contested; positions frozen pending investigation.',
  'ops.lead'
FROM issues i WHERE i.title = 'Margin call mismatch vs prime broker: USD 2.3M variance on GBP-STRAT-004';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Trade reconciliation team cross-referencing 1,840 individual positions. Suspected cause: ex-dividend adjustment not applied to 6 ETF basket constituents following the MSCI rebalance on 19 Jan.',
  'support.analyst'
FROM issues i WHERE i.title = 'Margin call mismatch vs prime broker: USD 2.3M variance on GBP-STRAT-004';

-- ISO 20022 pacs.008
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Rejection rate climbed from 3% on go-live day to 12% by day 3. Total 1,847 pacs.008 payments rejected by correspondent banks. Primary reason: BIC11 validation failing for 6 respondent banks not yet migrated to ISO 20022.',
  'dev.lead'
FROM issues i WHERE i.title = 'ISO 20022 pacs.008 rejection rate at 12% following SWIFT cutover';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'SWIFT service desk ticket raised (ref SWIFT-2024-00341). Interim workaround agreed: affected payments re-routed via legacy MT103 pathway. Note: this fallback pathway closes in March 2025.',
  'ops.manager'
FROM issues i WHERE i.title = 'ISO 20022 pacs.008 rejection rate at 12% following SWIFT cutover';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'All 6 affected BICs identified. 4 have confirmed migration timelines within 30 days. 2 have not responded to outreach. Legal team drafting contractual compliance notices to non-responsive correspondents.',
  'compliance.lead'
FROM issues i WHERE i.title = 'ISO 20022 pacs.008 rejection rate at 12% following SWIFT cutover';

-- PSD2 / Open Banking 429s
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Moneyhub, TrueLayer, and Yapily reporting HTTP 429 responses between 08:00-09:30 GMT. Rate limiter configured at 600 req/min per TPP; Moneyhub burst traffic peaking at 940 req/min.',
  'dev.lead'
FROM issues i WHERE i.title = 'PSD2 Open Banking API returning HTTP 429 errors to three regulated TPPs';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Rate limit breach triggers FCA PSD2 Article 33(6) obligation to investigate and provide written response within 5 working days. Compliance team formally notified; FCA notification clock started.',
  'compliance.lead'
FROM issues i WHERE i.title = 'PSD2 Open Banking API returning HTTP 429 errors to three regulated TPPs';

-- Chargeback lag
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Mastercard MCOM chargeback portal file import failing silently since Tuesday due to SFTP certificate expiry. 2,400 chargebacks are in an unprocessed state — neither disputed nor accepted — breaching the 72-hour scheme deadline.',
  'ops.lead'
FROM issues i WHERE i.title = 'Chargeback reconciliation lag: 2,400 unmatched transactions pending over 72 hours';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'SFTP certificate renewed and import re-triggered. All 2,400 transactions ingested. Automated matching resolved 1,820 (76%) immediately. 580 require manual review where match confidence is below the 85% threshold.',
  'support.analyst'
FROM issues i WHERE i.title = 'Chargeback reconciliation lag: 2,400 unmatched transactions pending over 72 hours';

-- T+2 settlement reconciliation
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Reconciliation engine flagged 47 unmatched trades from Wednesday session. All failures are multi-leg structured equity strategies with more than 3 legs, not matching against BNY Mellon custodian confirmations.',
  'ops.lead'
FROM issues i WHERE i.title = 'T+2 settlement reconciliation breaks on multi-leg equity structured trades';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'BNY Mellon confirm their records are correct. Root cause: internal aggregation logic for netted wash trades within the same portfolio on the same ISIN is incorrectly de-duplicating legs.',
  'support.analyst'
FROM issues i WHERE i.title = 'T+2 settlement reconciliation breaks on multi-leg equity structured trades';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Patch developed to correct the netted position logic. Deployed to UAT. All 47 historical trades re-matched successfully in UAT environment. Awaiting Operations Director sign-off before production deployment.',
  'dev.lead'
FROM issues i WHERE i.title = 'T+2 settlement reconciliation breaks on multi-leg equity structured trades';

-- IBOR-to-SOFR
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Post-transition audit identified 12 institutional fund fact sheets still referencing GBP LIBOR as benchmark rate. LIBOR ceased 30 June 2023. Continued reference constitutes a regulatory disclosure risk ahead of next FCA filing.',
  'compliance.lead'
FROM issues i WHERE i.title = 'IBOR-to-SOFR: residual GBP LIBOR references in 12 institutional fund fact sheets';

-- MiFID II late filing
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'ARM submission for equity trades executed 15 Jan failed due to FIX tag 58 (Text) encoding issue. Special characters in trader commentary caused XML schema validation failure at the Approved Reporting Mechanism.',
  'dev.lead'
FROM issues i WHERE i.title = 'MiFID II transaction reporting: 340 equity trades late-filed to FCA via ARM';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Legal and Compliance notified. Voluntary disclosure letter drafted for FCA submission. Maximum financial exposure under MAR Article 25 estimated at GBP 500,000. Board Risk Committee informed.',
  'compliance.lead'
FROM issues i WHERE i.title = 'MiFID II transaction reporting: 340 equity trades late-filed to FCA via ARM';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'FIX encoder patch deployed to UAT. Full regression test suite passed with zero failures. CCB approval for production deployment submitted; scheduled for 48 hours pending sign-off from CTO.',
  'dev.lead'
FROM issues i WHERE i.title = 'MiFID II transaction reporting: 340 equity trades late-filed to FCA via ARM';

-- Portal latency
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Portal performance degradation first reported by relationship managers on Monday. Synthetic monitoring confirms P99 latency at 8.2s versus 2s contractual SLA. Affects portfolio summary and document download flows.',
  'dev.lead'
FROM issues i WHERE i.title = 'Client portal P99 latency degraded to 8.2s against 2s contractual SLA';

-- Bloomberg B-PIPE
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Bloomberg B-PIPE TCP connection dropping every 40-90 minutes since Monday 08:00. NAV calculations for Emerging Market Bond Fund, Global Equity Fund, and Multi-Asset Income Fund delayed up to 3 hours per day.',
  'ops.lead'
FROM issues i WHERE i.title = 'Bloomberg B-PIPE feed drops causing NAV calculation delays on 3 funds';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Bloomberg TAC case opened (ref BLP-2024-09812). Interim workaround: switched affected feeds to Bloomberg API pull model. All three funds completed today''s NAV run successfully via the fallback path.',
  'dev.lead'
FROM issues i WHERE i.title = 'Bloomberg B-PIPE feed drops causing NAV calculation delays on 3 funds';

-- SFDR PAI
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Pre-submission validation against ESMA technical standard v2.1 failed. Four mandatory PAI indicators missing: #5 (GHG emissions intensity), #9 (biodiversity), #13 (controversial weapons exposure), #16 (gender pay gap ratio). Submission deadline is 30 June.',
  'compliance.lead'
FROM issues i WHERE i.title = 'SFDR PAI report missing 4 mandatory Level 2 indicators: deadline risk';

-- KYC overdue
INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Risk-based KYC refresh cycle flagged 180 corporate accounts (out of 940 active) where the last full review was more than 12 months ago. 22 are classified High Risk under FCA JMLSG guidance, requiring a 6-month review cycle.',
  'compliance.lead'
FROM issues i WHERE i.title = 'KYC periodic review overdue: 180 corporate accounts beyond 12-month refresh cycle';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Account restrictions applied to all 22 High Risk accounts pending completion of reviews. Relationship managers notified individually. 60-day remediation programme submitted to MLRO for approval.',
  'ops.manager'
FROM issues i WHERE i.title = 'KYC periodic review overdue: 180 corporate accounts beyond 12-month refresh cycle';

-- ──────────────────────────────────────────────────────────────────────────
-- NEXT ACTIONS
-- ──────────────────────────────────────────────────────────────────────────

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Deploy GL batch ETL config fix to production in approved emergency change window (Saturday 02:00 UTC) and validate balance postings across all 3,847 affected accounts before business open',
  'infra.team', CURRENT_DATE + INTERVAL '2 days', 'approved'
FROM issues i WHERE i.title = 'Core banking EOD batch failure: GL balance posting incomplete';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Implement dynamic intraday alert throttling to cap import rate at 600/hour; present capacity model and staffing proposal to Compliance Committee by month-end',
  'compliance.lead', CURRENT_DATE + INTERVAL '14 days', 'proposed'
FROM issues i WHERE i.title = 'AML screening queue backlog breaching 4-hour SLA threshold';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Instrument connection pool metrics with Prometheus; implement circuit-breaker and exponential back-off on account-summary service to prevent cascade failure during future pool exhaustion events',
  'dev.lead', CURRENT_DATE + INTERVAL '5 days', 'proposed'
FROM issues i WHERE i.title = 'Mobile banking 504 timeouts during morning peak 09:00-11:00 GMT';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Conduct joint network root-cause session with Euronext engineering; implement FIX session keep-alive tuning and persistent MTU configuration on clearing gateway; validate over 3 consecutive market opens',
  'dev.lead', CURRENT_DATE + INTERVAL '3 days', 'approved'
FROM issues i WHERE i.title = 'FIX drop-copy session disconnects causing unreported trades at market open';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Apply ex-dividend adjustments to 6 affected ETF basket positions in margin engine and re-run GBP-STRAT-004 margin calculation; escalate to Goldman Sachs relationship manager if variance persists beyond EOD',
  'ops.manager', CURRENT_DATE + INTERVAL '1 day', 'approved'
FROM issues i WHERE i.title = 'Margin call mismatch vs prime broker: USD 2.3M variance on GBP-STRAT-004';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Escalate 2 non-responsive correspondents to SWIFT relationship manager; implement BIC-level routing table to isolate non-migrated banks from pacs.008 path and prevent further rejections',
  'ops.manager', CURRENT_DATE + INTERVAL '7 days', 'approved'
FROM issues i WHERE i.title = 'ISO 20022 pacs.008 rejection rate at 12% following SWIFT cutover';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Increase rate limit for regulated TPPs to 1,200 req/min with burst allowance; replace sliding-window algorithm with token-bucket implementation; notify FCA of remediation steps and timeline within 5 working days',
  'dev.lead', CURRENT_DATE + INTERVAL '5 days', 'proposed'
FROM issues i WHERE i.title = 'PSD2 Open Banking API returning HTTP 429 errors to three regulated TPPs';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Complete manual review of 580 unmatched chargebacks within scheme deadline window; implement TLS certificate expiry alerting with 30-day advance notification to prevent recurrence',
  'ops.lead', CURRENT_DATE + INTERVAL '3 days', 'approved'
FROM issues i WHERE i.title = 'Chargeback reconciliation lag: 2,400 unmatched transactions pending over 72 hours';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Obtain Operations Director sign-off on UAT results and schedule production deployment in Sunday maintenance window (06:00-08:00 UTC); run full T+2 reconciliation cycle post-deployment to confirm fix',
  'ops.manager', CURRENT_DATE + INTERVAL '4 days', 'proposed'
FROM issues i WHERE i.title = 'T+2 settlement reconciliation breaks on multi-leg equity structured trades';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Update all 12 fund fact sheet templates in document management system to reference SONIA/SOFR benchmarks; republish via investor portal and file corrected versions with FCA within the 30-day voluntary disclosure window',
  'compliance.lead', CURRENT_DATE + INTERVAL '21 days', 'proposed'
FROM issues i WHERE i.title = 'IBOR-to-SOFR: residual GBP LIBOR references in 12 institutional fund fact sheets';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Deploy FIX encoder patch to production following CCB sign-off; backfill 340 late trade reports via ARM replay mechanism; submit voluntary disclosure letter to FCA and log on regulatory breach register',
  'compliance.lead', CURRENT_DATE + INTERVAL '2 days', 'approved'
FROM issues i WHERE i.title = 'MiFID II transaction reporting: 340 equity trades late-filed to FCA via ARM';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Profile API bottleneck using distributed tracing (Jaeger); implement Redis caching layer on portfolio summary endpoint — currently executing an unbounded DB query on every page load',
  'dev.lead', CURRENT_DATE + INTERVAL '7 days', 'proposed'
FROM issues i WHERE i.title = 'Client portal P99 latency degraded to 8.2s against 2s contractual SLA';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Implement automatic B-PIPE to Bloomberg API failover triggered when TCP session drops for more than 5 minutes; raise SLA credit claim with Bloomberg TAC for the outage period',
  'dev.lead', CURRENT_DATE + INTERVAL '5 days', 'proposed'
FROM issues i WHERE i.title = 'Bloomberg B-PIPE feed drops causing NAV calculation delays on 3 funds';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Engage MSCI ESG data team to source PAI indicators #5, #9, #13, #16 for all portfolio holdings; update SFDR PAI template and re-validate against ESMA v2.1 schema ahead of 30 June deadline',
  'compliance.lead', CURRENT_DATE + INTERVAL '30 days', 'proposed'
FROM issues i WHERE i.title = 'SFDR PAI report missing 4 mandatory Level 2 indicators: deadline risk';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Complete enhanced KYC refresh for all 22 High Risk corporate accounts within 30 days; mobilise additional KYC analyst resource to address remaining 158 Standard Risk accounts within the 60-day MLRO-approved programme',
  'compliance.lead', CURRENT_DATE + INTERVAL '30 days', 'approved'
FROM issues i WHERE i.title = 'KYC periodic review overdue: 180 corporate accounts beyond 12-month refresh cycle';

-- ──────────────────────────────────────────────────────────────────────────
-- GREEN CUSTOMERS — resolved & waiting issues to populate filter tabs
-- ──────────────────────────────────────────────────────────────────────────

-- Sovereign Life & Annuities (GREEN) ─────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Solvency II SCR model validation: third-party actuarial sign-off obtained', 'high', 'resolved'
FROM customers WHERE name = 'Sovereign Life & Annuities';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Policy admin migration to new core platform: UAT sign-off pending client review', 'medium', 'waiting'
FROM customers WHERE name = 'Sovereign Life & Annuities';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Solvency II internal model SCR calculation fully validated by Willis Towers Watson. PRA pre-application submission accepted. Issue closed — no further action required.',
  'compliance.lead'
FROM issues i WHERE i.title = 'Solvency II SCR model validation: third-party actuarial sign-off obtained';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'UAT completed successfully across all 14 test scenarios. Awaiting Sovereign Life sign-off on the UAT evidence pack before production cutover can be scheduled. Client confirmed review window of 5-7 business days.',
  'ops.lead'
FROM issues i WHERE i.title = 'Policy admin migration to new core platform: UAT sign-off pending client review';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Chase client for UAT sign-off; schedule production cutover call for following week once approval received',
  'alice.sales', CURRENT_DATE + INTERVAL '5 days', 'proposed'
FROM issues i WHERE i.title = 'Policy admin migration to new core platform: UAT sign-off pending client review';

-- Harborview Credit Union (GREEN) ─────────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'NCUA exam findings remediation: all 3 management letter items addressed and closed', 'high', 'resolved'
FROM customers WHERE name = 'Harborview Credit Union';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'ACH origination limit increase request: awaiting Federal Reserve approval', 'medium', 'waiting'
FROM customers WHERE name = 'Harborview Credit Union';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'All three NCUA management letter items (BSA/AML programme gap, overdraft policy disclosure, IT contingency plan) fully remediated. Examiner confirmed acceptance in writing on 14 Jan. Issue closed.',
  'compliance.lead'
FROM issues i WHERE i.title = 'NCUA exam findings remediation: all 3 management letter items addressed and closed';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Application submitted to Federal Reserve Bank of San Francisco on 3 Jan for ACH origination limit increase from USD 2M to USD 5M per day. Typical review window 30-45 business days. No further action until decision received.',
  'ops.manager'
FROM issues i WHERE i.title = 'ACH origination limit increase request: awaiting Federal Reserve approval';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Follow up with Federal Reserve relationship contact after 30 business days if no decision received; prepare interim ACH controls to accommodate member demand in the interim',
  'alice.sales', CURRENT_DATE + INTERVAL '22 days', 'proposed'
FROM issues i WHERE i.title = 'ACH origination limit increase request: awaiting Federal Reserve approval';

-- Dominion Insurance Group (GREEN) ───────────────────────────────────────
INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'Lloyd''s syndicate reporting: Xchanging premium reconciliation discrepancy resolved', 'high', 'resolved'
FROM customers WHERE name = 'Dominion Insurance Group';

INSERT INTO issues (customer_id, title, severity, status)
SELECT id, 'FCA Consumer Duty evidence framework: board paper drafted, awaiting board approval', 'medium', 'waiting'
FROM customers WHERE name = 'Dominion Insurance Group';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'GBP 140K premium reconciliation break on Syndicate 2623 traced to a duplicate bordereaux submission from a managing agent. Xchanging confirmed correction applied. Year-end bordereau reconciles to zero. Issue closed.',
  'ops.lead'
FROM issues i WHERE i.title = 'Lloyd''s syndicate reporting: Xchanging premium reconciliation discrepancy resolved';

INSERT INTO issue_updates (issue_id, update_text, updated_by)
SELECT i.id,
  'Consumer Duty board paper drafted covering product governance, price and value assessments, and customer support outcomes. Compliance Director has approved content. Scheduled for board meeting on 28 Feb — awaiting chair confirmation.',
  'compliance.lead'
FROM issues i WHERE i.title = 'FCA Consumer Duty evidence framework: board paper drafted, awaiting board approval';

INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
SELECT i.id,
  'Confirm board agenda slot with Dominion chair''s office; prepare executive summary briefing pack for non-executive directors ahead of the Consumer Duty paper',
  'james.whitfield', CURRENT_DATE + INTERVAL '10 days', 'proposed'
FROM issues i WHERE i.title = 'FCA Consumer Duty evidence framework: board paper drafted, awaiting board approval';

-- ──────────────────────────────────────────────────────────────────────────
-- USER ROLES
-- ──────────────────────────────────────────────────────────────────────────
INSERT INTO user_roles (username, role_name) VALUES
('alice.sales',   'sales_user'),
('bob.support',   'support_user'),
('carol.admin',   'admin')
ON CONFLICT DO NOTHING;
