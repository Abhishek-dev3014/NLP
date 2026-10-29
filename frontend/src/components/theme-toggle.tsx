"use client";
import { Moon, Sun } from "lucide-react";
export function ThemeToggle() {
  return (
    <button
      className="icon-button theme-toggle"
      aria-label="Toggle light and dark theme"
      onClick={() => {
        const next =
          document.documentElement.dataset.theme === "light" ? "dark" : "light";
        document.documentElement.dataset.theme = next;
        try {
          localStorage.setItem("verifact-theme", next);
        } catch {}
      }}
    >
      <Sun size={18} className="sun-icon" />
      <Moon size={18} className="moon-icon" />
    </button>
  );
}
