import sys
import customtkinter as ctk

from ui import LabelingPage


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1280x720")
        self.minsize(1280, 720)

        self.page = None

    def set_page(self, *args, **kwargs):
        self.page = LabelingPage(self, *args, **kwargs)
        self.page.pack(expand=True, fill="both")

if __name__ == "__main__":
    app = App()
    app.set_page('data')
    app.mainloop()

