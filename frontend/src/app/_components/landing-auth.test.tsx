import { afterEach, beforeEach, describe, expect, it, jest } from "@jest/globals";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { mockRouter, resetMockRouter } from "@/test/mocks/next-navigation";

import { LandingAuth } from "./landing-auth";

const originalFetch = global.fetch;

describe("LandingAuth", () => {
  beforeEach(() => {
    resetMockRouter();
    if (!global.fetch) {
      Object.defineProperty(global, "fetch", {
        configurable: true,
        writable: true,
        value: jest.fn(),
      });
    }
  });

  afterEach(() => {
    jest.restoreAllMocks();
    if (originalFetch) {
      global.fetch = originalFetch;
    } else {
      Reflect.deleteProperty(global, "fetch");
    }
  });

  it("submits login credentials and navigates to the dashboard", async () => {
    const user = userEvent.setup();
    const fetchSpy = jest.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    render(<LandingAuth />);

    await user.type(screen.getByLabelText(/email/i), "participant@example.com");
    await user.type(screen.getByLabelText(/password/i), "Password123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "participant@example.com",
          password: "Password123!",
        }),
      });
    });
    expect(mockRouter.push).toHaveBeenCalledWith("/dashboard");
    expect(mockRouter.refresh).toHaveBeenCalled();
  });

  it("submits register details with the selected role", async () => {
    const user = userEvent.setup();
    const fetchSpy = jest.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    render(<LandingAuth />);

    await user.click(screen.getByRole("tab", { name: /register/i }));
    await user.type(screen.getByLabelText(/full name/i), "Test Trainer");
    await user.type(screen.getByLabelText(/email/i), "trainer@example.com");
    await user.type(screen.getByLabelText(/password/i), "Password123!");
    await user.selectOptions(screen.getByLabelText(/role/i), "TRAINER");
    await user.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "trainer@example.com",
          password: "Password123!",
          full_name: "Test Trainer",
          role: "TRAINER",
        }),
      });
    });
    expect(mockRouter.push).toHaveBeenCalledWith("/dashboard");
    expect(mockRouter.refresh).toHaveBeenCalled();
  });

  it("renders API errors without navigating", async () => {
    const user = userEvent.setup();
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Invalid credentials" }),
    } as Response);

    render(<LandingAuth />);

    await user.type(screen.getByLabelText(/email/i), "participant@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
    expect(mockRouter.push).not.toHaveBeenCalled();
    expect(mockRouter.refresh).not.toHaveBeenCalled();
  });
});
