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

  // --- audit/2026-08: focus management (WCAG 2.4.3) --------------------------

  it("moves focus to the confirm button on open", () => {
    render(
      <ConfirmDialog
        open
        title="Log out?"
        confirmLabel="Log out"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Log out" })).toHaveFocus();
  });

  it("traps Tab inside the dialog instead of letting it escape to the page", async () => {
    const user = userEvent.setup();
    render(
      <>
        <button type="button">Behind the overlay</button>
        <ConfirmDialog
          open
          title="Log out?"
          cancelLabel="Cancel"
          confirmLabel="Log out"
          onConfirm={() => {}}
          onCancel={() => {}}
        />
      </>,
    );

    const confirm = screen.getByRole("button", { name: "Log out" });
    const cancel = screen.getByRole("button", { name: "Cancel" });
    const outside = screen.getByRole("button", { name: "Behind the overlay" });
    expect(confirm).toHaveFocus();

    // Confirm is the last focusable in the panel — Tab must wrap to the first.
    await user.tab();
    expect(outside).not.toHaveFocus();
    expect(cancel).toHaveFocus();

    // ...and Shift+Tab from the first wraps back to the last.
    await user.tab({ shift: true });
    expect(confirm).toHaveFocus();
  });

  it("returns focus to the trigger when it closes", () => {
    function Harness({ open }: { open: boolean }) {
      return (
        <>
          <button type="button">Account menu</button>
          <ConfirmDialog
            open={open}
            title="Log out?"
            onConfirm={() => {}}
            onCancel={() => {}}
          />
        </>
      );
    }
    const { rerender } = render(<Harness open={false} />);
    const trigger = screen.getByRole("button", { name: "Account menu" });
    trigger.focus();

    rerender(<Harness open />);
    expect(trigger).not.toHaveFocus();

    rerender(<Harness open={false} />);
    expect(trigger).toHaveFocus();
  });
});
