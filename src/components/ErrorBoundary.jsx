import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-600 shadow-sm mb-4">
            <AlertCircle size={32} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Unable to connect to HealBytes Clinical Network</h1>
          <p className="mt-2 text-sm text-slate-500 max-w-md">
            The application encountered a critical error communicating with the backend. 
            Please check your network connection and ensure the server is running.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 transition"
          >
            <RefreshCw size={16} />
            Retry Connection
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
