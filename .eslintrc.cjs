/**
 * ESLint configuration aligned with Next.js defaults. The file lives at the
 * repository root so `pnpm lint` (alias de `next lint`) fonctionne aussi bien
 * en local qu'en CI sans inviter Next.js à générer un template interactif.
 */
module.exports = {
  root: true,
  extends: ["next/core-web-vitals"],
};
