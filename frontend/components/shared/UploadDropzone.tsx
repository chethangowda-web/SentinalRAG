"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, File, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

interface UploadDropzoneProps {
  onUpload: (file: File) => void;
  progress: number;
  isUploading: boolean;
  disabled?: boolean;
}

const ACCEPTED_TYPES = [".pdf", ".png", ".jpg", ".jpeg"];

export function UploadDropzone({ onUpload, progress, isUploading, disabled }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setIsDragging(true);
    if (e.type === "dragleave") setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSelect(file);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSelect(file);
  };

  const validateAndSelect = (file: File) => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      alert("Please upload a PDF, PNG, JPG, or JPEG file.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      alert("File is too large. Maximum size is 50MB.");
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  return (
    <div className="space-y-4">
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "relative cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition-all duration-200",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-secondary/50",
          disabled && "pointer-events-none opacity-50"
        )}
      >
        <input ref={inputRef} type="file" accept={ACCEPTED_TYPES.join(",")} onChange={handleFileSelect} className="hidden" />
        <div className="flex flex-col items-center gap-3">
          <div className="rounded-full bg-primary/10 p-4">
            <Upload className={cn("h-8 w-8 text-primary", isDragging && "animate-bounce")} />
          </div>
          <div>
            <p className="text-sm font-medium">
              {isDragging ? "Drop your file here" : "Drag & drop your file here"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">or click to browse</p>
          </div>
          <div className="flex gap-3 text-[10px] text-muted-foreground">
            {ACCEPTED_TYPES.map((t) => (
              <span key={t} className="rounded bg-secondary px-2 py-0.5 font-mono">{t}</span>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground">Maximum file size: 50MB</p>
        </div>
      </div>

      {selectedFile && !isUploading && (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <File className="h-8 w-8 text-primary" />
            <div>
              <p className="text-sm font-medium">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
          <button onClick={() => setSelectedFile(null)} className="rounded-lg p-2 hover:bg-secondary">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {isUploading && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Uploading & processing...</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      )}

      {selectedFile && !isUploading && (
        <button
          onClick={handleUpload}
          className="w-full rounded-lg bg-primary py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Upload Document
        </button>
      )}
    </div>
  );
}
