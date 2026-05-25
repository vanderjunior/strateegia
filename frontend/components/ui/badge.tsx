import type { HTMLAttributes, PropsWithChildren } from "react";

export function Badge({
  children,
  className = "",
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLSpanElement>>) {
  return (
    <span
      className={`inline-flex max-w-full items-center justify-center rounded-full border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.12)] px-3 py-1 text-center font-mono text-[10px] uppercase leading-[1.3] tracking-[0.24em] whitespace-normal break-words text-gold2 ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
