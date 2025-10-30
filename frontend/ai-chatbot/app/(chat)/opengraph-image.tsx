import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

const TITLE = "Chart MCP Copilot";
const SUBTITLE = "Analyse de marché assistée par artefacts finance & recherche";

/**
 * Dynamically renders the Open Graph preview banner so that we do not need to
 * commit raster assets. The layout mirrors the tones used in the application
 * sidebar and highlights the dual artefact capabilities of the assistant.
 */
export default function OpengraphImage() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "stretch",
        background: "radial-gradient(circle at 20% 20%, #13286b, #020617)",
        color: "#f8fbff",
        display: "flex",
        flexDirection: "column",
        fontFamily: "Inter, Arial, sans-serif",
        height: "100%",
        justifyContent: "space-between",
        padding: "64px 72px",
        width: "100%",
      }}
    >
      <div style={{ fontSize: 64, fontWeight: 700 }}>{TITLE}</div>
      <div
        style={{
          display: "flex",
          gap: 32,
          marginTop: 32,
        }}
      >
        <span
          style={{
            background: "rgba(15, 118, 110, 0.4)",
            border: "1px solid rgba(45, 212, 191, 0.6)",
            borderRadius: 16,
            fontSize: 32,
            fontWeight: 600,
            padding: "18px 28px",
          }}
        >
          Finance
        </span>
        <span
          style={{
            background: "rgba(59, 130, 246, 0.35)",
            border: "1px solid rgba(147, 197, 253, 0.6)",
            borderRadius: 16,
            fontSize: 32,
            fontWeight: 600,
            padding: "18px 28px",
          }}
        >
          Recherche
        </span>
      </div>
      <div
        style={{
          color: "rgba(226, 232, 240, 0.92)",
          fontSize: 36,
          fontWeight: 500,
          lineHeight: 1.25,
          marginTop: 48,
          maxWidth: "80%",
        }}
      >
        {SUBTITLE}
      </div>
    </div>,
    size
  );
}
