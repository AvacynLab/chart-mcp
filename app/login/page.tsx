"use client";

import { FormEvent, useState } from "react";

/**
 * Minimal login page used exclusively by the test suite to bootstrap a regular
 * session. The real product would delegate to a full authentication provider,
 * however the deterministic E2E flow only requires a predictable cookie to be
 * set before redirecting the user to `/chat`.
 */
export default function LoginPage(): JSX.Element {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    const formData = new FormData(event.currentTarget);
    const email = (formData.get("email") ?? "").toString().trim();
    const password = (formData.get("password") ?? "").toString();

    if (!email || !password) {
      setError("Identifiants requis pour continuer");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    /** Persist a short-lived cookie consumed by `getServerSession`. */
    const cookieOptions = "path=/; max-age=86400";
    document.cookie = `sessionType=regular; ${cookieOptions}`;
    document.cookie = `sessionName=${encodeURIComponent(email)}; ${cookieOptions}`;

    /** Redirect to the chat route which is protected by the regular-only guard. */
    window.location.assign("/chat");
  };

  return (
    <main className="login" data-testid="auth-root">
      <h1>Connexion</h1>
      <p className="login__subtitle">Accède au chat en utilisant un compte régulier.</p>
      <form className="login__form" onSubmit={handleSubmit} noValidate>
        <label htmlFor="auth-email">Adresse e-mail</label>
        <input
          id="auth-email"
          name="email"
          type="email"
          autoComplete="email"
          required
          data-testid="auth-email"
          placeholder="utilisateur@example.com"
          disabled={isSubmitting}
        />
        <label htmlFor="auth-password">Mot de passe</label>
        <input
          id="auth-password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          data-testid="auth-password"
          placeholder="********"
          disabled={isSubmitting}
        />
        {error ? (
          <p role="alert" data-testid="auth-error" className="login__error">
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={isSubmitting} data-testid="auth-submit">
          {isSubmitting ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </main>
  );
}
