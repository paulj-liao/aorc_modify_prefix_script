# Step 1: Install the Rich module
# Run the following command in your terminal:
# pip install rich

# Step 2: Import necessary modules
import logging
from rich.logging import RichHandler

# Step 3: Configure logging
logging.basicConfig(
    level="NOTSET",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

# Step 4: Create a logger
logger = logging.getLogger("rich")

# Step 5: Log messages at different levels
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")