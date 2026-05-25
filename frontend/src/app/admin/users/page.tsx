"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { createUser, listUsers } from "@/lib/api";
import type { UserCreatePayload, UserResponse, UserRole } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const ROLES: UserRole[] = ["OPERATOR", "ADMIN"];

export default function AdminUsersPage() {
  const router = useRouter();
  const { user, status } = useAuth();

  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [form, setForm] = useState<UserCreatePayload>({
    email: "",
    password: "",
    full_name: "",
    role: "OPERATOR",
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setListError(null);
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Error cargando usuarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === "loading") return;
    if (status === "anonymous") {
      router.replace("/login");
      return;
    }
    if (user && user.role !== "ADMIN") {
      router.replace("/");
      return;
    }
    fetchUsers();
  }, [status, user, router, fetchUsers]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const created = await createUser(form);
      setSuccess(`Usuario ${created.email} creado.`);
      setForm({ email: "", password: "", full_name: "", role: "OPERATOR" });
      fetchUsers();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error creando usuario");
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "loading" || (user && user.role !== "ADMIN")) {
    return (
      <div className="mx-auto max-w-7xl p-4">
        <p className="text-muted-foreground py-8 text-center">Cargando...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4">
      <div>
        <div className="mono-label text-[0.55rem] text-primary">// admin</div>
        <h2 className="font-heading text-2xl tracking-tight">
          Gestión de usuarios
        </h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Crear usuario</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="full_name" className="mono-label text-[0.55rem]">
                  Nombre completo
                </label>
                <Input
                  id="full_name"
                  required
                  value={form.full_name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, full_name: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="email" className="mono-label text-[0.55rem]">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, email: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="password" className="mono-label text-[0.55rem]">
                  Contraseña (mín. 6)
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={6}
                    value={form.password}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, password: e.target.value }))
                    }
                    className="pr-9"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={
                      showPassword
                        ? "Ocultar contraseña"
                        : "Mostrar contraseña"
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
              <div className="space-y-1.5">
                <label htmlFor="role" className="mono-label text-[0.55rem]">
                  Rol
                </label>
                <select
                  id="role"
                  value={form.role}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, role: e.target.value as UserRole }))
                  }
                  className="border-input bg-transparent dark:bg-input/30 focus-visible:border-ring focus-visible:ring-ring/50 h-8 w-full rounded-lg border px-2.5 text-sm outline-none focus-visible:ring-3"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              {formError && (
                <div className="border-destructive/40 bg-destructive/10 text-destructive rounded-md border px-3 py-2 text-sm">
                  {formError}
                </div>
              )}
              {success && (
                <div className="border-primary/40 bg-primary/10 text-primary rounded-md border px-3 py-2 text-sm">
                  {success}
                </div>
              )}

              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Creando..." : "Crear usuario"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Usuarios registrados</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-muted-foreground py-6 text-center text-sm">
                Cargando...
              </p>
            ) : listError ? (
              <p className="text-destructive py-6 text-center text-sm">
                {listError}
              </p>
            ) : users.length === 0 ? (
              <p className="text-muted-foreground py-6 text-center text-sm">
                Sin usuarios.
              </p>
            ) : (
              <ul className="divide-border divide-y">
                {users.map((u) => (
                  <li
                    key={u.id}
                    className="flex items-center justify-between py-3"
                  >
                    <div>
                      <div className="text-sm font-medium">{u.full_name}</div>
                      <div className="text-muted-foreground font-mono text-xs">
                        {u.email}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!u.is_active && (
                        <Badge variant="secondary">inactivo</Badge>
                      )}
                      <Badge
                        variant={u.role === "ADMIN" ? "default" : "secondary"}
                      >
                        {u.role}
                      </Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
