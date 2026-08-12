import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

/** Browser tab favicon (also used by Google when it crawls the site). */
export default function Icon() {
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
          borderRadius: 8,
        }}
      >
        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: "#3dffb5",
            letterSpacing: -1,
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
