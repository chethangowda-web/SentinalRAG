"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, File, X, CheckCircle2, Loader2 } from "lucide-react";
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

  const resetFile = () => {
    setSelectedFile(null);
    setError(null);
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
            ? "border-primary bg-primary/5 shadow-sm"
            : error
            ? "border-destructive bg-destructive/5"
            : isUploading
            ? "border-primary/30 bg-primary/3"
            : "border-muted-foreground/25 hover:border-primary/50 hover:bg-primary/3 hover:shadow-sm",
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

        <AnimatePresence mode="wait">
          {isUploading ? (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-4">
                <Loader2 className="h-6 w-6 text-primary animate-spin" />
              </div>
              <p className="text-sm font-medium">Uploading...</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {selectedFile?.name}
              </p>
              <div className="w-48 mt-4">
                <Progress value={progress} className="h-1.5" />
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground tabular-nums">
                {progress}% complete
              </p>
            </motion.div>
          ) : selectedFile && !error ? (
            <motion.div
              key="selected"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-success/10 mb-4">
                <File className="h-6 w-6 text-success" />
              </div>
              <p className="text-sm font-medium">{selectedFile.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Ready to upload
              </p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  resetFile();
                }}
                className="mt-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-3 w-3" />
                Remove file
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-4">
                <Upload className="h-6 w-6 text-primary" />
              </div>
              <p className="text-sm font-medium">
                Drop your file here
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                or click to browse (PDF, PNG, JPG — up to 50MB)
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <motion.p
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 text-xs text-destructive flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            {error}
          </motion.p>
        )}
      </div>
    </div>
  );
}
