import type { NextConfig } from "next";

// Default to offline-friendly font compilation so builds succeed when
// the CI runner cannot reach Google Fonts. Developers can override this by
// exporting NEXT_DISABLE_FONT_DOWNLOAD=0 before invoking `pnpm build`.
if (!process.env.NEXT_DISABLE_FONT_DOWNLOAD) {
  process.env.NEXT_DISABLE_FONT_DOWNLOAD = "1";
}

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        hostname: "avatar.vercel.sh",
      },
    ],
  },
};

export default nextConfig;
