import { useState, useEffect, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { getPdfFromStore } from "@/utils/indexedDB";

export function usePdfViewer(policyId: string, sourceText?: string) {
    const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
    const [pageNum, setPageNum] = useState(1);
    const [pageCount, setPageCount] = useState(0);
    const [scale, setScale] = useState(1.2);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [highlights, setHighlights] = useState<{ x: number, y: number, w: number, h: number }[]>([]);

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const overlayRef = useRef<HTMLDivElement>(null);

    // 1. Fetch PDF Blob & Load Document
    useEffect(() => {
        setIsLoading(true);
        getPdfFromStore(policyId)
            .then(async (blob) => {
                if (!blob) {
                    setError("PDF not found in local cache. Please upload the document on this device to view it.");
                    setIsLoading(false);
                    return;
                }
                const arrayBuffer = await blob.arrayBuffer();
                const loadingTask = pdfjsLib.getDocument(new Uint8Array(arrayBuffer));
                const doc = await loadingTask.promise;
                setPdfDoc(doc);
                setPageCount(doc.numPages);
                setIsLoading(false);
            })
            .catch((err) => {
                console.error("Failed to load PDF", err);
                setError("Failed to load PDF document.");
                setIsLoading(false);
            });
    }, [policyId]);

    // 2. Render Page & Find Highlights
    useEffect(() => {
        if (!pdfDoc || !canvasRef.current || !overlayRef.current) return;

        let renderTask: pdfjsLib.RenderTask | null = null;
        let isCancelled = false;

        const renderPage = async () => {
            try {
                const page = await pdfDoc.getPage(pageNum);
                if (isCancelled) return;

                const viewport = page.getViewport({ scale });
                const canvas = canvasRef.current;
                const context = canvas?.getContext("2d");

                if (!canvas || !context) return;

                canvas.height = viewport.height;
                canvas.width = viewport.width;

                // Overlay sizing wrapper
                if (overlayRef.current) {
                    overlayRef.current.style.width = `${viewport.width}px`;
                    overlayRef.current.style.height = `${viewport.height}px`;
                }

                renderTask = page.render({ canvasContext: context, viewport });
                await renderTask.promise;

                // -- Text Highlighting Logic --
                if (sourceText) {
                    const textContent = await page.getTextContent();
                    const targetStr = sourceText.replace(/\s+/g, '').toLowerCase().substring(0, 50); // Fuzzy normalize

                    let currentStr = "";
                    let tempHighlights: typeof highlights = [];

                    for (let i = 0; i < textContent.items.length; i++) {
                        const item = textContent.items[i] as any;
                        const str = item.str.replace(/\s+/g, '').toLowerCase();
                        currentStr += str;

                        // Convert PDF rect to Viewport rect array
                        // item.transform is [scaleX, skewY, skewX, scaleY, tx, ty]
                        tempHighlights.push({
                            x: item.transform[4],
                            y: item.transform[5],
                            w: item.width,
                            h: item.height
                        });

                        if (currentStr.includes(targetStr)) {
                            // Match found on this page. Map all temp highlights to viewport
                            const mappedBoxes = tempHighlights.map(h => {
                                // pdfjs coordinates are inverse Y
                                const pt1 = viewport.convertToViewportPoint(h.x, h.y);
                                const pt2 = viewport.convertToViewportPoint(h.x + h.w, h.y + h.h);
                                return {
                                    x: Math.min(pt1[0], pt2[0]),
                                    y: Math.min(pt1[1], pt2[1]),
                                    w: Math.abs(pt1[0] - pt2[0]),
                                    h: Math.abs(pt1[1] - pt2[1])
                                };
                            });

                            setHighlights(mappedBoxes);

                            // Try to scroll the highlighted container into view
                            setTimeout(() => {
                                overlayRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
                            }, 200);

                            return;
                        }

                        if (currentStr.length > 300) {
                            // Prevent huge buffer, reset trailing context
                            currentStr = currentStr.slice(-100);
                            tempHighlights = tempHighlights.slice(-10);
                        }
                    }
                    // If we reach here, we didn't find the text on this page
                    setHighlights([]);
                }

            } catch (err) {
                if ((err as Error).name !== "RenderingCancelledException") {
                    console.error("Render error:", err);
                }
            }
        };

        renderPage();

        return () => {
            isCancelled = true;
            if (renderTask) {
                renderTask.cancel();
            }
        };
    }, [pdfDoc, pageNum, scale, sourceText]);

    const prevPage = () => setPageNum((prev) => Math.max(1, prev - 1));
    const nextPage = () => setPageNum((prev) => Math.min(pageCount, prev + 1));
    const zoomIn = () => setScale((prev) => Math.min(3, prev + 0.2));
    const zoomOut = () => setScale((prev) => Math.max(0.6, prev - 0.2));

    return {
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
    };
}
