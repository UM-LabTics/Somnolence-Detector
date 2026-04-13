"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useNow } from "@/hooks/use-now";

const NAV_ITEMS = [
  { href: "/", label: "Overview", code: "01" },
  { href: "/history", label: "Historial", code: "02" },
  { href: "/devices", label: "Flota", code: "03" },
];

export function Header() {
  const pathname = usePathname();
  const nowMs = useNow(1000);
  const now = nowMs ? new Date(nowMs) : null;

  const utc = now ? now.toISOString().slice(11, 19) : "--:--:--";
  const local = now
    ? now.toLocaleTimeString("es-UY", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      })
    : "--:--:--";

  return (
    <header className="relative z-10 border-b border-border bg-background/75 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-10 px-6">
        <div className="flex items-center gap-3">
          <div className="relative flex h-8 w-8 items-center justify-center">
            <div className="absolute inset-0 border border-primary/50" />
            <div className="absolute inset-[3px] border border-primary/20" />
            <div className="h-1.5 w-1.5 rounded-full bg-primary text-primary animate-pulse-dot" />
          </div>
          <div className="leading-none">
            <div className="mono-label text-[0.55rem]">Mission</div>
            <div className="font-heading text-xl tracking-tight text-foreground mt-0.5">
              Somnolence<span className="text-primary">.</span>
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, code }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "group relative flex items-baseline gap-2 px-3 py-2 transition-colors",
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <span className="mono-label text-[0.55rem] opacity-70">
                  {code}
                </span>
                <span className="text-sm">{label}</span>
                {active && (
                  <span className="absolute -bottom-px left-2 right-2 h-px bg-primary" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="flex-1" />

        <div className="flex items-center gap-6 font-mono text-xs tabular">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ok text-ok animate-pulse-dot" />
            <span className="mono-label text-[0.55rem]">Live</span>
          </div>
          <div className="hidden sm:flex flex-col items-end leading-tight">
            <span className="mono-label text-[0.55rem]">UTC</span>
            <span className="text-foreground">{utc}</span>
          </div>
          <div className="hidden md:flex flex-col items-end leading-tight">
            <span className="mono-label text-[0.55rem]">Local</span>
            <span className="text-foreground">{local}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
