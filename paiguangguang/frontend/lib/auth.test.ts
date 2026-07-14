import { beforeEach, describe, expect, it, vi } from "vitest";

import { getJson, postJson } from "@/lib/api";
import { login } from "@/lib/auth";
import { encryptLoginPassword } from "@/lib/login-encryption";


vi.mock("@/lib/api", () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
}));

vi.mock("@/lib/login-encryption", () => ({
  encryptLoginPassword: vi.fn(),
}));


describe("login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits no plaintext password field or value", async () => {
    vi.mocked(getJson).mockResolvedValue({
      key_id: "key-1",
      algorithm: "RSA-OAEP-256",
      public_key: { kty: "RSA", n: "n", e: "AQAB" },
    });
    vi.mocked(encryptLoginPassword).mockResolvedValue({
      encrypted_password: "ciphertext-only",
      key_id: "key-1",
    });
    vi.mocked(postJson).mockResolvedValue({ access_token: "token", token_type: "bearer" });

    await login({ email: "admin@example.com", password: "Secret123!" });

    expect(getJson).toHaveBeenCalledWith("/api/v1/auth/encryption-key");
    expect(postJson).toHaveBeenCalledWith("/api/v1/auth/login", {
      email: "admin@example.com",
      encrypted_password: "ciphertext-only",
      key_id: "key-1",
    });
    const serializedBody = JSON.stringify(vi.mocked(postJson).mock.calls[0][1]);
    expect(serializedBody).not.toContain("Secret123!");
    expect(vi.mocked(postJson).mock.calls[0][1]).not.toHaveProperty("password");
  });
});
