import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef } from "react";
import { UploadCloud, X, CheckCircle2, Loader2, FileArchive, Shield } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";

export const Route = createFileRoute("/_authenticated/feedback_/upload")({
  component: UploadFeedbackPage,
});

// PII Redaction logic (Frontend-side)
function redactPII(text: string): string {
  let redacted = text;
  // Redact Vietnamese Phone numbers (03, 05, 07, 08, 09) + 8 digits
  redacted = redacted.replace(/(0[3|5|7|8|9])+([0-9]{8})\b/g, "[SĐT_ĐÃ_ẨN]");
  // Redact License Plates (e.g., 29A-12345 or 29A-123.45)
  redacted = redacted.replace(/\d{2}[A-Z]\d?-\d{3}\.?\d{2}/gi, "[BIỂN_SỐ_ĐÃ_ẨN]");
  // Basic email redaction
  redacted = redacted.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, "[EMAIL_ĐÃ_ẨN]");
  return redacted;
}

function UploadFeedbackPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [csvData, setCsvData] = useState<{text: string, channel: string, area: string}[]>([]);
  const [manualText, setManualText] = useState("");
  const [mode, setMode] = useState<"text" | "csv">("text");
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [batchId, setBatchId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFile = (f: File) => {
    if (f.type !== "text/csv" && !f.name.endsWith(".csv")) {
      toast.error("Vui lòng tải lên file CSV.");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      toast.error("File quá lớn. Tối đa 5MB.");
      return;
    }
    setFile(f);
    parseCSV(f);
  };

  const parseCSV = (f: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split("\n").filter(l => l.trim() !== "");
      if (lines.length <= 1) {
         toast.error("File CSV trống hoặc chỉ có header.");
         setFile(null);
         return;
      }
      
      const parsed = lines.slice(1).map(line => {
        // Use a simple regex to split by comma outside quotes
        const parts = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map(p => p.trim().replace(/^"|"$/g, ''));
        const rawText = parts[0] || "";
        const redactedText = redactPII(rawText);
        return {
           text: redactedText,
           channel: parts[1] || "app",
           area: parts[2] || "HAN"
        };
      }).filter(item => item.text.length > 0);
      
      setCsvData(parsed);
      toast.success(`Đã đọc thành công ${parsed.length} dòng.`);
    };
    reader.readAsText(f);
  };

  const cancelUpload = () => {
    setFile(null);
    setCsvData([]);
  };

  const submitManual = async () => {
    if (!manualText.trim()) return;
    setIsProcessing(true);
    
    try {
      const redactedText = redactPII(manualText.trim());
      await apiFetch("/api/feedback/submit", {
        method: "POST",
        body: JSON.stringify({ text: redactedText, channel: "app", area: "HAN" }),
      });
      
      toast.success("Đã gửi phản hồi thành công.");
      setManualText("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Đã có lỗi xảy ra");
    } finally {
      setIsProcessing(false);
    }
  };

  const submitBatch = async () => {
    if (csvData.length === 0) return;
    setIsProcessing(true);
    setProgress(0);
    const id = crypto.randomUUID();
    setBatchId(id);
    abortControllerRef.current = new AbortController();

    let successCount = 0;
    try {
      for (let i = 0; i < csvData.length; i++) {
        if (abortControllerRef.current.signal.aborted) {
           toast.info("Đã hủy quá trình tải lên.");
           break;
        }
        
        await apiFetch("/api/feedback/submit", {
          method: "POST",
          body: JSON.stringify({ ...csvData[i], batch_id: id }),
          signal: abortControllerRef.current.signal
        });
        
        successCount++;
        setProgress(Math.round(((i + 1) / csvData.length) * 100));
        // Add a small delay to avoid rate limiting
        await new Promise(r => setTimeout(r, 100));
      }
      if (!abortControllerRef.current.signal.aborted) {
        toast.success(`Đã xử lý xong ${successCount} phản hồi (Batch: ${id.slice(0, 8)})`);
        cancelUpload();
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        toast.error("Lỗi khi gửi một số phản hồi. Vui lòng thử lại.");
      }
    } finally {
      setIsProcessing(false);
      abortControllerRef.current = null;
    }
  };

  const cancelProcessing = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Nạp Dữ liệu Phản hồi</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hỗ trợ tải lên file CSV hoặc nhập tay. Thông tin cá nhân (PII) sẽ tự động được che đi trước khi lưu trữ.
        </p>
      </div>

      <div className="flex gap-4 border-b border-border pb-px">
        <button 
          onClick={() => setMode("text")}
          className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${mode === "text" ? "border-xanh-green text-xanh-deep" : "border-transparent text-muted-foreground hover:text-foreground"}`}
        >
          Nhập trực tiếp
        </button>
        <button 
          onClick={() => setMode("csv")}
          className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${mode === "csv" ? "border-xanh-green text-xanh-deep" : "border-transparent text-muted-foreground hover:text-foreground"}`}
        >
          Tải lên CSV (Bulk)
        </button>
      </div>

      {mode === "text" && (
        <section className="rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-card)] animate-in fade-in slide-in-from-bottom-2">
           <label className="block text-sm font-semibold mb-2">Nội dung phản hồi</label>
           <textarea
             rows={4}
             value={manualText}
             onChange={(e) => setManualText(e.target.value)}
             placeholder="Nhập nội dung phản hồi tại đây. Số điện thoại và biển số xe sẽ tự động được làm mờ."
             className="w-full p-3 rounded-xl border border-border focus:outline-none focus:ring-2 focus:ring-xanh-green/40 resize-none bg-muted/20"
             disabled={isProcessing}
           />
           {manualText && (
             <div className="mt-3 p-3 rounded-xl bg-amber-50 border border-amber-100 flex gap-3 text-sm text-amber-900">
               <Shield className="h-5 w-5 shrink-0 text-amber-600" />
               <div>
                 <p className="font-semibold text-xs mb-1 text-amber-800">Preview (Sau khi che PII):</p>
                 <p className="font-mono text-xs opacity-80">{redactPII(manualText)}</p>
               </div>
             </div>
           )}
           <div className="mt-4 flex justify-end">
             <button
                onClick={submitManual}
                disabled={isProcessing || !manualText.trim()}
                className="h-10 px-5 rounded-xl text-white font-semibold flex items-center gap-2 shadow-[var(--shadow-green)] disabled:opacity-60 transition-all hover:opacity-90"
                style={{ background: "var(--gradient-green)" }}
             >
                {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : "Gửi Phản Hồi"}
             </button>
           </div>
        </section>
      )}

      {mode === "csv" && (
        <section className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
          {!file && (
            <div 
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center text-center transition-colors
                ${dragActive ? "border-xanh-green bg-xanh-green/5" : "border-border bg-card hover:bg-muted/30"}
              `}
            >
              <div className="h-14 w-14 rounded-full bg-xanh-green/10 flex items-center justify-center mb-4">
                <UploadCloud className="h-7 w-7 text-xanh-green" />
              </div>
              <h3 className="font-semibold text-lg">Kéo thả file CSV vào đây</h3>
              <p className="text-muted-foreground text-sm mt-1 mb-6">
                hoặc click để chọn file từ máy tính
              </p>
              <label className="cursor-pointer h-10 px-5 rounded-xl bg-card border border-border text-sm font-semibold flex items-center shadow-sm hover:bg-muted/50 transition-colors">
                Chọn File
                <input type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
              </label>
              <div className="mt-6 text-xs text-muted-foreground">
                <p>Định dạng: text, channel, area (có header)</p>
                <p>Dung lượng tối đa 5MB.</p>
              </div>
            </div>
          )}

          {file && !isProcessing && (
             <div className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] overflow-hidden animate-in fade-in slide-in-from-bottom-2">
                <div className="p-4 border-b border-border bg-muted/20 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileArchive className="h-8 w-8 text-xanh-deep opacity-80" />
                    <div>
                      <h3 className="font-semibold text-sm">{file.name}</h3>
                      <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB • {csvData.length} hợp lệ</p>
                    </div>
                  </div>
                  <button onClick={cancelUpload} className="p-2 hover:bg-muted rounded-full transition-colors">
                    <X className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
                
                <div className="p-4 bg-amber-50/50 border-b border-amber-100 flex gap-2 items-start">
                   <Shield className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                   <p className="text-xs text-amber-800">
                     <strong>Bảo mật & PII:</strong> Hệ thống tự động che số điện thoại, email và biển số xe trước khi lưu vào cơ sở dữ liệu. Xem trước kết quả ở bảng dưới.
                   </p>
                </div>

                <div className="max-h-[300px] overflow-y-auto p-0">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0 backdrop-blur-md">
                      <tr>
                        <th className="px-4 py-3 font-medium">Nội dung (Đã che PII)</th>
                        <th className="px-4 py-3 font-medium w-24">Kênh</th>
                        <th className="px-4 py-3 font-medium w-24">Khu vực</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {csvData.slice(0, 50).map((row, i) => (
                        <tr key={i} className="hover:bg-muted/20 transition-colors">
                          <td className="px-4 py-3 font-mono text-xs max-w-sm truncate">{row.text}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 rounded bg-muted text-[10px] uppercase font-mono">{row.channel}</span>
                          </td>
                          <td className="px-4 py-3">
                             <span className="px-2 py-1 rounded bg-muted text-[10px] uppercase font-mono">{row.area}</span>
                          </td>
                        </tr>
                      ))}
                      {csvData.length > 50 && (
                        <tr>
                          <td colSpan={3} className="px-4 py-4 text-center text-xs text-muted-foreground">
                            ... và {csvData.length - 50} dòng nữa
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="p-4 border-t border-border bg-muted/10 flex justify-end gap-3">
                  <button 
                    onClick={cancelUpload}
                    className="h-9 px-4 text-sm font-medium border border-border rounded-lg hover:bg-muted transition-colors"
                  >
                    Hủy bỏ
                  </button>
                  <button 
                    onClick={submitBatch}
                    className="h-9 px-6 text-sm font-semibold rounded-lg text-white shadow-[var(--shadow-green)] transition-all hover:opacity-90 flex items-center gap-2"
                    style={{ background: "var(--gradient-green)" }}
                  >
                    <CheckCircle2 className="h-4 w-4" /> Bắt đầu Nạp ({csvData.length})
                  </button>
                </div>
             </div>
          )}

          {isProcessing && mode === "csv" && (
            <div className="rounded-2xl border border-border bg-card p-8 shadow-[var(--shadow-card)] text-center animate-in fade-in zoom-in-95">
              <div className="relative w-20 h-20 mx-auto mb-6">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" className="stroke-muted fill-none stroke-[8]" />
                  <circle 
                    cx="50" cy="50" r="45" 
                    className="stroke-xanh-green fill-none stroke-[8] transition-all duration-300" 
                    strokeDasharray="283" 
                    strokeDashoffset={283 - (283 * progress) / 100}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center font-display font-bold text-xl text-xanh-deep">
                  {progress}%
                </div>
              </div>
              <h3 className="font-semibold text-lg mb-1">Đang nạp dữ liệu...</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Batch ID: <span className="font-mono text-xs">{batchId?.slice(0,8)}</span> • Vui lòng không đóng trang này.
              </p>
              <button 
                onClick={cancelProcessing}
                className="text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 px-4 py-2 rounded-lg transition-colors inline-flex items-center gap-1"
              >
                <X className="h-3 w-3" /> Dừng quá trình
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
