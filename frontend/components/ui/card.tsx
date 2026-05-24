import type { HTMLAttributes, PropsWithChildren } from "react";

export function Card({
  children,
  className = "",
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={`relative overflow-hidden rounded-[28px] border border-[rgba(168,184,196,0.12)] bg-[linear-gradient(180deg,rgba(21,39,56,0.96),rgba(10,21,32,0.98))] p-6 shadow-shell transition duration-300 before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-[linear-gradient(90deg,transparent,rgba(201,169,110,0.26),transparent)] hover:border-[rgba(201,169,110,0.16)] hover:bg-[linear-gradient(180deg,rgba(36,63,85,0.94),rgba(10,21,32,0.98))] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className = "",
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLHeadingElement>>) {
  return (
    <h3 className={`font-serif text-2xl text-ink ${className}`} {...props}>
      {children}
    </h3>
  );
}
