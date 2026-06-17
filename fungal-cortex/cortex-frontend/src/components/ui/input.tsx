"use client";

import { forwardRef, useState, type InputHTMLAttributes } from "react";

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  /** Show search icon on the left */
  search?: boolean;
  /** Show clear button when input has value */
  clearable?: boolean;
  onClear?: () => void;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      search = false,
      clearable = false,
      onClear,
      value,
      defaultValue,
      onChange,
      className = "",
      placeholder = "Search...",
      ...rest
    },
    ref,
  ) => {
    const [internalValue, setInternalValue] = useState(
      defaultValue?.toString() ?? "",
    );
    const isControlled = value !== undefined;
    const currentValue = isControlled ? value.toString() : internalValue;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!isControlled) setInternalValue(e.target.value);
      onChange?.(e);
    };

    const handleClear = () => {
      if (!isControlled) setInternalValue("");
      onClear?.();
      // If we had a ref to the input element we'd dispatch a change event on it
    };

    const hasValue = currentValue.length > 0;

    return (
      <div className="relative">
        {/* Search icon */}
        {search && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#666688] pointer-events-none">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </span>
        )}

        <input
          ref={ref}
          value={isControlled ? value : undefined}
          defaultValue={isControlled ? undefined : defaultValue}
          onChange={handleChange}
          placeholder={placeholder}
          className={[
            "w-full rounded-lg border border-[#1e1e3a] bg-[#0a0a0f] text-sm text-white placeholder-[#666688]",
            "transition-colors duration-150",
            "focus:border-[#00d4aa] focus:outline-none focus:ring-1 focus:ring-[#00d4aa]/40",
            "disabled:cursor-not-allowed disabled:opacity-50",
            search ? "pl-9 pr-9" : "px-3 pr-9",
            "py-2",
            className,
          ].join(" ")}
          {...rest}
        />

        {/* Clear button */}
        {clearable && hasValue && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center justify-center size-5 rounded-md text-[#666688] hover:text-white hover:bg-[#1e1e3a] transition-colors"
            aria-label="Clear input"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

export { Input };
