from abc import ABC, abstractmethod


class UI(ABC):
    @abstractmethod
    def init(self):
        """Initialize the application"""

    @abstractmethod
    def run(self):
        """Run the application, return when done"""

    @abstractmethod
    def cleanup(self):
        """Clean up resources after event loop is done"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_gui() -> UI:
    from ui.tkgui import TkGui
    return TkGui()
