import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = {
  width: 64,
  height: 64,
};
export const contentType = "image/png";

/**
 * Generates the application favicon without relying on binary blobs in git history.
 * The stylised "C" references the charting assistant while keeping the palette
 * close to the dashboard theme used across the chatbot interface.
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "linear-gradient(135deg, #040b2e 0%, #0f1f64 100%)",
          borderRadius: "50%",
          color: "#f5f8ff",
          display: "flex",
          fontSize: 32,
          fontWeight: 700,
          height: "100%",
          justifyContent: "center",
          width: "100%",
        }}
      >
        C
      </div>
    ),
    size,
  );
}
