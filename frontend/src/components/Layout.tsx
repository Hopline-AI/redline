import { Link, useLocation, Outlet } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";

export function Layout() {
  const { pathname } = useLocation();
  const { isDark, toggleTheme } = useTheme();

  return (
    <>
      <header className="app-header">
        <Link to="/" className="logo">
          Red<span>line</span>
        </Link>
        <nav>
          <Link to="/" aria-current={pathname === "/" ? "page" : undefined}>
            Upload
          </Link>
          <Link
            to="/review/pol_demo_001"
            aria-current={pathname.startsWith("/review") ? "page" : undefined}
          >
            Review
          </Link>
          <Link
            to="/report/pol_demo_001"
            aria-current={pathname.startsWith("/report") ? "page" : undefined}
          >
            Report
          </Link>
          <button
            className="ghost icon small"
            onClick={toggleTheme}
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </>
  );
}
