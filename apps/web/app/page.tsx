import { Hero } from "@/components/hero";
import { ProjectGrid } from "@/components/project-grid";
import { Wins } from "@/components/wins";
import { About } from "@/components/about";

export default function HomePage() {
  return (
    <>
      <Hero />
      <ProjectGrid />
      <Wins />
      <About />
    </>
  );
}
