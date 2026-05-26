import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/documents", () => ({
  uploadMaterialFile: vi.fn()
}));

import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import {
  acceptedUploadTypes,
  extensionForFileName,
  formatUploadFileSize,
  validateUploadFile
} from "@/components/workspace/upload-validation";
import { getApiConfig } from "@/lib/api/config";

function makeFile(name: string, type: string, size = 1024): File {
  const file = new File(["demo"], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("upload validation helpers and component states", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("accepts valid pdf, txt, and md files", () => {
    expect(validateUploadFile(makeFile("material.pdf", "application/pdf")).valid).toBe(true);
    expect(validateUploadFile(makeFile("material.txt", "text/plain")).valid).toBe(true);
    expect(validateUploadFile(makeFile("material.md", "text/markdown")).valid).toBe(true);
    expect(extensionForFileName("material.md")).toBe(".md");
    expect(formatUploadFileSize(1024)).toBe("1 KB");
  });

  it("rejects oversized files and unsupported extensions", () => {
    expect(validateUploadFile(makeFile("material.exe", "application/octet-stream")).message).toBe(
      "Tipo de arquivo não suportado."
    );
    expect(validateUploadFile(makeFile("material.pdf", "application/pdf", 6 * 1024 * 1024)).message).toBe(
      "O arquivo excede o limite atual de 5 MB."
    );
  });

  it("keeps .markdown out of the accepted backend extension list", () => {
    const serialized = JSON.stringify(acceptedUploadTypes);
    expect(serialized).not.toContain(".markdown");
  });

  it("requires a valid file plus confirmation before enabling send", async () => {
    const { container } = render(<MaterialUploadEntryClient />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const checkbox = screen.getByRole("checkbox");
    const button = screen.getByRole("button", { name: "Enviar para validação" });

    expect(button).toBeDisabled();
    expect(screen.getAllByText(/OCR em validação/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PDFs escaneados podem exigir OCR/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Confirmo que este material pode ser enviado para validação.")).toBeInTheDocument();

    fireEvent.change(fileInput, {
      target: {
        files: [makeFile("material.pdf", "application/pdf")]
      }
    });

    await waitFor(() => {
      expect(screen.getAllByText("Arquivo pronto para validação.").length).toBeGreaterThan(0);
    });
    expect(button).toBeDisabled();

    fireEvent.click(checkbox);
    expect(button).toBeEnabled();
  });

  it("shows a friendly invalid message for unsupported files", () => {
    const { container } = render(<MaterialUploadEntryClient />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: {
        files: [makeFile("material.exe", "application/octet-stream")]
      }
    });

    expect(screen.getAllByText("Tipo de arquivo não suportado.").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Enviar para validação" })).toBeDisabled();
  });
});
