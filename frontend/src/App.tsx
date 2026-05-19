import { Switch, Route, Router as WouterRouter, useLocation } from "wouter";
import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/hooks/use-auth";
import { AppLayout } from "@/components/layout/AppLayout";
import { Loader2 } from "lucide-react";

// Pages
import Login from "@/pages/login";
import Register from "@/pages/register";
import Home from "@/pages/home";
import Dashboard from "@/pages/dashboard";
import Purchase from "@/pages/purchase";
import Withdraw from "@/pages/withdraw";
import Transactions from "@/pages/transactions";
import Sponsor from "@/pages/sponsor";
import Profile from "@/pages/profile";
import Settings from "@/pages/settings";

import NotFound from "@/pages/not-found";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function ProtectedRoute({ component: Component, requireAdmin }: { component: any, requireAdmin?: boolean }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [, setLocation] = useLocation();
  const isAdminUser = !!(user as any)?.is_admin || !!(user as any)?.is_staff || !!(user as any)?.is_superuser;

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      setLocation("/login");
    }
    if (!isLoading && isAuthenticated && requireAdmin && !isAdminUser) {
      setLocation("/");
    }
  }, [isLoading, isAuthenticated, requireAdmin, isAdminUser, setLocation]);

  if (isLoading) {
    return (
      <div className="flex h-dvh w-full items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requireAdmin && !isAdminUser) {
    return null;
  }

  return (
    <AppLayout>
      <Component />
    </AppLayout>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/login" component={Login} />
      <Route path="/register" component={Register} />

      {/* Protected User Routes */}
      <Route path="/purchase">
        <ProtectedRoute component={Purchase} />
      </Route>
      <Route path="/user/home/">
        <ProtectedRoute component={Dashboard} />
      </Route>
      <Route path="/user/home">
        <ProtectedRoute component={Dashboard} />
      </Route>
      <Route path="/user/dashboard/">
        <ProtectedRoute component={Dashboard} />
      </Route>
      <Route path="/user/dashboard">
        <ProtectedRoute component={Dashboard} />
      </Route>
      <Route path="/user/dashbord/">
        <ProtectedRoute component={Dashboard} />
      </Route>
      <Route path="/user/dashbord">
        <ProtectedRoute component={Dashboard} />
      </Route>
      <Route path="/withdraw">
        <ProtectedRoute component={Withdraw} />
      </Route>
      <Route path="/transactions">
        <ProtectedRoute component={Transactions} />
      </Route>
      <Route path="/sponsor">
        <ProtectedRoute component={Sponsor} />
      </Route>
      <Route path="/profile">
        <ProtectedRoute component={Profile} />
      </Route>
      <Route path="/settings">
        <ProtectedRoute component={Settings} />
      </Route>

      {/* Catch all */}
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AuthProvider>
          <WouterRouter base="">
            <Switch>
              <Route path="/">
                <ProtectedRoute component={Home} />
              </Route>
              <Router />
            </Switch>
          </WouterRouter>
          <Toaster />
        </AuthProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;