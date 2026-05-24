import type { ButtonHTMLAttributes, PropsWithChildren } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
  }
>;

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "bg-gold text-surface-3 shadow-gold hover:-translate-y-0.5 hover:bg-[#dfc08a] hover:shadow-[0_12px_36px_rgba(201,169,110,0.26)]",
  secondary:
    "border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] text-ink hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)]",
  ghost:
    "border border-[rgba(168,184,196,0.12)] bg-transparent text-silver hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
};

export function Button({
  children,
  className = "",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-medium tracking-[-0.01em] transition duration-200 ${variantClass[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
