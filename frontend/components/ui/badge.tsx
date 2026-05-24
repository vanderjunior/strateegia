import type { HTMLAttributes, PropsWithChildren } from "react";

export function Badge({
  children,
  className = "",
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLSpanElement>>) {
  return (
    <span
      className={`inline-flex items-center rounded-full border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.12)] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.24em] text-gold2 ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
