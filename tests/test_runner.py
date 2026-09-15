"""
Root test runner proxy.
Runs all backend and edge test suites.
"""
import pytest
import sys
import os

if __name__ == "__main__":
    edge_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "edge", "src"))
    sys.path.insert(0, edge_src)
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    exit_code = pytest.main(["backend/tests", "edge/tests", "-v"])
    sys.exit(exit_code)
