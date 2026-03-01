import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Search } from "lucide-react";
import { usePdfViewer } from "@/hooks/usePdfViewer";

// Configure worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.mjs`;

interface Props {
  policyId: string;
  sourceText?: string;
  onClose: () => void;
}

export function PdfViewerModal({ policyId, sourceText, onClose }: Props) {
  const {
    pageNum,
    pageCount,
    scale,
    isLoading,
    error,
    highlights,
    canvasRef,
    overlayRef,
    prevPage,
    nextPage,
    zoomIn,
    zoomOut
  } = usePdfViewer(policyId, sourceText);

  return (
    <div style={{
      position: "fixed",
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: "rgba(0,0,0,0.8)",
      zIndex: 9999,
      display: "flex",
      flexDirection: "column",
      backdropFilter: "blur(4px)"
    }}>
      {/* Header Toolbar */}
      <div style={{
        padding: "16px",
        background: "var(--background)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
           <h3 style={{ margin: 0, fontSize: "16px" }}>Document Viewer</h3>
           {sourceText && (
              <span style={{ fontSize: "12px", background: "var(--primary-light)", color: "var(--primary-dark)", padding: "4px 8px", borderRadius: "12px", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Search size={14} /> Tracking source text
              </span>
           )}
        </div>
        
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
           <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "var(--background-alt)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border)" }}>
             <button onClick={zoomOut} style={{ padding: "4px", background: "transparent", border: "none", color: "var(--foreground)" }}><ZoomOut size={16} /></button>
             <span style={{ fontSize: "12px", minWidth: "40px", textAlign: "center", color: "var(--foreground)" }}>{Math.round(scale * 100)}%</span>
             <button onClick={zoomIn} style={{ padding: "4px", background: "transparent", border: "none", color: "var(--foreground)" }}><ZoomIn size={16} /></button>
           </div>
           
           <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "var(--background-alt)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border)" }}>
             <button onClick={prevPage} disabled={pageNum <= 1} style={{ padding: "4px", background: "transparent", border: "none", color: pageNum <= 1 ? "var(--muted-foreground)" : "var(--foreground)" }}><ChevronLeft size={16} /></button>
             <span style={{ fontSize: "12px", minWidth: "60px", textAlign: "center", color: "var(--foreground)" }}>Page {pageNum} of {pageCount}</span>
             <button onClick={nextPage} disabled={pageNum >= pageCount} style={{ padding: "4px", background: "transparent", border: "none", color: pageNum >= pageCount ? "var(--muted-foreground)" : "var(--foreground)" }}><ChevronRight size={16} /></button>
           </div>
           
           <button onClick={onClose} style={{ padding: "8px", marginLeft: "16px", borderRadius: "50%", background: "var(--background-alt)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--foreground)", cursor: "pointer" }}>
             <X size={20} />
           </button>
        </div>
      </div>

      {/* PDF Container */}
      <div style={{ flex: 1, overflow: "auto", display: "flex", justifyContent: "center", padding: "32px" }}>
         {isLoading && <div style={{ color: "white", alignSelf: "center" }}>Loading PDF...</div>}
         {error && <div style={{ color: "var(--danger)", alignSelf: "center" }}>{error}</div>}
         
         {!isLoading && !error && (
            <div style={{ position: "relative", boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }} ref={overlayRef}>
                <canvas ref={canvasRef} style={{ display: "block", backgroundColor: "white" }} />
                
                {/* Highlights Overlay */}
                {highlights.map((h, i) => (
                    <div 
                       key={i}
                       style={{
                           position: "absolute",
                           left: h.x,
                           top: h.y,
                           width: h.w,
                           height: h.h,
                           backgroundColor: "rgba(255, 255, 0, 0.4)",
                           mixBlendMode: "multiply",
                           pointerEvents: "none"
                       }}
                    />
                ))}
            </div>
         )}
      </div>
    </div>
  );
}
