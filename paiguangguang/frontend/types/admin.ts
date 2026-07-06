export type AdminPagedResponse<T> = T[] & {
  total: number;
  page: number;
  page_size: number;
};

export type AdminDocumentData = {
  doc_id: string;
  title: string | null;
  original_filename: string | null;
  text_length: number;
  content_hash: string;
  owner_user_id: string | null;
  workspace_id: string | null;
  permission_scope: string | null;
  status: string;
  parse_status: string;
  chunk_status: string;
  embedding_status: string;
  index_status: string;
  is_deleted: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminIngestionJobData = {
  job_id: string;
  document_id: string;
  status: string;
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  is_reindex: boolean;
  chunk_size: number | null;
  chunk_overlap: number | null;
  created_at: string;
  updated_at: string;
};

export type AdminDocumentUpdateRequest = {
  title?: string | null;
  original_filename?: string | null;
  text?: string | null;
  owner_user_id?: string | null;
  workspace_id?: string | null;
  permission_scope?: string | null;
  status?: string | null;
  parse_status?: string | null;
  chunk_status?: string | null;
  embedding_status?: string | null;
  index_status?: string | null;
  error_message?: string | null;
  is_deleted?: boolean | null;
};

export type AdminDocumentCreateRequest = {
  title?: string | null;
  original_filename?: string | null;
  text: string;
  owner_user_id?: string | null;
  workspace_id?: string | null;
  permission_scope?: string | null;
};

export type AdminUserData = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  roles: string[];
  workspace_ids: string[];
  effective_permissions: string[];
};

export type AdminUserCreateRequest = {
  email: string;
  display_name: string;
  password: string;
  is_active?: boolean;
  roles?: string[];
  workspace_slugs?: string[];
};

export type AdminUserUpdateRequest = {
  display_name?: string | null;
  password?: string | null;
  is_active?: boolean | null;
  roles?: string[] | null;
  workspace_slugs?: string[] | null;
};

export type AdminRoleData = {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
  created_at: string;
  updated_at: string;
};

export type AdminRoleCreateRequest = {
  name: string;
  description?: string | null;
  permissions?: string[];
};

export type AdminRoleUpdateRequest = {
  name?: string | null;
  description?: string | null;
  permissions?: string[] | null;
};

export type AdminPermissionData = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminPermissionCreateRequest = {
  name: string;
  description?: string | null;
};

export type AdminPermissionUpdateRequest = {
  name?: string | null;
  description?: string | null;
};

export type AdminWorkspaceData = {
  id: string;
  slug: string;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminWorkspaceCreateRequest = {
  slug: string;
  name: string;
  is_default?: boolean;
};

export type AdminWorkspaceUpdateRequest = {
  slug?: string | null;
  name?: string | null;
  is_default?: boolean | null;
};
