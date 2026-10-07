from abc import ABC, abstractmethod
from core.logger import logger

class BaseAgent(ABC):
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.logger = logger
        
    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the agent's primary task."""
        pass

    def run_with_retry(self, func, retries=3, *args, **kwargs):
        for attempt in range(1, retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"Attempt {attempt} failed in {self.__class__.__name__}: {str(e)}")
                if attempt == retries:
                    self.logger.error(f"All {retries} attempts failed in {self.__class__.__name__}.")
                    raise e
