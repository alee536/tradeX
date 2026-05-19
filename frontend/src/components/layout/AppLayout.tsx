import { ReactNode, useState } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import {
  Settings,
  LogOut,
  ShieldAlert,
  Home,
  LayoutDashboard,
  ShoppingCart,
  ArrowDownToLine,
  History,
  Users,
  UserCircle,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SocialLinks } from "@/components/ui/social-links";
import { Logo } from "../ui/logo";

interface SidebarItem {
  icon: React.ElementType;
  label: string;
  href: string;
  adminOnly?: boolean;
}

const items: SidebarItem[] = [
  { icon: Home, label: "Home", href: "/" },
  { icon: LayoutDashboard, label: "Dashboard", href: "/user/dashboard" },
  { icon: ShoppingCart, label: "Purchase", href: "/purchase" },
  { icon: ArrowDownToLine, label: "Withdraw", href: "/withdraw" },
  { icon: History, label: "Transactions", href: "/transactions" },
  { icon: Users, label: "Sponsor", href: "/sponsor" },
  { icon: UserCircle, label: "Profile", href: "/profile" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

const adminItems: SidebarItem[] = [
  { icon: ShieldAlert, label: "Admin Dashboard", href: "/admin", adminOnly: true },
  { icon: Users, label: "Users", href: "/admin/users", adminOnly: true },
  { icon: ShoppingCart, label: "Purchases", href: "/admin/purchases", adminOnly: true },
  { icon: ArrowDownToLine, label: "Withdrawals", href: "/admin/withdrawals", adminOnly: true },
  { icon: Settings, label: "System Settings", href: "/admin/settings", adminOnly: true },
  { icon: Users, label: "Sponsor Relations", href: "/admin/sponsor", adminOnly: true },
];

export function Sidebar({ className, onItemClick }: { className?: string; onItemClick?: () => void }) {
  const [location] = useLocation();
  const { user, logout } = useAuth();

  const allItems = user?.is_admin ? [...items, ...adminItems] : items;

  return (
    <aside
      className={cn("w-64 shrink-0 flex flex-col h-full", className)}
      style={{
        background: "linear-gradient(180deg, #060c18 0%, #070e1c 100%)",
        borderRight: "1px solid rgba(59,130,246,0.1)",
      }}
    >
      <div className="flex flex-col gap-3 px-4 py-4" style={{ borderBottom: "1px solid rgba(59,130,246,0.1)" }}>
        <div className="flex items-center justify-between gap-3">
          <Logo size="md" />
          {onItemClick && (
            <button
              onClick={onItemClick}
              className="lg:hidden text-gray-400 hover:text-white p-1 rounded hover:bg-white/5 cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        {allItems.map((item) => (
          <Link key={item.href} href={item.href}>
            <div
              onClick={onItemClick}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition-colors duration-200 cursor-pointer",
                location === item.href
                  ? "bg-white/10 text-white"
                  : "text-gray-200 hover:bg-white/10"
              )}
            >
              <item.icon className="h-4 w-4 text-blue-400 shrink-0" />
              <span>{item.label}</span>
            </div>
          </Link>
        ))}
      </nav>

      <div className="border-t border-white/10 p-4">
        {user && (
          <div className="flex items-center gap-3 px-3 py-2 mb-3 rounded-lg bg-white/5">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 bg-blue-500/20 text-blue-300">
              {user.username?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="min-w-0">
              <p className="text-sm text-white font-medium truncate">{user.username}</p>
              <p className="text-xs text-gray-500 truncate">{user.is_admin ? "Administrator" : "Trader"}</p>
            </div>
          </div>
        )}
        <button
          onClick={() => {
            if (onItemClick) onItemClick();
            logout();
          }}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-sm text-gray-300 hover:text-red-300 hover:bg-red-500/10 cursor-pointer"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}

export function AppLayout({ children }: { children: ReactNode }) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="flex h-dvh w-full overflow-hidden" style={{ background: "#070d1a" }}>
      {/* Desktop Sidebar */}
      <Sidebar className="hidden lg:flex sticky top-0 h-dvh" />

      {/* Mobile Sidebar Overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
            onClick={() => setIsMobileOpen(false)}
          />
          {/* Drawer content */}
          <div className="relative flex-1 max-w-xs w-full bg-[#070e1c] flex flex-col z-10 animate-in slide-in-from-left duration-200">
            <Sidebar className="w-full h-full" onItemClick={() => setIsMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Mobile Header */}
        <header
          className="flex lg:hidden items-center justify-between px-4 py-3 shrink-0"
          style={{
            background: "#060c18",
            borderBottom: "1px solid rgba(59,130,246,0.1)",
          }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileOpen(true)}
              className="text-gray-200 hover:text-white p-1 rounded hover:bg-white/5 cursor-pointer"
            >
              <Menu className="h-6 w-6" />
            </button>
            <Logo size="sm" />
          </div>
          {user && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold bg-blue-500/20 text-blue-300">
                {user.username?.[0]?.toUpperCase() ?? "U"}
              </div>
            </div>
          )}
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 relative z-10">
          <div className="max-w-7xl mx-auto h-full">
            {children}
          </div>
        </main>

        {/* Global footer with social links */}
        <footer className="shrink-0 p-4 border-t border-white/5 bg-transparent">
          <div className="max-w-7xl mx-auto flex items-center justify-between text-sm text-gray-400">
            <span>© {new Date().getFullYear()} 24TRADEX</span>
            <div className="flex items-center gap-4">
              <SocialLinks />
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
