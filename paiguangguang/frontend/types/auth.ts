export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AuthTokenData = {
  access_token: string;
  token_type: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type EncryptedLoginRequest = {
  email: string;
  encrypted_password: string;
  key_id: string;
};

export type LoginEncryptionKeyData = {
  key_id: string;
  algorithm: "RSA-OAEP-256";
  public_key: JsonWebKey;
};
