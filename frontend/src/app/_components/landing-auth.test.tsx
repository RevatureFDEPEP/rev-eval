import { beforeEach, describe, expect, it, jest } from "@jest/globals";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { mockRouter } from "@/test/mocks/next-navigation";

import { LandingAuth } from "./landing-auth";

const mockFetch = jest.fn<typeof fetch>();

describe("LandingAuth", () => {
  beforeEach(() => {
    mockRouter.push.mockReset();
    mockRouter.refresh.mockReset();
    mockFetch.mockReset();
    global.fetch = mockFetch;
  });

  it("submits login credentials and navigates to the dashboard", async () => {
    const user = userEvent.setup();
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    render(<LandingAuth />);

    await user.type(screen.getByLabelText(/email/i), "participant@example.com");
    await user.type(screen.getByLabelText(/password/i), "Password123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith("/api/auth/login", {
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
    mockFetch.mockResolvedValue({
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
      expect(mockFetch).toHaveBeenCalledWith("/api/auth/register", {
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
    mockFetch.mockResolvedValue({
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
