import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AuthIdentity } from "@/lib/api/types";
import { AuthProvider, useAuthContext } from "./AuthContext";

const identity: AuthIdentity = {
  user_id: 7,
  email: "candidate@example.com",
  role: "PARTICIPANT",
};

function Consumer() {
  const user = useAuthContext();
  return (
    <span>
      {user.email}:{user.role}:{user.user_id}
    </span>
  );
}

describe("AuthContext", () => {
  it("exposes the server-seeded identity to consumers", () => {
    render(
      <AuthProvider initialUser={identity}>
        <Consumer />
      </AuthProvider>
    );
    expect(screen.getByText("candidate@example.com:PARTICIPANT:7")).toBeInTheDocument();
  });

  it("throws when used outside a provider", () => {
    // Silence React's error boundary console noise for this expected throw.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Consumer />)).toThrow(/within an <AuthProvider>/);
    spy.mockRestore();
  });
});
