import { createRoot } from "react-dom/client";
import { setAuthTokenGetter } from "@workspace/api-client-react";
import { getStoredAuthToken } from "@/lib/auth-session";
import App from "./App";
import "./index.css";

// Generated API paths already include /api (e.g. /api/auth/login).
// Do NOT call setBaseUrl("/api") or URLs become /api/api/...
setAuthTokenGetter(() => getStoredAuthToken());

createRoot(document.getElementById("root")!).render(<App />);
