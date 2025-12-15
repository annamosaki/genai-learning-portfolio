import { ImageResponse } from "next/og";
import { cv } from "@content/cv";

export const runtime = "edge";
export const alt = "Anna Mosaki — Portfolio";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#05070b",
          color: "#e8eef7",
          padding: 64,
        }}
      >
        <div style={{ display: "flex", color: "#3dffb5", fontSize: 22, letterSpacing: 4 }}>
          PORTFOLIO
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 84, lineHeight: 1.05, fontWeight: 700 }}>{cv.name}</div>
          <div style={{ marginTop: 16, fontSize: 28, color: "#4cc9ff" }}>{cv.title}</div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 20, color: "#8b9bb4" }}>
          <span>Quant · AI · Markets</span>
          <span style={{ color: "#3dffb5" }}>annamosaki.com</span>
        </div>
      </div>
    ),
    { ...size },
  );
}
