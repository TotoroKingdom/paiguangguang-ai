export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function getBackendBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  return configuredUrl ? configuredUrl.replace(/\/+$/, "") : "";
}

type ApiEnvelope<T> = {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
  } | null;
};

type RequestOptions = {
  token?: string | null;
};

async function requestJson<TResponse>(
  path: string,
  init: RequestInit,
  options?: RequestOptions
): Promise<TResponse> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = options?.token?.trim();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    ...init,
    headers
  });

  const payload = (await response.json()) as ApiEnvelope<TResponse>;

  if (!response.ok || !payload.success || !payload.data) {
    throw new ApiError(
      payload.error?.message || "Request failed",
      response.status,
      payload.error?.code || "REQUEST_FAILED"
    );
  }

  return payload.data;
}

async function requestFormData<TResponse>(path: string, init: RequestInit, options?: RequestOptions): Promise<TResponse> {
  const headers = new Headers(init.headers);
  const token = options?.token?.trim();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    ...init,
    headers,
  });

  const payload = (await response.json()) as ApiEnvelope<TResponse>;

  if (!response.ok || !payload.success || !payload.data) {
    throw new ApiError(
      payload.error?.message || "Request failed",
      response.status,
      payload.error?.code || "REQUEST_FAILED"
    );
  }

  return payload.data;
}

export async function postJson<TResponse, TBody extends Record<string, unknown>>(
  path: string,
  body: TBody,
  options?: RequestOptions
): Promise<TResponse> {
  return requestJson<TResponse>(
    path,
    {
      method: "POST",
      body: JSON.stringify(body)
    },
    options
  );
}

export async function getJson<TResponse>(path: string, options?: RequestOptions): Promise<TResponse> {
  return requestJson<TResponse>(
    path,
    {
      method: "GET"
    },
    options
  );
}

export async function postEmptyJson<TResponse>(path: string, options?: RequestOptions): Promise<TResponse> {
  return requestJson<TResponse>(
    path,
    {
      method: "POST"
    },
    options
  );
}

export async function postFormData<TResponse>(path: string, body: FormData, options?: RequestOptions): Promise<TResponse> {
  return requestFormData<TResponse>(
    path,
    {
      method: "POST",
      body,
    },
    options
  );
}

export async function patchJson<TResponse, TBody extends Record<string, unknown>>(
  path: string,
  body: TBody,
  options?: RequestOptions
): Promise<TResponse> {
  return requestJson<TResponse>(
    path,
    {
      method: "PATCH",
      body: JSON.stringify(body)
    },
    options
  );
}

export async function deleteJson<TResponse>(path: string, options?: RequestOptions): Promise<TResponse> {
  return requestJson<TResponse>(
    path,
    {
      method: "DELETE"
    },
    options
  );
}
