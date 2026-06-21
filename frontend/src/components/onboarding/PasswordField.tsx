import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/cn";

/** Password input with a show/hide toggle. Extracted from AuthGate so the
 * AuthGate file stays focused on form state + submission rather than the
 * mechanics of one field. The visible `*` (required indicator) is `aria-hidden`
 * so it doesn't leak into the accessible name — WCAG 3.3.2.
 */
export function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
  show,
  onToggle,
  minLength,
  invalid,
  describedBy,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  placeholder: string;
  show: boolean;
  onToggle: () => void;
  /** Skip minLength on login so existing short-password accounts still work. */
  minLength?: number | undefined;
  invalid?: boolean;
  describedBy?: string | undefined;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs text-text-lo">
        {label}{" "}
        <span aria-hidden="true" className="text-danger">
          *
        </span>
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? "text" : "password"}
          autoComplete={autoComplete}
          required
          aria-required="true"
          {...(invalid ? { "aria-invalid": true } : {})}
          {...(describedBy ? { "aria-describedby": describedBy } : {})}
          {...(minLength !== undefined ? { minLength } : {})}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "h-10 w-full rounded-md border border-border-strong bg-surface-1 pl-3 pr-10 text-text-hi placeholder:text-text-lo",
          )}
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={onToggle}
          aria-label={show ? "Hide password" : "Show password"}
          aria-pressed={show}
          className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded text-text-lo transition-colors hover:text-text-hi"
        >
          {show ? (
            <EyeOff size={16} aria-hidden />
          ) : (
            <Eye size={16} aria-hidden />
          )}
        </button>
      </div>
    </div>
  );
}
