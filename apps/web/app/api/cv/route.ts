import { cv } from "@content/cv";

export const runtime = "nodejs";

function escapePdfText(s: string) {
  return s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

/** Minimal single-page PDF generated from the same cv.ts source of truth. */
function buildPdf() {
  const lines = [
    cv.name,
    cv.title,
    `${cv.email} | ${cv.phone} | ${cv.location}`,
    "",
    cv.seeking,
    "",
    "EXPERIENCE",
    ...cv.experience.flatMap((e) => [
      `${e.company} — ${e.role}`,
      `${e.start} – ${e.end} | ${e.location}`,
      ...e.bullets.map((b) => `• ${b}`),
      "",
    ]),
    "EDUCATION",
    ...cv.education.map((e) => `${e.school} — ${e.degree} (${e.years})`),
    "",
    "PROJECTS",
    ...cv.projects.map((p) => `${p.number} ${p.title}: ${p.tagline}`),
    "",
    "WINS",
    ...cv.wins.map((w) => `${w.title} — ${w.org}`),
  ];

  const contentLines = lines.map((l, i) => {
    const y = 800 - i * 12;
    return `BT /F1 9 Tf 40 ${y} Td (${escapePdfText(l).slice(0, 110)}) Tj ET`;
  });
  const stream = contentLines.join("\n");

  const objects = [
    "1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
    "2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
    "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n",
    `4 0 obj<< /Length ${stream.length} >>stream\n${stream}\nendstream\nendobj\n`,
    "5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
  ];

  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (const obj of objects) {
    offsets.push(Buffer.byteLength(pdf, "utf8"));
    pdf += obj;
  }
  const xrefPos = Buffer.byteLength(pdf, "utf8");
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  for (let i = 1; i <= objects.length; i++) {
    pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefPos}\n%%EOF`;
  return Buffer.from(pdf, "utf8");
}

export async function GET() {
  const pdf = buildPdf();
  return new Response(new Uint8Array(pdf), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'attachment; filename="Anna_Mosaki_CV.pdf"',
      "Cache-Control": "public, max-age=3600",
    },
  });
}
