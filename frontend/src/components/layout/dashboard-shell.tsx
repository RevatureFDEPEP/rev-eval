"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@workos-inc/authkit-nextjs/components";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { handleSignOut } from "@/app/(dashboard)/actions";
import { toast } from "sonner";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
} from "lucide-react";
import { cn } from "@/lib/utils";

const SIDEBAR_TRANSITION = "transition-all duration-300 ease-in-out";

type DashboardShellProps = {
  children: ReactNode;
};

type NavItem = {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
};

export function DashboardShell({ children }: DashboardShellProps) {
  const { user, loading } = useAuth({ ensureSignedIn: true });
  const pathname = usePathname();
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!user || typeof window === "undefined") return;

    const toastKey = `welcome-toast-${user.id ?? user.email}`;

    if (!sessionStorage.getItem(toastKey)) {
      const name = user.firstName
        ? `${user.firstName}${user.lastName ? ` ${user.lastName}` : ""}`
        : user.email;
      toast.success(`Welcome, ${name}!`, {
        description: "You're signed in to Revature EvaluAI",
      });
      sessionStorage.setItem(toastKey, "true");
    }
  }, [user]);

  const navBase = useMemo(() => {
    if (!pathname) return "/dashboard";
    if (pathname.startsWith("/trainer")) return "/trainer";
    if (pathname.startsWith("/participant")) return "/participant";
    return "/dashboard";
  }, [pathname]);

  const navItems: NavItem[] = useMemo(() => {
    const items: NavItem[] = [
      { label: "Dashboard", href: `${navBase}/dashboard`, icon: LayoutDashboard },
      { label: "Tests", href: `${navBase}/tests`, icon: ClipboardList },
    ];

    // Only show Questions for trainers
    if (navBase === "/trainer") {
      items.push({ label: "Questions", href: `${navBase}/questions`, icon: BookOpen });
    }

    return items;
  }, [navBase]);

  const activeHref = useMemo(() => {
    if (!pathname) return "";
    const matching = navItems.find((item) => pathname.startsWith(item.href));
    return matching?.href ?? "";
  }, [navItems, pathname]);

  // Check if user is taking a test (hide sidebar during tests)
  const isTakingTest = useMemo(() => {
    return pathname?.includes('/take/') ?? false;
  }, [pathname]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="size-12 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="text-sm text-slate-600">Loading your workspace…</p>
        </div>
      </div>
    );
  }

  const displayName = user.firstName
    ? `${user.firstName}${user.lastName ? ` ${user.lastName}` : ""}`
    : user.email;
  const initials = displayName
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const dicebearSeed = encodeURIComponent(displayName || user.email);

  const sidebarContent = (
    <div className={cn("flex h-full flex-col border-r bg-white/80 backdrop-blur-sm")}
    >
      <div className={cn("flex h-16 items-center px-4", sidebarExpanded ? "justify-between" : "justify-center")}>
        <Link href="/dashboard" className="flex items-center gap-3 text-slate-900">
          <div className="flex size-9 items-center justify-center rounded-full bg-slate-900 text-white">
            <span className="text-lg font-semibold">R</span>
          </div>
          {sidebarExpanded && (
            <div className="leading-tight">
              <p className="text-sm font-semibold">Revature</p>
              <p className="text-xs text-slate-500">EvaluAI</p>
            </div>
          )}
        </Link>
        {sidebarExpanded && (
          <Button
            size="icon"
            variant="ghost"
            className="hidden shrink-0 rounded-full md:inline-flex"
            onClick={() => setSidebarExpanded((prev) => !prev)}
          >
            <ChevronLeft className="size-4" />
            <span className="sr-only">Toggle sidebar</span>
          </Button>
        )}
      </div>
      {!sidebarExpanded && (
        <div className="flex justify-center border-b pb-3">
          <Button
            size="icon"
            variant="ghost"
            className="hidden shrink-0 rounded-full md:inline-flex"
            onClick={() => setSidebarExpanded((prev) => !prev)}
          >
            <ChevronRight className="size-4" />
            <span className="sr-only">Toggle sidebar</span>
          </Button>
        </div>
      )}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              SIDEBAR_TRANSITION,
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-all duration-200 hover:-translate-y-0.5 hover:bg-gradient-to-r hover:from-orange-100/80 hover:to-purple-100/80 hover:text-slate-900",
              activeHref === href && "bg-slate-900 text-white hover:bg-slate-900 hover:text-white",
              sidebarExpanded ? "justify-start" : "justify-center",
            )}
            onClick={() => setMobileOpen(false)}
          >
            <Icon className="size-5" />
            {sidebarExpanded && <span>{label}</span>}
          </Link>
        ))}
      </nav>
      <div className="border-t px-4 py-4 text-xs text-slate-400">
        Revature EvaluAI © {new Date().getFullYear()}
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-orange-50/60 via-white to-purple-50/60">
      {!isTakingTest && (
        <aside
          className={cn(
            SIDEBAR_TRANSITION,
            "hidden md:block",
            sidebarExpanded ? "w-64" : "w-20",
          )}
        >
          {sidebarContent}
        </aside>
      )}

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/70 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-4 sm:px-6">
            <div className="flex items-center gap-3">
              {!isTakingTest && (
                <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                  <SheetTrigger asChild>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="inline-flex items-center justify-center rounded-full md:hidden"
                      aria-label="Open navigation"
                    >
                      <Menu className="size-5" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left" className="w-64 p-0">
                    <SheetHeader className="px-4 py-3 text-left">
                      <SheetTitle>Navigation</SheetTitle>
                    </SheetHeader>
                    <div className="h-full overflow-y-auto">{sidebarContent}</div>
                  </SheetContent>
                </Sheet>
              )}
              <Link href="/dashboard" className="text-base font-semibold text-slate-900 md:hidden">
                Revature EvaluAI
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="flex items-center gap-3 rounded-full border border-slate-200 bg-white px-2 py-1 text-left shadow-sm transition duration-200 hover:border-orange-200 hover:shadow-md"
                  >
                    <Avatar className="size-9">
                      <AvatarImage
                        src={`https://api.dicebear.com/9.x/neutral/svg?seed=${dicebearSeed}`}
                        alt={displayName}
                      />
                      <AvatarFallback>{initials}</AvatarFallback>
                    </Avatar>
                    <div className="hidden text-left text-sm leading-tight sm:block">
                      <p className="font-semibold text-slate-900">{displayName}</p>
                      <p className="text-xs text-slate-500">{user.email}</p>
                    </div>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <DropdownMenuLabel className="text-xs uppercase text-slate-500">
                    Signed in as
                  </DropdownMenuLabel>
                  <div className="px-3 py-2 text-sm">
                    <p className="font-medium text-slate-900">{displayName}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Mail className="size-3" />
                      <span>{user.email}</span>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <form action={handleSignOut}>
                    <DropdownMenuItem asChild>
                      <button
                        type="submit"
                        className="flex w-full items-center gap-2 text-sm text-red-600 focus:outline-none"
                      >
                        <LogOut className="size-4" />
                        Sign out
                      </button>
                    </DropdownMenuItem>
                  </form>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        <main className="flex-1 px-3 py-6 sm:px-5">
          <div className="mx-auto w-full max-w-7xl space-y-6">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default DashboardShell;
