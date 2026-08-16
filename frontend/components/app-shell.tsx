"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Building2,
  CalendarDays,
  FileText,
  FolderKanban,
  LayoutDashboard,
  Megaphone,
  Palette,
  Scissors,
  Settings
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { label: "Clients & Projects", icon: Building2, href: "/clients" },
  { label: "Generator", icon: FileText, href: "/" },
  { label: "Brand Profile", icon: Palette, href: "/brand-profile" },
  { label: "Knowledge Base", icon: BookOpen, href: "/knowledge-base" },
  { label: "Campaign Generator", icon: Megaphone, href: "/campaigns" },
  { label: "Repurposer", icon: Scissors, href: "/repurpose" },
  { label: "Calendar", icon: CalendarDays, href: "/calendar" },
  { label: "Assets Library", icon: FolderKanban, href: "/assets" },
  { label: "Settings", icon: Settings, href: "/settings" }
] satisfies Array<{ label: string; icon: React.ComponentType<{ className?: string }>; href: Route }>;

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { workspace, updateWorkspace } = useWorkspace();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(232,78,15,0.08),transparent_28rem),linear-gradient(180deg,#fffdfb_0%,#f7f3ef_100%)]">
      <div className="grid min-h-screen lg:grid-cols-[292px_1fr]">
        <aside className="hidden border-r bg-neutral-950 text-white lg:block">
          <div className="flex h-full flex-col">
            <div className="flex items-center gap-3 px-5 py-5">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-white">
                <span className="text-lg font-bold tracking-tight text-neutral-950">AC</span>
              </div>
              <div>
                <div className="font-semibold leading-tight">AI Content Studio</div>
                <div className="text-xs text-white/55">Multi-tenant content workspace</div>
              </div>
            </div>
            <Separator className="bg-white/10" />
            <nav className="space-y-1 px-3 py-4">
              {navItems.map((item) => {
                const active = isActive(pathname, item.href);
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-white text-neutral-950 font-semibold"
                        : "text-white/68 hover:bg-white/10 hover:text-white"
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="mt-auto space-y-3 p-4">
              <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase text-white/45">Workspace</span>
                  <Badge variant="secondary" className="border-white/10 bg-white/10 text-white">
                    Project scoped
                  </Badge>
                </div>
                <p className="truncate text-sm font-medium">{workspace.clientName}</p>
                <p className="truncate text-xs text-white/55">{workspace.projectName}</p>
              </div>
            </div>
          </div>
        </aside>
        <main className="min-w-0">
          <header className="sticky top-0 z-20 border-b bg-background/90 px-4 py-3 backdrop-blur md:px-6">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">Marketing Content Operations</p>
                <h1 className="text-xl font-semibold tracking-tight md:text-2xl">AI Marketing Workspace</h1>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 xl:w-[560px]">
                <div className="space-y-1">
                  <Label className="text-xs">Client</Label>
                  <Input value={workspace.clientName} onChange={(event) => updateWorkspace("clientName", event.target.value)} />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Project</Label>
                  <Input value={workspace.projectName} onChange={(event) => updateWorkspace("projectName", event.target.value)} />
                </div>
              </div>
            </div>
          </header>
          <div className="p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
