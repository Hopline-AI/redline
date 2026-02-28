import { Link } from 'react-router-dom';
import { FileSearch, Layers, Code, ShieldCheck, ArrowRight } from 'lucide-react';
import { SEO } from '@/components/SEO';

export default function Landing() {
  return (
    <div className="container" style={{ paddingBottom: 'var(--space-10)' }}>
      <SEO 
        title="Redline | Explainable Compliance Engine"
        description="Verify policies with deterministic logic. AI doesn't interpret the law. It extracts the rules."
      />

      <section style={{ textAlign: 'center', padding: 'var(--space-10) 0', maxWidth: '800px', margin: '0 auto' }}>
        <p style={{ color: 'var(--primary)', fontWeight: 600, fontSize: 'var(--text-7)', marginBottom: 'var(--space-4)' }}>Explainable Compliance Engine</p>
        <h1 style={{ fontSize: 'clamp(2.5rem, 5vw, 4.5rem)', fontWeight: 800, letterSpacing: '-0.02em', textWrap: 'balance', marginBottom: 'var(--space-4)' }}>
          Verify policies with deterministic logic
        </h1>
        <p style={{ color: 'var(--muted-foreground)', fontSize: 'var(--text-6)', lineHeight: 1.6, textWrap: 'balance', margin: '0 auto var(--space-6)' }}>
          AI doesn’t interpret the law, it extracts the rules. Our deterministic engine checks your HR policies against California and Federal legislation with zero hallucination risk.
        </p>
        <div className="hstack gap-3" style={{ justifyContent: 'center' }}>
          <Link to="/" className="btn btn-primary" style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '1rem' }}>
            Start Compliance Check
            <ArrowRight size={18} />
          </Link>
          <a href="#how-it-works" className="btn btn-secondary" style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '1rem' }}>
            View Architecture
          </a>
        </div>
      </section>

      <section className="mb-8" style={{ maxWidth: '900px', margin: '0 auto var(--space-10)' }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <h2 style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em', textWrap: 'balance' }}>The old way vs. The Redline way</h2>
        </div>
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
          <div className="card" style={{ padding: 'var(--space-6)', opacity: 0.8 }}>
            <div className="hstack gap-2 mb-4">
              <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--danger)' }} />
              <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Manual Review</h3>
            </div>
            <ul className="vstack gap-3" style={{ listStyle: 'none', padding: 0, color: 'var(--muted-foreground)' }}>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--danger)', fontWeight: 'bold' }}>×</span> Requires expensive outside counsel</li>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--danger)', fontWeight: 'bold' }}>×</span> Weeks to process entire employee handbooks</li>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--danger)', fontWeight: 'bold' }}>×</span> Inconsistent interpretations between attorneys</li>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--danger)', fontWeight: 'bold' }}>×</span> Misses state vs. federal edge cases</li>
            </ul>
          </div>
          <div className="card" style={{ padding: 'var(--space-6)', border: '2px solid var(--border)' }}>
            <div className="hstack gap-2 mb-4">
              <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--success)' }} />
              <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Redline Engine</h3>
            </div>
            <ul className="vstack gap-3" style={{ listStyle: 'none', padding: 0 }}>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--success)', fontWeight: 'bold' }}>✓</span> Instant, on-premise execution</li>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--success)', fontWeight: 'bold' }}>✓</span> Complete handbook processed in minutes</li>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--success)', fontWeight: 'bold' }}>✓</span> Deterministic comparison avoids AI hallucinations</li>
              <li style={{ display: 'flex', gap: 'var(--space-2)' }}><span style={{ color: 'var(--success)', fontWeight: 'bold' }}>✓</span> Automatic mapping of CA vs Federal conflicts</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="how-it-works" style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <h2 style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em', textWrap: 'balance' }}>How it works under the hood</h2>
          <p style={{ color: 'var(--muted-foreground)', textWrap: 'balance' }}>We designed the system so that AI does exactly one thing: extract data. Code handles the rest.</p>
        </div>

        <div className="vstack gap-4">
          <div className="card hstack gap-4 align-start" style={{ padding: 'var(--space-6)' }}>
            <div style={{ flexShrink: 0, width: 48, height: 48, borderRadius: 'var(--radius-medium)', backgroundColor: 'var(--faint)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FileSearch size={24} color="var(--primary)" />
            </div>
            <div>
              <h3 style={{ margin: '0 0 var(--space-1) 0' }}>Ingest & Parse</h3>
              <p style={{ margin: 0, color: 'var(--muted-foreground)' }}>Upload your California HR policy PDF. We extract raw text safely and chunk it by section.</p>
            </div>
          </div>
          
          <div style={{ width: 2, height: 24, backgroundColor: 'var(--border)', margin: '0 auto' }} />

          <div className="card" style={{ padding: 'var(--space-6)' }}>
            <div className="hstack gap-4 align-start mb-4">
              <div style={{ flexShrink: 0, width: 48, height: 48, borderRadius: 'var(--radius-medium)', backgroundColor: 'var(--faint)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Layers size={24} color="var(--primary)" />
              </div>
              <div>
                <h3 style={{ margin: '0 0 var(--space-1) 0' }}>Mistral 7B Extraction</h3>
                <p style={{ margin: 0, color: 'var(--muted-foreground)' }}>Fine-tuned to output strict JSON. It extracts the rules into a standardized schema.</p>
              </div>
            </div>
            <pre style={{ margin: 0, padding: 'var(--space-4)', backgroundColor: 'var(--faint)', borderRadius: 'var(--radius-medium)', borderLeft: '3px solid var(--primary)', fontSize: '0.85rem' }}>
              <code className="tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{`{
  "rule_type": "restriction",
  "conditions": [{
    "field": "employee.count",
    "operator": "gte",
    "value": 75
  }],
  "action": { "type": "require" }
}`}</code>
            </pre>
          </div>

          <div style={{ width: 2, height: 24, backgroundColor: 'var(--border)', margin: '0 auto' }} />

          <div className="card" style={{ padding: 'var(--space-6)' }}>
            <div className="hstack gap-4 align-start mb-4">
              <div style={{ flexShrink: 0, width: 48, height: 48, borderRadius: 'var(--radius-medium)', backgroundColor: 'var(--faint)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Code size={24} color="var(--primary)" />
              </div>
              <div>
                <h3 style={{ margin: '0 0 var(--space-1) 0' }}>Deterministic Comparison</h3>
                <p style={{ margin: 0, color: 'var(--muted-foreground)' }}>Our pure-code engine compares the extracted JSON against structured CA & Federal legislation.</p>
              </div>
            </div>
             <pre style={{ margin: 0, padding: 'var(--space-4)', backgroundColor: 'var(--faint)', borderRadius: 'var(--radius-medium)', borderLeft: '3px solid var(--danger)', fontSize: '0.85rem' }}>
              <code className="tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{`if (policy.notice_days < ca.warn.notice_days) {
  return "contradicts";
} else if (policy.notice_days > fed.warn.notice_days) {
  return "exceeds";
}`}</code>
            </pre>
          </div>

          <div style={{ width: 2, height: 24, backgroundColor: 'var(--border)', margin: '0 auto' }} />

          <div className="card hstack gap-4 align-start" style={{ padding: 'var(--space-6)' }}>
             <div style={{ flexShrink: 0, width: 48, height: 48, borderRadius: 'var(--radius-medium)', backgroundColor: 'var(--faint)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShieldCheck size={24} color="var(--primary)" />
            </div>
            <div>
              <h3 style={{ margin: '0 0 var(--space-1) 0' }}>Lawyer Review & Reinforcement</h3>
              <p style={{ margin: 0, color: 'var(--muted-foreground)' }}>Lawyers review the exact conflicts. Every approval or edit feeds back into our continuous retrain loop via W&B.</p>
            </div>
          </div>
        </div>
      </section>

      <footer style={{ marginTop: 'var(--space-10)', textAlign: 'center', padding: 'var(--space-8) 0', borderTop: '1px solid var(--border)' }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: 'var(--space-6)', textWrap: 'balance' }}>Ready to audit your policies?</h2>
        <Link to="/" className="btn btn-primary btn-lg">
          Upload Policy Document
        </Link>
        <p style={{ marginTop: 'var(--space-8)', color: 'var(--muted-foreground)', fontSize: 'var(--text-7)' }}>
          © 2026 Redline — Built for Mistral Worldwide Hackathon
        </p>
      </footer>
    </div>
  );
}
