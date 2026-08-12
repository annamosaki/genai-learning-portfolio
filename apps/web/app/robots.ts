import type { MetadataRoute } from "next";
import { cv } from "@content/cv";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${cv.links.site}/sitemap.xml`,
    host: cv.links.site,
  };
}
