import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

/** Apple touch / high-res icon (helps Google pick a crisp favicon). */
export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#05070b",
          borderRadius: 36,
        }}
      >
        <div
          style={{
            fontSize: 84,
            fontWeight: 700,
            color: "#3dffb5",
            letterSpacing: -4,
            fontFamily: "system-ui, sans-serif",
          }}
        >
          AM
        </div>
      </div>
    ),
    { ...size },
  );
}
