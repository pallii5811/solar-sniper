import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(0 0% 6%)",
        foreground: "hsl(0 0% 98%)",
        card: "hsl(0 0% 9%)",
        "card-foreground": "hsl(0 0% 98%)",
        popover: "hsl(0 0% 9%)",
        "popover-foreground": "hsl(0 0% 98%)",
        muted: "hsl(0 0% 14%)",
        "muted-foreground": "hsl(0 0% 68%)",
        border: "hsl(0 0% 16%)",
        input: "hsl(0 0% 16%)",
        primary: "#00E676",
        "primary-foreground": "hsl(0 0% 9%)",
        destructive: "hsl(0 84% 60%)",
        "destructive-foreground": "hsl(0 0% 98%)"
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.6rem",
        sm: "0.45rem"
      }
    }
  },
  plugins: []
};

export default config;
