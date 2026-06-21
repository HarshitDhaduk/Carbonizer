/** Map a humanised error message back to which field is at fault. Used by
 * the error-summary anchor + the per-field `aria-invalid` flag in
 * AuthGate so the offending input is announced + focusable in one click.
 */
export function mismatchField(
  message: string,
): "email" | "password" | "confirm" {
  const lower = message.toLowerCase();
  if (lower.includes("don't match") || lower.includes("doesn't match"))
    return "confirm";
  if (lower.includes("password") || lower.includes("credentials"))
    return "password";
  return "email";
}

export function isPasswordError(message: string | null): boolean {
  if (!message) return false;
  return mismatchField(message) === "password";
}

export function isPasswordMismatch(message: string | null): boolean {
  if (!message) return false;
  return mismatchField(message) === "confirm";
}
