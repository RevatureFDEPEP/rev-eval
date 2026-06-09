import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LandingAuth } from "./landing-auth";

// Stub the App Router so onSubmit's navigation is observable.
const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

function mockFetch(response: { ok: boolean; body?: unknown }) {
  const json = vi.fn().mockResolvedValue(response.body ?? {});
  const fetchMock = vi.fn().mockResolvedValue({ ok: response.ok, json });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  push.mockReset();
  refresh.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LandingAuth", () => {
  it("renders the login tab by default without register-only fields", () => {
    render(<LandingAuth />);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.queryByLabelText("Full name")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Role")).not.toBeInTheDocument();
  });

  it("reveals full name + role + the password hint when switching to Register", () => {
    render(<LandingAuth />);
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Register" }));
    expect(screen.getByLabelText("Full name")).toBeInTheDocument();
    expect(screen.getByLabelText("Role")).toBeInTheDocument();
    expect(screen.getByText("Minimum 8 characters.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Register" })).toBeInTheDocument();
  });

  it("posts login credentials and navigates to the dashboard on success", async () => {
    const fetchMock = mockFetch({ ok: true });
    render(<LandingAuth />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [endpoint, init] = fetchMock.mock.calls[0];
    expect(endpoint).toBe("/api/auth/login");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      email: "user@example.com",
      password: "secret123",
    });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(refresh).toHaveBeenCalled();
  });

  it("posts full_name and role when registering", async () => {
    const fetchMock = mockFetch({ ok: true });
    render(<LandingAuth />);
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Register" }));

    fireEvent.change(screen.getByLabelText("Full name"), {
      target: { value: "Ada Lovelace" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "ada@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "longenough" },
    });
    fireEvent.change(screen.getByLabelText("Role"), {
      target: { value: "TRAINER" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [endpoint, init] = fetchMock.mock.calls[0];
    expect(endpoint).toBe("/api/auth/register");
    expect(JSON.parse(init.body)).toEqual({
      email: "ada@example.com",
      password: "longenough",
      full_name: "Ada Lovelace",
      role: "TRAINER",
    });
  });

  it("renders the server error detail and does not navigate on failure", async () => {
    mockFetch({ ok: false, body: { detail: "Invalid credentials" } });
    render(<LandingAuth />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("surfaces a network error when fetch rejects", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("boom"));
    vi.stubGlobal("fetch", fetchMock);
    render(<LandingAuth />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("boom")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("disables the submit button while the request is in flight", async () => {
    let resolveFetch: (value: { ok: boolean; json: () => Promise<unknown> }) => void = () => {};
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        })
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<LandingAuth />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    const button = await screen.findByRole("button", { name: "Working…" });
    expect(button).toBeDisabled();

    resolveFetch({ ok: true, json: () => Promise.resolve({}) });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });
});
