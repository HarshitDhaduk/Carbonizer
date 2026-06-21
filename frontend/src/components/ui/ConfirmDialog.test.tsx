import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmDialog } from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("renders nothing when closed", () => {
    render(
      <ConfirmDialog
        open={false}
        title="Log out?"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("renders title + description when open", () => {
    render(
      <ConfirmDialog
        open
        title="Log out?"
        description="You'll need to sign in again."
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveAccessibleName("Log out?");
    expect(dialog).toHaveAccessibleDescription("You'll need to sign in again.");
  });

  it("Escape fires onCancel", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Log out?"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("Confirm click fires onConfirm exactly once", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Log out?"
        confirmLabel="Log out"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Log out" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("backdrop click fires onCancel", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Log out?"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    // The first child button is the backdrop (aria-hidden).
    const backdrop = screen
      .getAllByRole("button", { hidden: true })
      .find((btn) => btn.getAttribute("aria-hidden") === "true");
    expect(backdrop).toBeDefined();
    if (backdrop) await user.click(backdrop);
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
