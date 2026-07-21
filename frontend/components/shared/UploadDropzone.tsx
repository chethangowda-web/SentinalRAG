"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, File, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

interface UploadDropzoneProps {
  onUpload: (file: File) => void;
  progress: number;
  isUploading: boolean;
  disabled?: boolean;
}

const ALLOWED_TYPES = [".pdf", ".png", ".jpg", ".jpeg"];
const MAX_SIZE = 50 * 1024 * 1024;

export function UploadDropzone({
  onUpload,
  progress,
  isUploading,
  disabled,
}: UploadDropzoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_TYPES.includes(ext)) {
      return `Invalid file type. Allowed: ${ALLOWED_TYPES.join(", ")}`;
    }
    if (file.size > MAX_SIZE) {
      return `File too large. Maximum size is 50MB.`;
    }
    if (file.size === 0) {
      return "File is empty.";
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      const err = validateFile(file);
      if (err) {
        setError(err);
        return;
      }
      setSelectedFile(file);
      onUpload(file);
    },
    [onUpload, validateFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleClick = () => inputRef.current?.click();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-2">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={disabled ? undefined : handleClick}
        className={cn(
          "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-all duration-200",
          dragOver
            ? "border-primary bg-primary/5"
            : error
            ? "border-destructive bg-destructive/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-secondary/30",
          disabled && "pointer-events-none opacity-50"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled}
        />

        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-4">
          <Upload className="h-6 w-6 text-primary" />
        </div>

        <p className="text-sm font-medium">
          {isUploading ? "Uploading..." : "Drop your file here"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          or click to browse (PDF, PNG, JPG — up to 50MB)
        </p>

        {selectedFile && !isUploading && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-secondary/50 px-3 py-2">
            <File className="h-4 w-4 text-primary" />
            <span className="text-sm">{selectedFile.name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                setError(null);
              }}
              className="ml-2 rounded p-0.5 hover:bg-secondary"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {error && (
          <p className="mt-3 text-xs text-destructive">{error}</p>
        )}
      </div>
    </div>
  );
}
