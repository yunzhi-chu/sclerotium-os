import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  children?: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[#00d4aa] text-[#0a0a0f] hover:bg-[#00e8bb] active:bg-[#00c099] disabled:bg-[#00d4aa]/40",
  secondary:
    "bg-[#7c3aed] text-white hover:bg-[#8b5cf6] active:bg-[#6d28d9] disabled:bg-[#7c3aed]/40",
  danger:
    "bg-[#ef4444] text-white hover:bg-[#f87171] active:bg-[#dc2626] disabled:bg-[#ef4444]/40",
  ghost:
    "bg-transparent text-[#a0a0c0] hover:bg-[#1e1e3a] hover:text-white active:bg-[#2a2a4a] disabled:text-[#a0a0c0]/40",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-6 py-3 text-base gap-2.5",
};

const Spinner = ({ size }: { size: ButtonSize }) => {
  const dimension = size === "sm" ? 12 : size === "md" ? 16 : 20;
  return (
    <svg
      className="animate-spin shrink-0"
      width={dimension}
      height={dimension}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="31.4 31.4"
        className="opacity-25"
      />
      <path
        d="M12 2a10 10 0 019.95 9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      children,
      className = "",
      type = "button",
      ...rest
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={[
          "inline-flex items-center justify-center font-medium rounded-lg",
          "transition-all duration-150 ease-in-out",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00d4aa]/50 focus-visible:ring-offset-1 focus-visible:ring-offset-[#141428]",
          "cursor-pointer disabled:cursor-not-allowed select-none",
          variantClasses[variant],
          sizeClasses[size],
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        {...rest}
      >
        {loading && <Spinner size={size} />}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";

export { Button };
