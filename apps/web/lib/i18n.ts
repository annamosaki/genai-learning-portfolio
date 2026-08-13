export type Locale = "en" | "fr";

export const dictionaries = {
  en: {
    nav: {
      work: "Projects",
      about: "Experience",
      wins: "Wins",
      ask: "Ask",
      demos: "Demos",
    },
    hero: {
      seeking: "Open to roles · London · Based in Lisbon · Immediate start",
      ctaWork: "View projects",
      ctaContact: "Contact",
    },
    projects: {
      title: "Projects",
      subtitle: "Live demos — open one or dig into the source.",
      live: "Live",
      openDemo: "Open demo",
      source: "Source",
    },
    wins: { title: "Highlights" },
    about: { title: "Experience", education: "Education", languages: "Languages", stack: "Stack" },
    footer: { built: "Anna Mosaki · Quant · AI" },
  },
  fr: {
    nav: {
      work: "Projets",
      about: "Expérience",
      wins: "Palmarès",
      ask: "Ask",
      demos: "Démos",
    },
    hero: {
      seeking: "Ouverte aux opportunités · Londres · Basée à Lisbonne · Disponible immédiatement",
      ctaWork: "Voir les projets",
      ctaContact: "Contact",
    },
    projects: {
      title: "Projets",
      subtitle: "Démos live — ouvrir une démo ou le code source.",
      live: "Live",
      openDemo: "Ouvrir la démo",
      source: "Source",
    },
    wins: { title: "Palmarès" },
    about: { title: "Expérience", education: "Formation", languages: "Langues", stack: "Stack" },
    footer: { built: "Anna Mosaki · Quant · AI" },
  },
} as const;

export function t(locale: Locale) {
  return dictionaries[locale] ?? dictionaries.en;
}
