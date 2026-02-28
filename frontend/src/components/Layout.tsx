import { Link, useLocation, Outlet } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";

export function Layout() {
  const { pathname } = useLocation();
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("theme");
      if (stored) return stored === "dark";
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.style.colorScheme = "dark";
      localStorage.setItem("theme", "dark");
    } else {
      root.style.colorScheme = "light";
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

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
            onClick={() => setIsDark(!isDark)}
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
