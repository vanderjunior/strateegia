import type { AcceptedUploadType } from "@/lib/api/types";

export const MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md"] as const;
export const ACCEPTED_MIME_TYPES = [
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/x-markdown"
] as const;
export const ACCEPT_STRING = ".pdf,.txt,.md,text/plain,text/markdown,application/pdf";

export const acceptedUploadTypes: AcceptedUploadType[] = [
  {
    id: "pdf-textual",
    label: "PDF textual",
    extensions: [".pdf"],
    mimeTypes: ["application/pdf"]
  },
  {
    id: "txt",
    label: "TXT",
    extensions: [".txt"],
    mimeTypes: ["text/plain"]
  },
  {
    id: "markdown",
    label: "Markdown",
    extensions: [".md"],
    mimeTypes: ["text/markdown", "text/x-markdown"],
    note: "Validação"
  },
  {
    id: "pdf-scanned",
    label: "PDF digitalizado",
    extensions: [".pdf"],
    mimeTypes: ["application/pdf"],
    note: "OCR em validação"
  }
];

export function extensionForFileName(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  if (dotIndex < 0) {
    return "";
  }
  return filename.slice(dotIndex).toLowerCase();
}

export function validateUploadFile(file: File): { valid: boolean; message: string } {
  const ext = extensionForFileName(file.name);
  if (!ACCEPTED_EXTENSIONS.includes(ext as (typeof ACCEPTED_EXTENSIONS)[number])) {
    return { valid: false, message: "Tipo de arquivo não suportado." };
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return { valid: false, message: "O arquivo excede o limite atual de 5 MB." };
  }
  if (file.type && !ACCEPTED_MIME_TYPES.includes(file.type as (typeof ACCEPTED_MIME_TYPES)[number])) {
    return { valid: false, message: "O arquivo não passou na validação de tipo." };
  }
  return { valid: true, message: "Arquivo pronto para validação." };
}

export function formatUploadFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isScannedPdfFile(file: File | null): boolean {
  if (!file) {
    return false;
  }
  return extensionForFileName(file.name) === ".pdf" && file.name.toLowerCase().includes("scan");
}
