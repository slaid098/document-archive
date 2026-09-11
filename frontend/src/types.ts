/** Типы под ответы backend (app/schemas.py). */

export interface Version {
  id: number;
  version_number: number;
  file_name: string;
  file_size: number;
  sha256_hash: string;
  comment: string | null;
  created_at: string;
  download_url: string;
}

export interface DocumentItem {
  id: number;
  title: string;
  document_number: string;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  version_count: number;
  current_version: Version | null;
}

export interface DocumentsResponse {
  documents: DocumentItem[];
  cached: boolean;
}

export interface DocumentDetail extends DocumentItem {
  versions: Version[];
}

export interface UploadResult {
  document: DocumentItem | null;
  version: Version;
  deduplicated: boolean;
  bytes_saved: number;
}

export interface Stats {
  logical_bytes: number;
  physical_bytes: number;
  saved_bytes: number;
}