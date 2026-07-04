"use client";

import { Component, type ReactNode } from "react";

type Props = { children: ReactNode; label?: string };
type State = { error: Error | null };

export class PageErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
          <p className="text-sm font-medium text-danger">
            {this.props.label ?? "This page"} failed to render
          </p>
          <p className="max-w-md text-xs text-muted">{this.state.error.message}</p>
          <button
            type="button"
            className="rounded-lg border border-border bg-panel px-4 py-2 text-sm text-white hover:bg-surface"
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
