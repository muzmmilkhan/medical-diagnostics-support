export interface UploadResponse {
  message: string;
  filename: string;
  chunks_processed: number;
  stored_in_s3: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Source {
  source: string;
  page: number | null;
  snippet: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
}
