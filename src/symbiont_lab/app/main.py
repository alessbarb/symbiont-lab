from __future__ import annotations


def main() -> None:
    try:
        import tkinter as tk
    except ImportError as exc:
        raise RuntimeError("Symbiont Lab desktop application requires tkinter.") from exc
    from .main_window import SymbiontLabWindow

    root = tk.Tk()
    SymbiontLabWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
