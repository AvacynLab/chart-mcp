import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = {
  width: 1200,
  height: 675,
};
export const contentType = "image/png";

const TITLE = "Chart MCP Copilot";
const FOOTER = "Flux SSE + recherche SearxNG";

/**
 * Generates the summary image used by the Twitter card without committing binary
 * assets. The composition mirrors the Open Graph variant while adapting the
 * vertical spacing to fit Twitter's 16:9 layout guidelines.
 */
export default function TwitterImage() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "linear-gradient(130deg, #06133d 0%, #030712 100%)",
          color: "#f8fafc",
          display: "flex",
          flexDirection: "column",
          fontFamily: "Inter, Arial, sans-serif",
          height: "100%",
          justifyContent: "center",
          padding: "60px 72px",
          width: "100%",
        }}
      >
        <div style={{ fontSize: 70, fontWeight: 700 }}>Finance × Search</div>
        <div
          style={{
            fontSize: 34,
            fontWeight: 500,
            marginTop: 28,
            textAlign: "center",
          }}
        >
          {TITLE}
        </div>
        <div
          style={{
            background: "rgba(59, 130, 246, 0.25)",
            border: "1px solid rgba(96, 165, 250, 0.55)",
            borderRadius: 20,
            fontSize: 28,
            fontWeight: 600,
            marginTop: 36,
            padding: "18px 32px",
          }}
        >
          {FOOTER}
        </div>
      </div>
    ),
    size,
  );
}
