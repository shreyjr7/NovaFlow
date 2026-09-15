"""NovaFlow Edge AI package."""
import logging

logger = logging.getLogger(__name__)


def load_config(path: str = "../config/edge.yaml"):
    try:
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        logger.warning("PyYAML not installed. Returning empty config.")
        return {}
