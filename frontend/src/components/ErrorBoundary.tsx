import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full min-h-[300px] flex items-center justify-center p-6 bg-gray-950 text-gray-100">
          <div className="max-w-md w-full bg-gray-900 border border-rose-900/60 rounded-2xl p-6 shadow-2xl space-y-4 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center border border-rose-500/40">
              <AlertOctagon size={24} />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                {this.props.fallbackTitle || "Render Interruption Caught"}
              </h3>
              <p className="text-xs text-gray-400 mt-1">
                An unhandled exception was safely caught by the NovaFlow Error Boundary.
              </p>
              {this.state.error && (
                <div className="mt-3 p-2 bg-gray-950 rounded-lg border border-gray-800 text-[11px] font-mono text-rose-300 break-words text-left max-h-28 overflow-y-auto">
                  {this.state.error.message || String(this.state.error)}
                </div>
              )}
            </div>
            <button
              onClick={this.handleReset}
              className="px-4 py-2 bg-brand hover:bg-brand/80 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 mx-auto transition shadow-lg"
            >
              <RefreshCw size={14} />
              <span>Recover Component</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
