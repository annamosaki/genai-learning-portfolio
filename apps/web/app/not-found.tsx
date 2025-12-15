import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-xl flex-col items-start justify-center px-4 py-24">
      <p className="font-mono text-xs text-[var(--color-accent)]">404</p>
      <h1 className="display mt-2 text-4xl">Page not found</h1>
      <Link href="/" className="btn btn-primary mt-6">
        Back home
      </Link>
    </div>
  );
}
