import type { ButtonHTMLAttributes, PropsWithChildren } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
  }
>;

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "bg-gold text-surface-3 shadow-gold hover:bg-[#dfc08a]",
  secondary:
    "border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] text-ink hover:bg-[rgba(201,169,110,0.16)]",
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
      className={`inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-medium transition duration-200 ${variantClass[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
