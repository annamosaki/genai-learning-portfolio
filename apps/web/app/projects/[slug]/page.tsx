import { notFound } from "next/navigation";
import Link from "next/link";
import { cv } from "@content/cv";
import { DemoEmbed } from "@/components/demos/DemoEmbed";
import { ZoneLink } from "@/components/zone-link";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateStaticParams() {
  return cv.projects.map((project) => ({
    slug: project.slug,
  }));
}

export default async function ProjectPage({ params }: Props) {
  const { slug } = await params;
  const project = cv.projects.find((p) => p.slug === slug);

  if (!project) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div className="mb-8">
        <Link
          href="/#projects"
          className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-muted)] hover:text-[var(--color-accent)]"
        >
          ← Back to projects
        </Link>
        <h1 className="display mb-2 text-3xl font-medium tracking-tight">
          {project.number} {project.title}
        </h1>
        <p className="text-lg text-[var(--color-muted)]">{project.tagline}</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {project.status === "live" && project.demoUrl ? (
            <DemoEmbed 
              url={project.demoUrl} 
              title={project.title}
              className="mb-8"
            />
          ) : (
            <div className="mb-8 rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-8 text-center">
              <div className="mb-4 text-4xl opacity-50">🚧</div>
              <h3 className="mb-2 text-lg font-medium">Coming Soon</h3>
              <p className="text-[var(--color-muted)]">This demo is still in development.</p>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div>
            <h3 className="mb-3 font-medium">Status</h3>
            <span
              className={`chip ${
                project.status === "live"
                  ? "border-green-500/30 bg-green-500/10 text-green-400"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-400"
              }`}
            >
              {project.status === "live" ? "Live" : "In Development"}
            </span>
          </div>

          <div>
            <h3 className="mb-3 font-medium">Stack</h3>
            <div className="flex flex-wrap gap-2">
              {project.stack.map((tech) => (
                <span key={tech} className="chip text-xs">
                  {tech}
                </span>
              ))}
            </div>
          </div>

          {project.comingSoon.length > 0 && (
            <div>
              <h3 className="mb-3 font-medium">Coming Soon</h3>
              <ul className="space-y-1 text-sm text-[var(--color-muted)]">
                {project.comingSoon.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="h-1 w-1 rounded-full bg-[var(--color-accent)]" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-col gap-3">
            {project.demoUrl && (
              <ZoneLink href={project.demoUrl} className="btn btn-primary">
                Open Demo →
              </ZoneLink>
            )}
            {project.repoUrl && (
              <Link
                href={project.repoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                View Source →
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}