import { describe, expect, it, vi } from "vitest";

import { encryptLoginPassword } from "@/lib/login-encryption";
import type { LoginEncryptionKeyData } from "@/types/auth";


describe("encryptLoginPassword", () => {
  it("uses RSA-OAEP SHA-256 and returns only ciphertext metadata", async () => {
    let encodedPlaintext: Uint8Array | undefined;
    const importedKey = {} as CryptoKey;
    const cryptoApi = {
      getRandomValues<T extends ArrayBufferView>(array: T) {
        const bytes = new Uint8Array(array.buffer, array.byteOffset, array.byteLength);
        bytes.forEach((_, index) => {
          bytes[index] = index + 1;
        });
        return array;
      },
      subtle: {
        importKey: vi.fn().mockResolvedValue(importedKey),
        encrypt: vi.fn().mockImplementation(async (_algorithm, _key, plaintext) => {
          encodedPlaintext = plaintext as Uint8Array;
          return new Uint8Array([250, 251, 252]).buffer;
        }),
      },
    } as unknown as Crypto;
    const keyData: LoginEncryptionKeyData = {
      key_id: "key-1",
      algorithm: "RSA-OAEP-256",
      public_key: {
        kty: "RSA",
        n: "modulus",
        e: "AQAB",
        alg: "RSA-OAEP-256",
        use: "enc",
        key_ops: ["encrypt"],
      },
    };

    const result = await encryptLoginPassword("Secret123!", keyData, {
      cryptoApi,
      now: () => 1_784_044_800_000,
    });

    expect(cryptoApi.subtle.importKey).toHaveBeenCalledWith(
      "jwk",
      keyData.public_key,
      { name: "RSA-OAEP", hash: "SHA-256" },
      false,
      ["encrypt"]
    );
    const encryptCall = vi.mocked(cryptoApi.subtle.encrypt).mock.calls[0];
    expect(encryptCall[0]).toEqual({ name: "RSA-OAEP" });
    expect(encryptCall[1]).toBe(importedKey);
    expect(ArrayBuffer.isView(encryptCall[2])).toBe(true);
    expect(JSON.parse(new TextDecoder().decode(encodedPlaintext))).toEqual({
      password: "Secret123!",
      issued_at: 1_784_044_800,
      nonce: "AQIDBAUGBwgJCgsMDQ4PEBES",
    });
    expect(result).toEqual({
      encrypted_password: "-vv8",
      key_id: "key-1",
    });
    expect(result).not.toHaveProperty("password");
  });

  it("never falls back when Web Crypto is unavailable", async () => {
    await expect(
      encryptLoginPassword("Secret123!", {
        key_id: "key-1",
        algorithm: "RSA-OAEP-256",
        public_key: {} as JsonWebKey,
      }, { cryptoApi: undefined })
    ).rejects.toThrow("Secure login is not supported by this browser");
  });
});
