/**
 * Escape Multi Zone basePath and return to the portfolio home.
 * Must be a plain <a> — Next.js Link would stay inside /demos/...
 */
export function BackToPortfolio({ className = '' }: { className?: string }) {
  const home = process.env.NEXT_PUBLIC_PORTFOLIO_URL || 'http://localhost:3000';

  return (
    <a
      href={home}
      className={
        className ||
        'inline-flex items-center gap-1.5 text-sm text-muted hover:text-accent transition-colors'
      }
      title="Back to portfolio home"
    >
      <span aria-hidden>←</span>
      <span>Portfolio</span>
    </a>
  );
}
