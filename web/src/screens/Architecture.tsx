export default function Architecture() {
  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '26px 28px' }}>

        <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 16, padding: '24px 24px 20px', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: '#1C1C23' }}>System Architecture</div>
              <div style={{ fontSize: 12.5, color: '#9A9AA6', marginTop: 3 }}>Five-layer request flow — from user to data and back</div>
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

          <svg viewBox="0 0 1060 490" width="100%" xmlns="http://www.w3.org/2000/svg" style={{ display: 'block', fontFamily: 'Manrope, sans-serif' }}>
            <defs>
              <marker id="ah"  markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#A0A0AE"/></marker>
              <marker id="ahB" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#2A5BC0"/></marker>
              <marker id="ahR" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#B4232A"/></marker>
              <marker id="ahP" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#6D4AB6"/></marker>
              <marker id="ahG" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><polygon points="0 0,8 4,0 8" fill="#1F7A4D"/></marker>
            </defs>

            {/* Column backgrounds */}
            <rect x="0"   y="0" width="193" height="490" fill="#EDF2FB"/>
            <rect x="194" y="0" width="185" height="490" fill="#FEF1F1"/>
            <rect x="380" y="0" width="200" height="490" fill="#F5F4FA"/>
            <rect x="581" y="0" width="199" height="490" fill="#F1EEF9"/>
            <rect x="781" y="0" width="279" height="490" fill="#EDF6F1"/>

            {/* Column dividers */}
            {[193, 379, 580, 780].map(x => <line key={x} x1={x} y1="0" x2={x} y2="490" stroke="#E0E0EA" strokeWidth="1"/>)}

            {/* Column headers */}
            <text x="96"  y="28" textAnchor="middle" fontSize="11" fontWeight="800" fill="#2A5BC0" letterSpacing="1.2">CLIENT</text>
            <text x="286" y="28" textAnchor="middle" fontSize="11" fontWeight="800" fill="#B4232A" letterSpacing="1.2">SECURITY</text>
            <text x="480" y="28" textAnchor="middle" fontSize="11" fontWeight="800" fill="#3D3D4F" letterSpacing="1.2">APPLICATION</text>
            <text x="680" y="28" textAnchor="middle" fontSize="11" fontWeight="800" fill="#6D4AB6" letterSpacing="1.2">INTELLIGENCE</text>
            <text x="920" y="28" textAnchor="middle" fontSize="11" fontWeight="800" fill="#1F7A4D" letterSpacing="1.2">DATA</text>

            {/* CLIENT — Atlas UI */}
            <rect x="14" y="46" width="165" height="80" rx="10" fill="#fff" stroke="#BFCFEF" strokeWidth="1.4"/>
            <circle cx="31" cy="72" r="6" fill="#2A5BC0"/>
            <text x="44" y="77" fontSize="14" fontWeight="800" fill="#1C1C23">Atlas UI</text>
            <text x="24" y="98" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">React · Vite · :5173</text>
            <text x="24" y="113" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">bearer token</text>

            {/* CLIENT — API Client */}
            <rect x="14" y="170" width="165" height="70" rx="10" fill="#fff" stroke="#BFCFEF" strokeWidth="1.4"/>
            <circle cx="31" cy="194" r="6" fill="#2A5BC0"/>
            <text x="44" y="199" fontSize="14" fontWeight="800" fill="#1C1C23">API Client</text>
            <text x="24" y="220" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">curl · eval harness</text>
            <text x="24" y="234" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">POST /query</text>

            {/* SECURITY — API Gateway */}
            <rect x="207" y="46" width="159" height="80" rx="10" fill="#fff" stroke="#EFC0C0" strokeWidth="1.4"/>
            <circle cx="224" cy="72" r="6" fill="#B4232A"/>
            <text x="237" y="77" fontSize="14" fontWeight="800" fill="#1C1C23">API Gateway</text>
            <text x="217" y="98" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">nginx :443</text>
            <text x="217" y="113" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">TLS termination</text>

            {/* SECURITY — Identity & Access */}
            <rect x="207" y="170" width="159" height="70" rx="10" fill="#fff" stroke="#EFC0C0" strokeWidth="1.4"/>
            <circle cx="224" cy="194" r="6" fill="#B4232A"/>
            <text x="237" y="199" fontSize="14" fontWeight="800" fill="#1C1C23">Identity &amp; Access</text>
            <text x="217" y="220" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">Keycloak :8080</text>
            <text x="217" y="234" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">OIDC · JWKS</text>

            {/* APPLICATION — AI Orchestrator (featured) */}
            <rect x="393" y="38" width="174" height="90" rx="10" fill="#1C1C23" stroke="#3D3D4F" strokeWidth="1.4"/>
            <circle cx="412" cy="66" r="6" fill="#FFE600"/>
            <text x="425" y="71" fontSize="14" fontWeight="800" fill="#fff">AI Orchestrator</text>
            <text x="403" y="94" fontSize="12" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">FastAPI :8000</text>
            <text x="403" y="108" fontSize="11" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">orchestrator.py</text>

            {/* APPLICATION — Access Control */}
            <rect x="393" y="180" width="174" height="70" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="412" cy="204" r="6" fill="#B4232A"/>
            <text x="425" y="209" fontSize="14" fontWeight="800" fill="#1C1C23">Access Control</text>
            <text x="403" y="231" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">security.py</text>
            <text x="403" y="244" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">role-per-tool check</text>

            {/* APPLICATION — Session Cache */}
            <rect x="393" y="300" width="174" height="70" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="412" cy="324" r="6" fill="#9A6B00"/>
            <text x="425" y="329" fontSize="14" fontWeight="800" fill="#1C1C23">Session Cache</text>
            <text x="403" y="352" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">Redis :6379</text>
            <text x="403" y="365" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">TTL 15 min – 1 h</text>

            {/* APPLICATION — Telemetry */}
            <rect x="393" y="416" width="174" height="58" rx="10" fill="#fff" stroke="#E0DFF2" strokeWidth="1.4"/>
            <circle cx="412" cy="438" r="5.5" fill="#1F7A4D"/>
            <text x="425" y="443" fontSize="14" fontWeight="800" fill="#1C1C23">Telemetry</text>
            <text x="403" y="462" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">logging_utils.py · JSON</text>

            {/* INTELLIGENCE — Query Planner */}
            <rect x="595" y="38" width="172" height="90" rx="10" fill="#fff" stroke="#D0C8F0" strokeWidth="1.4"/>
            <circle cx="614" cy="66" r="6" fill="#6D4AB6"/>
            <text x="627" y="71" fontSize="14" fontWeight="800" fill="#1C1C23">Query Planner</text>
            <text x="605" y="94" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">GPT-4.1-mini</text>
            <text x="605" y="108" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">planner.py</text>

            {/* INTELLIGENCE — Synthesizer */}
            <rect x="595" y="180" width="172" height="70" rx="10" fill="#fff" stroke="#D0C8F0" strokeWidth="1.4"/>
            <circle cx="614" cy="204" r="6" fill="#6D4AB6"/>
            <text x="627" y="209" fontSize="14" fontWeight="800" fill="#1C1C23">Synthesizer</text>
            <text x="605" y="231" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">GPT-4.1-mini</text>
            <text x="605" y="244" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">answer_synthesizer.py</text>

            {/* INTELLIGENCE — Risk Assessor */}
            <rect x="595" y="300" width="172" height="70" rx="10" fill="#fff" stroke="#D0C8F0" strokeWidth="1.4"/>
            <circle cx="614" cy="324" r="6" fill="#9A6B00"/>
            <text x="627" y="329" fontSize="14" fontWeight="800" fill="#1C1C23">Risk Assessor</text>
            <text x="605" y="352" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">deterministic</text>
            <text x="605" y="365" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">customer_escalation.py</text>

            {/* DATA — Tool Server (featured) */}
            <rect x="795" y="38" width="200" height="90" rx="10" fill="#1C1C23" stroke="#2D3D2D" strokeWidth="1.4"/>
            <circle cx="816" cy="66" r="6" fill="#4ADE80"/>
            <text x="830" y="71" fontSize="14" fontWeight="800" fill="#fff">Tool Server</text>
            <text x="806" y="94" fontSize="12" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">MCP :8100</text>
            <text x="806" y="108" fontSize="11" fill="#A6A6B2" fontFamily="JetBrains Mono,monospace">3s timeout · DB fallback</text>

            {/* DATA — Operations DB */}
            <rect x="795" y="180" width="200" height="70" rx="10" fill="#fff" stroke="#C0E0D0" strokeWidth="1.4"/>
            <circle cx="816" cy="204" r="6" fill="#1F7A4D"/>
            <text x="830" y="209" fontSize="14" fontWeight="800" fill="#1C1C23">Operations DB</text>
            <text x="806" y="231" fontSize="12" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">PostgreSQL :5432</text>
            <text x="806" y="244" fontSize="11" fill="#9A9AA6" fontFamily="JetBrains Mono,monospace">pg_trgm · fuzzy match</text>

            {/* Arrows */}

            {/* Atlas UI → API Gateway */}
            <line x1="180" y1="86" x2="206" y2="86" stroke="#2A5BC0" strokeWidth="1.6" markerEnd="url(#ahB)"/>
            <text x="183" y="81" fontSize="10" fill="#2A5BC0" fontFamily="JetBrains Mono,monospace" fontWeight="600">HTTPS</text>

            {/* API Client → API Gateway (elbow up along column edge) */}
            <path d="M180,205 L194,205 L194,120 L206,120" stroke="#2A5BC0" strokeWidth="1.4" fill="none" markerEnd="url(#ahB)"/>

            {/* API Gateway → AI Orchestrator */}
            <line x1="367" y1="86" x2="392" y2="86" stroke="#B4232A" strokeWidth="1.6" markerEnd="url(#ahR)"/>
            <text x="369" y="81" fontSize="10" fill="#B4232A" fontFamily="JetBrains Mono,monospace" fontWeight="600">JWT ✓</text>

            {/* API Gateway ↔ Identity & Access (JWKS) */}
            <line x1="286" y1="127" x2="286" y2="169" stroke="#B4232A" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ahR)"/>
            <text x="290" y="152" fontSize="10" fill="#B4232A" fontFamily="JetBrains Mono,monospace" fontWeight="600">JWKS</text>

            {/* AI Orchestrator → Query Planner */}
            <line x1="568" y1="83" x2="594" y2="83" stroke="#6D4AB6" strokeWidth="1.6" markerEnd="url(#ahP)"/>
            <text x="571" y="78" fontSize="10" fill="#6D4AB6" fontFamily="JetBrains Mono,monospace" fontWeight="600">plan</text>

            {/* Query Planner → Tool Server */}
            <line x1="768" y1="83" x2="794" y2="83" stroke="#1F7A4D" strokeWidth="1.6" markerEnd="url(#ahG)"/>
            <text x="770" y="78" fontSize="10" fill="#1F7A4D" fontFamily="JetBrains Mono,monospace" fontWeight="600">tool calls</text>

            {/* Tool Server → Operations DB */}
            <line x1="895" y1="129" x2="895" y2="179" stroke="#1F7A4D" strokeWidth="1.4" markerEnd="url(#ahG)"/>
            <text x="899" y="158" fontSize="10" fill="#1F7A4D" fontFamily="JetBrains Mono,monospace" fontWeight="600">SQL</text>

            {/* AI Orchestrator ↓ Access Control (internal dispatch) */}
            <line x1="480" y1="129" x2="480" y2="179" stroke="#A0A0AE" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ah)"/>

            {/* Access Control ↓ Session Cache */}
            <line x1="480" y1="251" x2="480" y2="299" stroke="#A0A0AE" strokeWidth="1.3" strokeDasharray="4,3" markerEnd="url(#ah)"/>

            {/* AI Orchestrator → Synthesizer (tool outputs after execution) */}
            <path d="M480,129 L480,157 L595,157 L595,179" stroke="#6D4AB6" strokeWidth="1.3" fill="none" strokeDasharray="5,3" markerEnd="url(#ahP)"/>
            <text x="504" y="153" fontSize="10" fill="#6D4AB6" fontFamily="JetBrains Mono,monospace" fontWeight="600">tool outputs</text>

            {/* AI Orchestrator → Risk Assessor */}
            <path d="M480,129 L480,274 L595,274 L595,299" stroke="#9A6B00" strokeWidth="1.2" fill="none" strokeDasharray="4,3" markerEnd="url(#ah)"/>
          </svg>

          {/* Arrow legend */}
          <div style={{ display: 'flex', gap: 24, marginTop: 16, paddingTop: 14, borderTop: '1px solid #F0F0F4', flexWrap: 'wrap' }}>
            {[
              ['──', '#2A5BC0', 'Primary request path'],
              ['──', '#B4232A', 'Authentication flow'],
              ['──', '#6D4AB6', 'AI planning / synthesis'],
              ['──', '#1F7A4D', 'Data retrieval'],
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
              ['1', 'User selects identity. Keycloak issues an OIDC token (or x-role header in APP_ENV=local).'],
              ['5', 'Orchestrator calls the Query Planner (GPT-4.1-mini) to decide which tools to invoke.'],
              ['2', 'Client calls POST /query with the bearer token through nginx :443 → FastAPI :8000.'],
              ['6', 'Each tool call is RBAC-checked, then routed through MCP :8100 to Postgres with 3s timeout + direct fallback.'],
              ['3', 'FastAPI validates the token via Keycloak JWKS and extracts the user role.'],
              ['7', 'The Risk Assessor skill composes a deterministic escalation signal from the retrieved data.'],
              ['4', 'Session context and customer lookup cache are read from Redis (15 min – 1 h TTL).'],
              ['8', 'Response Synthesizer (GPT-4.1-mini) generates a natural-language answer from structured tool outputs. Logs emitted. Answer returned.'],
            ] as [string,string][]).map(([n, t]) => (
              <div key={n} style={{ display: 'flex', gap: 14 }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 700, color: '#FFE600', flexShrink: 0, marginTop: 1 }}>{n}</span>
                <span style={{ fontSize: 13.5, color: '#C7C7D2', lineHeight: 1.6 }}>{t}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
