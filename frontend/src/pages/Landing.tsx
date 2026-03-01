import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { SEO } from '@/components/SEO';
import Redline from '@/components/Redline';

export default function Landing() {
  return (
    <div className="container" style={{ minHeight: 'calc(100vh - 8rem)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <SEO 
        title="Redline | Explainable Compliance Engine"
        description="Verify policies with deterministic logic. AI doesn't interpret the law. It extracts the rules."
      />

      <section style={{ textAlign: 'center', maxWidth: '800px', width: '100%', padding: 'var(--space-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 'var(--space-4)' }}>
          <Redline style={{ width: 64, height: 64 }} />
        </div>
        <p style={{ color: 'var(--primary)', fontWeight: 600, fontSize: 'var(--text-7)', marginBottom: 'var(--space-4)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Redline Compliance
        </p>
        <h1 style={{ fontSize: 'clamp(3rem, 6vw, 5rem)', fontWeight: 800, letterSpacing: '-0.03em', textWrap: 'balance', marginBottom: 'var(--space-5)', lineHeight: 1.05, color: 'var(--foreground)' }}>
          <span style={{ color: 'var(--danger)' }}>Deterministic</span> Policy Verification
        </h1>
        <p style={{ color: 'var(--muted-foreground)', fontSize: 'clamp(1.1rem, 2vw, 1.25rem)', lineHeight: 1.6, textWrap: 'balance', margin: '0 auto var(--space-8)', maxWidth: '600px' }}>
          AI extracts the rules. Code handles the rest. Audit your HR policies against state and federal legislation instantly, with zero hallucination risk.
        </p>
        <div className="hstack gap-4" style={{ justifyContent: 'center' }}>
          <Link to="/" className="btn btn-primary" style={{ padding: '0 var(--space-6)', height: '3rem', fontSize: '1rem' }}>
            Upload Policy
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </div>
  );
}
