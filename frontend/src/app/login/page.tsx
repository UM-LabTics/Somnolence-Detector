"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login fallido");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 space-y-2">
          <div className="mono-label text-[0.55rem] text-primary">// access</div>
          <h1 className="font-heading text-3xl tracking-tight">
            Identifícate<span className="text-primary">.</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Acceso al sistema de monitoreo de somnolencia.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="email" className="mono-label text-[0.55rem]">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@somnolence.com"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="password" className="mono-label text-[0.55rem]">
              Contraseña
            </label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="pr-9"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
                className="text-muted-foreground hover:text-foreground absolute inset-y-0 right-0 flex items-center px-2.5 transition-colors"
              >
                {showPassword ? (
                  <EyeOff className="size-4" />
                ) : (
                  <Eye className="size-4" />
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <Button
            type="submit"
            disabled={submitting}
            className="w-full"
            size="lg"
          >
            {submitting ? "Verificando..." : "Iniciar sesión"}
          </Button>
        </form>
      </div>
    </div>
  );
}
