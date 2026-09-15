#!/usr/bin/env python3
"""
run_simulator.py
================
Convenience script to start the Edge AI Simulator.

Usage:
    python run_simulator.py [--host HOST] [--port PORT] [--reload]

Example:
    python run_simulator.py --port 7000

Then open the control panel at:
    http://localhost:7000/ui
"""

import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="NovaFlow Edge AI Simulator")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", default=7000, type=int, help="Port to listen on (default: 7000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print(f"\n🚍  NovaFlow Edge AI Simulator starting...")
    print(f"    Control Panel: http://localhost:{args.port}/ui")
    print(f"    API Docs:      http://localhost:{args.port}/docs")
    print(f"    Health:        http://localhost:{args.port}/health\n")

    uvicorn.run(
        "edge.src.edge.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

if __name__ == "__main__":
    main()
