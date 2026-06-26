export default function Architecture() {
  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '26px 28px' }}>

        <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 16, padding: '24px 24px 20px', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: '#1C1C23' }}>System Architecture</div>
              <div style={{ fontSize: 12.5, color: '#9A9AA6', marginTop: 3 }}>LangGraph ReAct · autonomous agent · CDC streaming · RAG · two-layer cache · persistent memory</div>
            </div>
            <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              {([['#2A5BC0','Client'],['#B4232A','Security'],['#1C1C23','Application'],['#6D4AB6','Intelligence'],['#1F7A4D','Data']] as [string,string][]).map(([c,l]) => (
                <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 10, height: 10, borderRadius: '50%', background: c, display: 'inline-block', flexShrink: 0 }} />
                  <span style={{ fontSize: 12.5, color: '#6B6B78' }}>{l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* viewBox expanded (1220×760) to include autonomous, CDC, cache, memory nodes */}
          <svg viewBox="0 0 1220 760" width="100%" xmlns="http://www.w3.org/2000/svg" style={{ display: 'block', fontFamily: 'Manrope, sans-serif' }}>
            <defs>
              <marker id="ah"  markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#A0A0AE"/></marker>
              <marker id="ahB" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#2A5BC0"/></marker>
              <marker id="ahR" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#B4232A"/></marker>
              <marker id="ahP" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#6D4AB6"/></marker>
              <marker id="ahG" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#1F7A4D"/></marker>
              <marker id="ahY" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#9A6B00"/></marker>
            </defs>

            {/* ── Column backgrounds ── */}
            <rect x="0"   y="0" width="196" height="760" fill="#EDF2FB"/>
            <rect x="196" y="0" width="188" height="760" fill="#FEF1F1"/>
            <rect x="384" y="0" width="210" height="760" fill="#F5F4FA"/>
            <rect x="594" y="0" width="210" height="760" fill="#F1EEF9"/>
            <rect x="804" y="0" width="416" height="760" fill="#EDF6F1"/>

            {/* Column dividers */}
            {[195, 383, 593, 803].map(x => <line key={x} x1={x} y1="0" x2={x} y2="760" stroke="#E0E0EA" strokeWidth="1"/>)}

            {/* ── Column headers ── */}
            <text x="98"  y="28" textAnchor="middle" fontSize="10.5" fontWeight="800" fill="#2A5BC0" letterSpacing="1.2">CLIENT</text>
            <text x="290" y="28" textAnchor="middle" fontSize="10.5" fontWeight="800" fill="#B4232A" letterSpacing="1.2">SECURITY</text>
            <text x="489" y="28" textAnchor="middle" fontSize="10.5" fontWeight="800" fill="#3D3D4F" letterSpacing="1.2">APPLICATION</text>
            <text x="699" y="28" textAnchor="middle" fontSize="10.5" fontWeight="800" fill="#6D4AB6" letterSpacing="1.2">INTELLIGENCE</text>
            <text x="1012" y="28" textAnchor="middle" fontSize="10.5" fontWeight="800" fill="#1F7A4D" letterSpacing="1.2">DATA</text>

            {/* ── CLIENT ── */}
            <rect x="14" y="46" width="168" height="80" rx="10" fill="#fff" stroke="#BFCFEF" strokeWidth="1.4"/>
            <circle cx="31" cy="72" r="6" fill="#2A5BC0"/>
            <text x="44" y="77" fontSize="13" fontWeight="800" fill="#1C1C23">Atlas UI</text>
            <text x="24" y="97" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">React · Vite · :5173</text>
            <text x="24" y="111" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">bearer token · SSE</text>

            <rect x="14" y="168" width="168" height="68" rx="10" fill="#fff" stroke="#BFCFEF" strokeWidth="1.4"/>
            <circle cx="31" cy="192" r="6" fill="#2A5BC0"/>
            <text x="44" y="197" fontSize="13" fontWeight="800" fill="#1C1C23">API Client</text>
            <text x="24" y="217" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">curl · eval harness</text>
            <text x="24" y="230" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">POST /query</text>

            {/* ── SECURITY ── */}
            <rect x="208" y="46" width="162" height="80" rx="10" fill="#fff" stroke="#EFC0C0" strokeWidth="1.4"/>
            <circle cx="225" cy="72" r="6" fill="#B4232A"/>
            <text x="238" y="77" fontSize="13" fontWeight="800" fill="#1C1C23">API Gateway</text>
            <text x="218" y="97" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">nginx :443</text>
            <text x="218" y="111" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">TLS · rate-limit</text>

            <rect x="208" y="168" width="162" height="68" rx="10" fill="#fff" stroke="#EFC0C0" strokeWidth="1.4"/>
            <circle cx="225" cy="192" r="6" fill="#B4232A"/>
            <text x="238" y="197" fontSize="13" fontWeight="800" fill="#1C1C23">Identity &amp; Access</text>
            <text x="218" y="217" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">Keycloak :8080</text>
            <text x="218" y="230" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">OIDC · JWKS</text>

            {/* ── APPLICATION ── */}

            {/* LangGraph Orchestrator — featured */}
            <rect x="396" y="38" width="186" height="90" rx="10" fill="#1C1C23" stroke="#3D3D4F" strokeWidth="1.4"/>
            <circle cx="416" cy="64" r="6" fill="#FFE600"/>
            <text x="430" y="69" fontSize="13" fontWeight="800" fill="#fff">LangGraph Orchestrator</text>
            <text x="406" y="90" fontSize="10.5" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">FastAPI :8000</text>
            <text x="406" y="104" fontSize="10.5" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">graph_orchestrator.py</text>

            {/* Pre-flight Disambiguation */}
            <rect x="396" y="178" width="186" height="72" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="416" cy="200" r="6" fill="#9A6B00"/>
            <text x="430" y="205" fontSize="13" fontWeight="800" fill="#1C1C23">Pre-flight Disambig</text>
            <text x="406" y="225" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">search_customers tool</text>
            <text x="406" y="239" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">LLM-driven · pg_trgm</text>

            {/* RBAC Gate */}
            <rect x="396" y="302" width="186" height="68" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="416" cy="324" r="6" fill="#B4232A"/>
            <text x="430" y="329" fontSize="13" fontWeight="800" fill="#1C1C23">RBAC Gate</text>
            <text x="406" y="350" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">security.py</text>
            <text x="406" y="363" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">role-per-tool · pre-exec</text>

            {/* Session Cache */}
            <rect x="396" y="422" width="186" height="68" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="416" cy="444" r="6" fill="#9A6B00"/>
            <text x="430" y="449" fontSize="13" fontWeight="800" fill="#1C1C23">Session Cache</text>
            <text x="406" y="469" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">Redis :6379</text>
            <text x="406" y="483" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">TTL 15 min – 1 h</text>

            {/* Telemetry */}
            <rect x="396" y="510" width="186" height="60" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="416" cy="532" r="5.5" fill="#1F7A4D"/>
            <text x="430" y="537" fontSize="13" fontWeight="800" fill="#1C1C23">Telemetry</text>
            <text x="406" y="557" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">logging_utils.py · JSON</text>

            {/* ── INTELLIGENCE ── */}

            {/* ReAct Think Node — featured */}
            <rect x="608" y="38" width="182" height="90" rx="10" fill="#1C1C23" stroke="#3D3D4F" strokeWidth="1.4"/>
            <circle cx="628" cy="64" r="6" fill="#6D4AB6"/>
            <text x="642" y="69" fontSize="13" fontWeight="800" fill="#fff">ReAct Think Node</text>
            <text x="618" y="90" fontSize="10.5" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">GPT-4.1-mini · iterative</text>
            <text x="618" y="104" fontSize="10.5" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">max 6 iterations</text>

            {/* ReAct loop annotation */}
            <rect x="762" y="50" width="22" height="68" rx="4" fill="none" stroke="#FFE600" strokeWidth="1.2" strokeDasharray="3,2"/>
            <text x="773" y="90" fontSize="9" fill="#FFE600" fontFamily="JetBrains Mono,monospace" textAnchor="middle" transform="rotate(-90,773,90)">loop</text>

            {/* Synthesizer */}
            <rect x="608" y="178" width="182" height="72" rx="10" fill="#fff" stroke="#D0C8F0" strokeWidth="1.4"/>
            <circle cx="628" cy="200" r="6" fill="#6D4AB6"/>
            <text x="642" y="205" fontSize="13" fontWeight="800" fill="#1C1C23">Synthesizer</text>
            <text x="618" y="225" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">GPT-4.1-mini</text>
            <text x="618" y="239" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">answer_synthesizer.py</text>

            {/* Risk Assessor */}
            <rect x="608" y="302" width="182" height="68" rx="10" fill="#fff" stroke="#D0C8F0" strokeWidth="1.4"/>
            <circle cx="628" cy="324" r="6" fill="#9A6B00"/>
            <text x="642" y="329" fontSize="13" fontWeight="800" fill="#1C1C23">Risk Assessor</text>
            <text x="618" y="350" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">deterministic rubric</text>
            <text x="618" y="363" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">customer_escalation.py</text>

            {/* ── DATA ── */}

            {/* Tool Server — featured */}
            <rect x="820" y="38" width="208" height="90" rx="10" fill="#1C1C23" stroke="#2D3D2D" strokeWidth="1.4"/>
            <circle cx="840" cy="64" r="6" fill="#4ADE80"/>
            <text x="854" y="69" fontSize="13" fontWeight="800" fill="#fff">Tool Server</text>
            <text x="830" y="90" fontSize="10.5" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">MCP :8100</text>
            <text x="830" y="104" fontSize="10.5" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">3s timeout · DB fallback</text>

            {/* Operations DB */}
            <rect x="820" y="178" width="208" height="82" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="840" cy="202" r="6" fill="#1F7A4D"/>
            <text x="854" y="207" fontSize="13" fontWeight="800" fill="#1C1C23">Operations DB</text>
            <text x="830" y="228" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">PostgreSQL :5432</text>
            <text x="830" y="242" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">pg_trgm · pgvector(1536)</text>

            {/* Embedding Service */}
            <rect x="820" y="314" width="208" height="72" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="840" cy="337" r="6" fill="#6D4AB6"/>
            <text x="854" y="342" fontSize="13" fontWeight="800" fill="#1C1C23">Embedding Service</text>
            <text x="830" y="362" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">text-embedding-3-small</text>
            <text x="830" y="376" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">1536-dim · backfill startup</text>

            {/* Proactive Alerts */}
            <rect x="820" y="444" width="208" height="72" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="840" cy="467" r="6" fill="#B4232A"/>
            <text x="854" y="472" fontSize="13" fontWeight="800" fill="#1C1C23">Proactive Alerts</text>
            <text x="830" y="492" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">GET /alerts</text>
            <text x="830" y="506" fontSize="10.5" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">health scan · 60s poll</text>

            {/* ── AUTONOMOUS & REAL-TIME ── */}
            <line x1="820" y1="534" x2="1218" y2="534" stroke="#C0E0D0" strokeWidth="1" strokeDasharray="4,3"/>
            <text x="820" y="530" fontSize="9" fontWeight="700" fill="#1F7A4D" fontFamily="JetBrains Mono,monospace" letterSpacing="0.8">AUTONOMOUS  ·  REAL-TIME</text>

            {/* Autonomous Agent */}
            <rect x="820" y="538" width="194" height="82" rx="10" fill="#1C1C23" stroke="#2D3D2D" strokeWidth="1.4"/>
            <circle cx="840" cy="562" r="6" fill="#4ADE80"/>
            <text x="854" y="567" fontSize="12.5" fontWeight="800" fill="#fff">Autonomous Agent</text>
            <text x="830" y="588" fontSize="10" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">health sweep · 15 min</text>
            <text x="830" y="601" fontSize="10" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">churn signal · daily</text>

            {/* CDC Listener */}
            <rect x="1022" y="538" width="186" height="82" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="1042" cy="562" r="6" fill="#1F7A4D"/>
            <text x="1056" y="567" fontSize="12.5" fontWeight="800" fill="#1C1C23">CDC Listener</text>
            <text x="1032" y="588" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">pg_notify LISTEN</text>
            <text x="1032" y="601" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">issue_updated · note_added</text>

            {/* Two-layer Query Cache */}
            <rect x="820" y="630" width="194" height="90" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="840" cy="654" r="6" fill="#9A6B00"/>
            <text x="854" y="659" fontSize="12.5" fontWeight="800" fill="#1C1C23">Query Cache</text>
            <text x="830" y="679" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">L1: Redis SHA-256 · 15min</text>
            <text x="830" y="692" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">L2: pgvector cosine &gt;0.92</text>
            <text x="830" y="705" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">semantic dedup · 1h TTL</text>

            {/* Persistent Memory */}
            <rect x="1022" y="630" width="186" height="90" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="1042" cy="654" r="6" fill="#1F7A4D"/>
            <text x="1056" y="659" fontSize="12.5" fontWeight="800" fill="#1C1C23">Persistent Memory</text>
            <text x="1032" y="679" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">scope: user / session</text>
            <text x="1032" y="692" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">key-value · TTL aware</text>
            <text x="1032" y="705" fontSize="10" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">Redis + PostgreSQL</text>

            {/* ── ARROWS ── */}

            {/* Atlas UI → API Gateway */}
            <line x1="183" y1="86" x2="207" y2="86" stroke="#2A5BC0" strokeWidth="1.6" markerEnd="url(#ahB)"/>
            <text x="185" y="81" fontSize="9.5" fill="#2A5BC0" fontFamily="JetBrains Mono,monospace" fontWeight="600">HTTPS</text>

            {/* API Client → API Gateway (elbow) */}
            <path d="M183,202 L196,202 L196,120 L207,120" stroke="#2A5BC0" strokeWidth="1.4" fill="none" markerEnd="url(#ahB)"/>

            {/* API Gateway → LangGraph Orchestrator */}
            <line x1="371" y1="86" x2="395" y2="86" stroke="#B4232A" strokeWidth="1.6" markerEnd="url(#ahR)"/>
            <text x="373" y="81" fontSize="9.5" fill="#B4232A" fontFamily="JetBrains Mono,monospace" fontWeight="600">JWT ✓</text>

            {/* API Gateway ↔ Identity & Access (JWKS) */}
            <line x1="289" y1="127" x2="289" y2="167" stroke="#B4232A" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ahR)"/>
            <text x="293" y="151" fontSize="9.5" fill="#B4232A" fontFamily="JetBrains Mono,monospace" fontWeight="600">JWKS</text>

            {/* LangGraph Orchestrator → Pre-flight Disambig */}
            <line x1="489" y1="129" x2="489" y2="177" stroke="#9A6B00" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ahY)"/>

            {/* Pre-flight Disambig → RBAC Gate */}
            <line x1="489" y1="251" x2="489" y2="301" stroke="#A0A0AE" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ah)"/>

            {/* LangGraph Orchestrator → ReAct Think Node */}
            <line x1="583" y1="83" x2="607" y2="83" stroke="#6D4AB6" strokeWidth="1.6" markerEnd="url(#ahP)"/>
            <text x="585" y="78" fontSize="9.5" fill="#6D4AB6" fontFamily="JetBrains Mono,monospace" fontWeight="600">think</text>

            {/* ReAct Think Node → Tool Server */}
            <line x1="791" y1="83" x2="819" y2="83" stroke="#1F7A4D" strokeWidth="1.6" markerEnd="url(#ahG)"/>
            <text x="793" y="78" fontSize="9.5" fill="#1F7A4D" fontFamily="JetBrains Mono,monospace" fontWeight="600">execute</text>

            {/* Tool Server → Operations DB */}
            <line x1="924" y1="129" x2="924" y2="177" stroke="#1F7A4D" strokeWidth="1.4" markerEnd="url(#ahG)"/>
            <text x="928" y="157" fontSize="9.5" fill="#1F7A4D" fontFamily="JetBrains Mono,monospace" fontWeight="600">SQL</text>

            {/* Operations DB → Embedding Service */}
            <line x1="924" y1="261" x2="924" y2="313" stroke="#6D4AB6" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ahP)"/>
            <text x="928" y="292" fontSize="9.5" fill="#6D4AB6" fontFamily="JetBrains Mono,monospace" fontWeight="600">embed</text>

            {/* ReAct Think Node — loop arrow (execute → think, curved) */}
            <path d="M791,60 L800,60 L800,110 L791,110" stroke="#FFE600" strokeWidth="1.3" fill="none" strokeDasharray="3,2" markerEnd="url(#ahP)"/>

            {/* Tool outputs → Synthesizer */}
            <path d="M489,129 L489,160 L608,160 L608,177" stroke="#6D4AB6" strokeWidth="1.3" fill="none" strokeDasharray="5,3" markerEnd="url(#ahP)"/>
            <text x="510" y="156" fontSize="9.5" fill="#6D4AB6" fontFamily="JetBrains Mono,monospace" fontWeight="600">tool outputs</text>

            {/* AI Orchestrator → Risk Assessor */}
            <path d="M489,129 L489,284 L608,284 L608,301" stroke="#9A6B00" strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ahY)"/>

            {/* LangGraph Orchestrator ↔ Session Cache */}
            <path d="M489,129 L489,160 L440,160 L440,421" stroke="#A0A0AE" strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ah)"/>

            {/* Embedding → Operations DB (backfill) */}
            <path d="M924,313 L960,313 L960,260 L1029,260" stroke="#6D4AB6" strokeWidth="1.2" fill="none" strokeDasharray="4,3"/>

            {/* Proactive Alerts → Autonomous Agent */}
            <line x1="924" y1="517" x2="924" y2="537" stroke="#1F7A4D" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ahG)"/>

            {/* Autonomous Agent → Operations DB (reads + writes briefings) */}
            <path d="M917,538 L917,260" stroke="#1F7A4D" strokeWidth="1.2" fill="none" strokeDasharray="3,3" markerEnd="url(#ahG)"/>

            {/* CDC Listener ← Operations DB (pg_notify) */}
            <path d="M1029,245 L1115,245 L1115,537" stroke="#1F7A4D" strokeWidth="1.2" fill="none" strokeDasharray="3,3" markerEnd="url(#ahG)"/>
            <text x="1034" y="240" fontSize="9" fill="#1F7A4D" fontFamily="JetBrains Mono,monospace" fontWeight="600">pg_notify</text>

            {/* Query Cache ← LangGraph Orchestrator (cache check) */}
            <path d="M440,421 L440,675 L819,675" stroke="#9A6B00" strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ahY)"/>

            {/* Persistent Memory ← ReAct loop */}
            <path d="M699,160 L1115,160 L1115,629" stroke="#6D4AB6" strokeWidth="1.1" fill="none" strokeDasharray="4,3" markerEnd="url(#ahP)"/>
          </svg>

          {/* Arrow legend */}
          <div style={{ display: 'flex', gap: 24, marginTop: 16, paddingTop: 14, borderTop: '1px solid #F0F0F4', flexWrap: 'wrap' }}>
            {[
              ['──', '#2A5BC0', 'Primary request path'],
              ['──', '#B4232A', 'Authentication flow'],
              ['──', '#6D4AB6', 'AI planning / synthesis'],
              ['──', '#1F7A4D', 'Data retrieval'],
              ['──', '#FFE600', 'ReAct loop (think→execute)'],
              ['- -', '#9A9AA6', 'Internal dispatch'],
            ].map(([dash, color, label]) => (
              <div key={label as string} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 14, color: color as string, fontWeight: 700, letterSpacing: 1 }}>{dash}</span>
                <span style={{ fontSize: 12.5, color: '#6B6B78' }}>{label as string}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Request lifecycle */}
        <div style={{ background: '#1C1C23', borderRadius: 18, padding: '26px 30px' }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: '#FFE600', textTransform: 'uppercase', letterSpacing: '.09em', marginBottom: 20 }}>Request lifecycle</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px 44px' }}>
            {([
              ['1', 'User submits query. Keycloak issues an OIDC token (or x-role header in APP_ENV=local).'],
              ['7', 'Each tool call passes through the RBAC Gate before execution. Write tools (recommend_next_action) require support_user or admin. Blocked calls return a 403 SSE event.'],
              ['2', 'Client calls POST /query/stream with the bearer token through nginx :443 → FastAPI :8000. Response streams via SSE. nginx uses consistent-hash routing (X-Forwarded-For) for SSE stickiness across pods.'],
              ['8', 'Tool Server routes calls to MCP :8100 (3 s timeout) with direct-DB fallback. RAG: conceptual queries embed via text-embedding-3-small (1536-dim) and retrieve via pgvector cosine similarity.'],
              ['3', 'FastAPI validates JWT via Keycloak JWKS and extracts the user role. Two-layer query cache is checked: L1 Redis exact-match (SHA-256, 15 min TTL), L2 pgvector semantic similarity (cosine > 0.92, 1 h TTL).'],
              ['9', 'Risk Assessor applies a deterministic rubric to produce risk level, urgency, and recommended next action. Response Synthesizer (GPT-4.1-mini) streams the final answer. Persistent memory updated with session context.'],
              ['4', 'Pre-flight handles confirmed names. For ambiguous fragments ("nexi", "pinnacle"), the ReAct LLM calls the search_customers tool (pg_trgm fuzzy match). 1 result → auto-resolved; multiple → LLM presents options; 0 → LLM tells user.'],
              ['10','Proactive Alerts scans all customers on each poll (60 s). Critical / amber accounts surface as a sidebar badge. Autonomous Agent runs health sweeps every 15 min and churn signals daily; results are stored as briefings in PostgreSQL.'],
              ['5', 'LangGraph StateGraph enters the ReAct loop: pre_flight → think → rbac_gate → execute → think (repeat) → risk_assess → END.'],
              ['11','CDC Listener (pg_notify) watches issue_updated and issue_note_added channels. Critical escalations trigger immediate briefing creation without waiting for the next scheduled sweep.'],
              ['6', 'ReAct Think Node (GPT-4.1-mini) observes results so far and decides the next single tool — or "done". Persistent memory provides cross-session customer context. Iterates up to 6 times.'],
              ['12','Write audit log: every durable write (recommend_next_action, create_issue) is dual-recorded to Redis (24 h, fast debug) and PostgreSQL write_audit table (permanent compliance record). Trace ID threaded end-to-end.'],
            ] as [string,string][]).map(([n, t]) => (
              <div key={n} style={{ display: 'flex', gap: 14 }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700, color: '#FFE600', flexShrink: 0, marginTop: 1, minWidth: 18 }}>{n}</span>
                <span style={{ fontSize: 13, color: '#C7C7D2', lineHeight: 1.6 }}>{t}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
