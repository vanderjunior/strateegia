import type { HTMLAttributes, PropsWithChildren } from "react";

export function Card({
  children,
  className = "",
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={`rounded-[28px] border border-[rgba(168,184,196,0.12)] bg-[linear-gradient(180deg,rgba(21,39,56,0.96),rgba(10,21,32,0.98))] p-6 shadow-shell ${className}`}
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
