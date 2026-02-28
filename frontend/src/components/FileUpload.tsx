import { useRef } from "react";
import { Upload } from "lucide-react";
import { useDragAndDrop } from "@/hooks/useDragAndDrop";

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function FileUpload({ onFile, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  
  const { dragOver, handleFile, onDragOver, onDragLeave, onDrop } = useDragAndDrop(onFile);

  return (
    <div
      className={`dropzone${dragOver ? " drag-over" : ""}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="icon">
        <Upload size={40} />
      </div>
      <p>
        <strong>Drop your policy PDF here</strong>
      </p>
      <p>
        <small className="text-light">or click to browse</small>
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt"
        disabled={disabled}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  );
}
