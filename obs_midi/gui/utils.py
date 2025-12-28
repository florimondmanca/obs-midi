import tkinter as tk
from tkinter import ttk
from typing import Any


def scrollable_frame(
    parent: tk.BaseWidget, **kwargs: Any
) -> tuple[ttk.Frame, ttk.Frame]:
    """
    A scrollable tkinter frame implementation

    Credits
    - https://gist.github.com/JackTheEngineer/81df334f3dcff09fd19e4169dd560c59
    - https://sqlpey.com/python/tkinter-scrollable-frames
    """

    outer = ttk.Frame(parent, **kwargs)

    # Canvas for scrolling
    canvas = tk.Canvas(outer, borderwidth=0)
    inner = ttk.Frame(canvas)

    v_scrollbar = ttk.Scrollbar(outer, command=canvas.yview)
    canvas.configure(yscrollcommand=v_scrollbar.set)

    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    canvas.create_window((4, 4), window=inner, anchor="nw", tags="inner_frame")

    inner.bind(
        "<Configure>", lambda *args: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.bind_all(
        "<MouseWheel>",
        lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"),
    )
    canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

    return outer, inner
