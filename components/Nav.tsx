import Link from "next/link";

const ITEMS = [
  { href: "/", label: "MOM10 · 10-stock" },
  { href: "/mom20", label: "MOM20 · 20-stock" },
  { href: "/star-rsi-sharpe", label: "STAR RSI SHARPE" },
  { href: "/rishi-viraj", label: "RISHI x VIRAJ" },
];

export default function Nav({ current }: { current: string }) {
  return (
    <nav className="mb-8 inline-flex flex-wrap gap-1 rounded-xl border border-zinc-200 bg-white/80 p-1 shadow-sm backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
      {ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={
            "rounded-lg px-3.5 py-2 text-sm font-medium transition " +
            (item.href === current
              ? "bg-zinc-900 text-white shadow-sm dark:bg-zinc-100 dark:text-zinc-900"
              : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50")
          }
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
