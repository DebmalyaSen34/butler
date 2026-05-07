import os
import logging

logger = logging.getLogger(__name__)

def create_file(filename: str, content: str) -> str:
    try:
        base_dir = os.getcwd()
        filepath = os.path.join(base_dir, filename)

        with open(filepath, 'w') as f:
            f.write(content)
        return f"Success: File '{filename}' created."
    except Exception as e:
        logger.error(f"Error creating file '{filename}': {e}", exc_info=True)
        return f"Error: Could not create file '{filename}'."
