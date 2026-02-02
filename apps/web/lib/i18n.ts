export type Locale = "en" | "fr";

export const dictionaries = {
  en: {
    nav: {
      work: "Projects",
      about: "Experience",
      wins: "Wins",
      ask: "Ask",
      demos: "Demos",
      status: "Status",
      cv: "Download CV",
    },
    hero: {
      seeking: "Open to roles · US & Europe · Immediate start",
      ctaWork: "View projects",
      ctaCv: "Download CV",
      ctaContact: "Contact",
    },
    projects: {
      title: "Projects",
      subtitle: "Live demos and planned builds — open a demo or dig into the source.",
      planned: "Coming soon",
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
      status: "Statut",
      cv: "Télécharger le CV",
    },
    hero: {
      seeking: "Ouverte aux opportunités · US & Europe · Disponible immédiatement",
      ctaWork: "Voir les projets",
      ctaCv: "Télécharger le CV",
      ctaContact: "Contact",
    },
    projects: {
      title: "Projets",
      subtitle: "Démos live et builds prévus — ouvrir une démo ou le code source.",
      planned: "Bientôt",
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
