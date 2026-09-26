import Link from "next/link";
import { Compass, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6 font-sans">
      <div className="glass-panel p-8 rounded-2xl border border-white/10 max-w-md w-full shadow-2xl flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-ensemble/15 border border-ensemble/30 flex items-center justify-center text-ensemble">
          <Compass className="w-6 h-6 animate-pulse" />
        </div>
        
        <div className="space-y-1">
          <span className="text-[11px] font-mono uppercase tracking-wider text-ensemble font-semibold">
            Error 404
          </span>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Page Not Found
          </h1>
          <p className="text-xs text-text-secondary leading-relaxed">
            The requested page does not exist or has been removed.
          </p>
        </div>

        <Link
          href="/"
          className="mt-2 flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-ensemble text-slate-950 hover:bg-ensemble/90 transition-all shadow-md"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}
