import customtkinter as ctk

class BaseView(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.config_manager = config_manager
        self.log_textbox = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Light mode background for views
        self.configure(fg_color="#F9F9FB")

    def log(self, message):
        if self.log_textbox:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        else:
            try:
                print(f"[VERBOSE] {message}")
            except UnicodeEncodeError:
                # Fallback for consoles that don't support UTF-8
                print(f"[VERBOSE] {message.encode('ascii', 'replace').decode('ascii')}")

    def create_header(self, title):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="ew")
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text=title, 
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#333333" 
        )
        title_label.pack(side="left")
        
        # Red underline/accent
        accent = ctk.CTkFrame(self, fg_color="#C30021", height=4, width=50)
        accent.place(x=30, y=65)
        
        return header_frame

    def create_card(self, parent, **kwargs):
        """Helper to create a white rounded card"""
        card = ctk.CTkFrame(
            parent, 
            corner_radius=15, 
            fg_color="#FFFFFF", 
            border_width=1,
            border_color="#EEEEEE",
            **kwargs
        )
        return card
