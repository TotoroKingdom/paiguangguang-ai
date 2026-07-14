import type { EncryptedLoginRequest, LoginEncryptionKeyData } from "@/types/auth";


type EncryptionOptions = {
  cryptoApi?: Crypto;
  now?: () => number;
};


function bytesToBase64Url(value: ArrayBuffer | Uint8Array) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}


export async function encryptLoginPassword(
  password: string,
  keyData: LoginEncryptionKeyData,
  options: EncryptionOptions = {}
): Promise<Omit<EncryptedLoginRequest, "email">> {
  const cryptoApi = Object.prototype.hasOwnProperty.call(options, "cryptoApi")
    ? options.cryptoApi
    : globalThis.crypto;
  if (!cryptoApi?.subtle || typeof cryptoApi.getRandomValues !== "function") {
    throw new Error("Secure login is not supported by this browser");
  }

  const nonceBytes = new Uint8Array(18);
  cryptoApi.getRandomValues(nonceBytes);
  const envelope = {
    password,
    issued_at: Math.floor((options.now?.() ?? Date.now()) / 1000),
    nonce: bytesToBase64Url(nonceBytes),
  };
  const publicKey = await cryptoApi.subtle.importKey(
    "jwk",
    keyData.public_key,
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["encrypt"]
  );
  const plaintext = new TextEncoder().encode(JSON.stringify(envelope));
  const ciphertext = await cryptoApi.subtle.encrypt(
    { name: "RSA-OAEP" },
    publicKey,
    plaintext
  );
  return {
    encrypted_password: bytesToBase64Url(ciphertext),
    key_id: keyData.key_id,
  };
}
