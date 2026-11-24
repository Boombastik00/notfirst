import type { Metadata } from "next";
import type { ReactNode } from "react";

import SiteFooter from "@/components/SiteFooter";
import "./base.css";

export const metadata: Metadata = {
  title: "не первая",
  description: "истории женщин с которыми можно себя соотнести",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
