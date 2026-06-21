import { describe, expect, it } from "vitest";
import {
  isPasswordError,
  isPasswordMismatch,
  mismatchField,
} from "./auth-errors";

describe("mismatchField", () => {
  it("routes a password-mismatch message to the confirm field", () => {
    expect(mismatchField("Passwords don't match.")).toBe("confirm");
    expect(mismatchField("Password doesn't match.")).toBe("confirm");
  });

  it("routes a credentials error to the password field", () => {
    expect(mismatchField("Incorrect email or password")).toBe("password");
    expect(mismatchField("Invalid credentials")).toBe("password");
  });

  it("routes anything else to the email field", () => {
    expect(mismatchField("Account already exists")).toBe("email");
    expect(mismatchField("Some other error")).toBe("email");
  });
});

describe("isPasswordError", () => {
  it("returns false on null", () => {
    expect(isPasswordError(null)).toBe(false);
  });

  it("returns true for credentials errors", () => {
    expect(isPasswordError("Incorrect email or password")).toBe(true);
  });

  it("returns false for confirm-field errors", () => {
    expect(isPasswordError("Passwords don't match")).toBe(false);
  });
});

describe("isPasswordMismatch", () => {
  it("returns false on null", () => {
    expect(isPasswordMismatch(null)).toBe(false);
  });

  it("returns true for confirm-field errors", () => {
    expect(isPasswordMismatch("Passwords don't match")).toBe(true);
  });

  it("returns false for credentials errors", () => {
    expect(isPasswordMismatch("Incorrect email or password")).toBe(false);
  });
});
