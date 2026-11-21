import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
from math import ceil

APP_NAME = "PLAN B | Smart Study Recovery System"
DB_NAME = "plan_b.db"

# Calm, modern palette
BG = "#F7F3EA"
NAVY = "#34483B"
NAVY_2 = "#506957"
BLUE = "#8A9A78"
BLUE_LIGHT = "#E9EEE5"
TEAL = "#71866D"
TEAL_LIGHT = "#EEF2E9"
INK = "#343A32"
MUTED = "#85877D"
WHITE = "#FFFEFA"
BORDER = "#E8E1D5"
ORANGE = "#C18B55"


class PlanBApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1200x780")
        self.root.minsize(980, 680)
        self.root.configure(bg=BG)

        self.conn = sqlite3.connect(DB_NAME)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_database()
        self.setup_styles()
        self.build_shell()
        self.show_page("Dashboard")
        self.refresh_all()

    def create_database(self):
        # Keep the V1/V2 tables unchanged so existing subjects and sessions remain available.
        self.conn.execute("""CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            study_date TEXT NOT NULL,
            planned INTEGER NOT NULL,
            completed INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""")
        # Book tracker tables are added without changing existing subjects/sessions.
        self.conn.execute("""CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            book_no INTEGER NOT NULL,
            book_name TEXT NOT NULL,
            target_minutes INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            UNIQUE(subject_id, book_no)
        )""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS book_study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            study_date TEXT NOT NULL,
            minutes INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
        )""")
        self.conn.commit()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE,
                        foreground=INK, rowheight=32, borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#F0EAE0", foreground=NAVY,
                        font=("Segoe UI", 9, "bold"), relief="flat", padding=(8, 8))
        style.map("Treeview", background=[("selected", BLUE_LIGHT)],
                  foreground=[("selected", NAVY)])
        style.configure("TCombobox", padding=7, fieldbackground=WHITE)
        style.configure("TEntry", padding=8)
        style.configure("Horizontal.TProgressbar", troughcolor="#E8E1D5",
                        background=TEAL, bordercolor="#E8E1D5", lightcolor=TEAL,
                        darkcolor=TEAL)

    def build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=NAVY, width=218)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=NAVY)
        brand.pack(fill="x", padx=22, pady=(28, 30))
        tk.Label(brand, text="PLAN B", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(brand, text="STUDY SMARTER", bg=NAVY, fg="#DCE5D9",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 0))

        tk.Label(self.sidebar, text="WORKSPACE", bg=NAVY, fg="#B6C5B4",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22, pady=(0, 10))
        self.nav_buttons = {}
        for name, symbol in [("Dashboard", "▦"), ("Subjects", "▤"),
                             ("Books Tracker", "▣"), ("Study Log", "✎"), ("Recovery Planner", "↗"),
                             ("Exam Planner", "◷")]:
            btn = tk.Button(self.sidebar, text=f"  {symbol}    {name}",
                            command=lambda n=name: self.show_page(n),
                            anchor="w", bd=0, relief="flat", cursor="hand2",
                            bg=NAVY, fg="#D5DDF5", activebackground=NAVY_2,
                            activeforeground=WHITE, font=("Segoe UI", 10),
                            padx=15, pady=12)
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = btn

        bottom = tk.Frame(self.sidebar, bg=NAVY)
        bottom.pack(side="bottom", fill="x", padx=22, pady=22)
        tk.Label(bottom, text="LOCAL • PRIVATE • OFFLINE", bg=NAVY,
                 fg="#B6C5B4", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(bottom, text="Version 4.0 • Hackathon Edition", bg=NAVY, fg="#DCE5D9",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(5, 0))

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.topbar = tk.Frame(self.main, bg=WHITE, height=58,
                               highlightthickness=1, highlightbackground=BORDER)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)
        self.page_title = tk.Label(self.topbar, text="Dashboard", bg=WHITE,
                                   fg=INK, font=("Segoe UI", 12, "bold"))
        self.page_title.pack(side="left", padx=28)
        self.today_label = tk.Label(self.topbar, text=date.today().strftime("%A, %d %B %Y"),
                                    bg=WHITE, fg=MUTED, font=("Segoe UI", 9))
        self.today_label.pack(side="right", padx=28)

        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=24)
        self.pages = {}

    def show_page(self, name):
        for child in self.content.winfo_children():
            child.destroy()
        for nav_name, btn in self.nav_buttons.items():
            btn.configure(bg=NAVY_2 if nav_name == name else NAVY,
                          fg=WHITE if nav_name == name else "#D5DDF5")
        self.page_title.configure(text=name)
        builders = {
            "Dashboard": self.build_dashboard,
            "Subjects": self.build_subjects,
            "Books Tracker": self.build_books_tracker,
            "Study Log": self.build_log,
            "Recovery Planner": self.build_recovery,
            "Exam Planner": self.build_exam_planner,
        }
        builders[name]()
        self.current_page = name
        self.refresh_all()

    def heading(self, title, subtitle):
        tk.Label(self.content, text=title, bg=BG, fg=INK,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subtitle, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 18))

    def card(self, parent, padx=18, pady=16):
        frame = tk.Frame(parent, bg=WHITE, highlightthickness=1,
                         highlightbackground=BORDER, padx=padx, pady=pady)
        return frame

    def metric_card(self, parent, title, value, accent=BLUE):
        card = self.card(parent, 17, 15)
        tk.Frame(card, bg=accent, height=3).pack(fill="x", pady=(0, 12))
        tk.Label(card, text=title.upper(), bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(card, textvariable=value, bg=WHITE, fg=INK,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(6, 0))
        return card

    def build_dashboard(self):
        self.heading("Good to see you!", "A clear view of your study progress, all in one place.")
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")
        for i in range(4):
            cards.columnconfigure(i, weight=1, uniform="metric")
        self.subject_count_var = tk.StringVar(value="0")
        self.planned_total_var = tk.StringVar(value="0 min")
        self.completed_total_var = tk.StringVar(value="0 min")
        self.missed_total_var = tk.StringVar(value="0 min")
        metrics = [
            ("Subjects", self.subject_count_var, BLUE),
            ("Planned time", self.planned_total_var, "#7C5CDA"),
            ("Completed time", self.completed_total_var, TEAL),
            ("Missed time", self.missed_total_var, ORANGE),
        ]
        for i, (title, var, color) in enumerate(metrics):
            self.metric_card(cards, title, var, color).grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 9, 0), pady=4)

        progress_card = self.card(self.content, 18, 13)
        progress_card.pack(fill="x", pady=(12, 0))
        progress_head = tk.Frame(progress_card, bg=WHITE)
        progress_head.pack(fill="x")
        tk.Label(progress_head, text="OVERALL STUDY COMPLETION", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self.study_progress_text = tk.StringVar(value="0%")
        tk.Label(progress_head, textvariable=self.study_progress_text, bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 10, "bold")).pack(side="right")
        self.study_progress = ttk.Progressbar(progress_card, style="Horizontal.TProgressbar",
                                               maximum=100, mode="determinate")
        self.study_progress.pack(fill="x", pady=(9, 0))
        demo_row = tk.Frame(self.content, bg=BG)
        demo_row.pack(fill="x", pady=(9, 0))
        tk.Button(demo_row, text="Load Demo Data", command=self.load_demo_data,
                  bg="#EFE9DC", fg=NAVY, activebackground="#E4DCCB", activeforeground=NAVY,
                  bd=0, padx=13, pady=7, cursor="hand2",
                  font=("Segoe UI", 8, "bold")).pack(side="right")

        lower = tk.Frame(self.content, bg=BG)
        lower.pack(fill="both", expand=True, pady=(20, 0))
        recent_card = self.card(lower)
        recent_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(recent_card, text="Recent study sessions", bg=WHITE, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        self.recent_tree = self.make_tree(recent_card,
            [("date", "DATE", 105), ("subject", "SUBJECT", 190),
             ("planned", "PLANNED", 85), ("completed", "DONE", 85), ("missed", "MISSED", 85)])
        self.recent_tree._container.pack(fill="both", expand=True)
        tk.Button(recent_card, text="Delete Selected", command=self.delete_selected_session,
                  bg="#F7E8E3", fg="#A44735", activebackground="#F0D8D0",
                  bd=0, padx=12, pady=7, cursor="hand2",
                  font=("Segoe UI", 8, "bold")).pack(anchor="e", pady=(9, 0))

        tip = self.card(lower, 18, 18)
        tip.configure(width=230)
        tip.pack_propagate(False)
        tip.pack(side="right", fill="y", padx=(10, 0))
        tk.Label(tip, text="YOUR NEXT STEP", bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(tip, text="Small progress\nevery day adds up.", bg=WHITE, fg=INK,
                 justify="left", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(12, 8))
        tk.Label(tip, text="Log your study time regularly. PLAN B will keep track of missed minutes and help you recover them.",
                 bg=WHITE, fg=MUTED, justify="left", wraplength=185,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Button(tip, text="＋  Add study session", command=lambda: self.show_page("Study Log"),
                  bg=BLUE, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=12, pady=10, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(20, 0))

    def make_tree(self, parent, columns):
        wrap = tk.Frame(parent, bg=WHITE)
        tree = ttk.Treeview(wrap, columns=[c[0] for c in columns], show="headings", height=8)
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center", stretch=True)
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        tree._container = wrap
        return tree

    def build_subjects(self):
        self.heading("Your subjects", "Keep your semester subjects organized in one place.")
        form = self.card(self.content)
        form.pack(fill="x", pady=(0, 16))
        tk.Label(form, text="ADD A SUBJECT", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.subject_entry = ttk.Entry(form, width=42, font=("Segoe UI", 10))
        self.subject_entry.grid(row=1, column=0, sticky="w", padx=(0, 12))
        tk.Button(form, text="＋  Add subject", command=self.add_subject,
                  bg=BLUE, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=16, pady=9, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).grid(row=1, column=1, sticky="w")
        listing = self.card(self.content)
        listing.pack(fill="both", expand=True)
        tk.Label(listing, text="Subject list", bg=WHITE, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        self.subject_tree = self.make_tree(listing, [("id", "ID", 80), ("name", "SUBJECT NAME", 420)])
        self.subject_tree._container.pack(fill="both", expand=True)
        tk.Button(listing, text="Delete Selected", command=self.delete_selected_subject,
                  bg="#F7E8E3", fg="#A44735", activebackground="#F0D8D0",
                  bd=0, padx=12, pady=7, cursor="hand2",
                  font=("Segoe UI", 8, "bold")).pack(anchor="e", pady=(9, 0))

    def build_books_tracker(self):
        self.heading("Books tracker", "Add your books, record study minutes, and see the total automatically.")

        add_card = self.card(self.content, 18, 16)
        add_card.pack(fill="x", pady=(0, 14))
        tk.Label(add_card, text="ADD A BOOK", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        subjects = self.conn.execute("SELECT id, name FROM subjects ORDER BY name").fetchall()
        self.book_subject_map = {name: sid for sid, name in subjects}
        self.book_subject_var = tk.StringVar(value=subjects[0][1] if subjects else "")
        self.book_no_var = tk.StringVar(value="1")
        self.book_name_var = tk.StringVar()
        self.book_target_var = tk.StringVar(value="0")
        tk.Label(add_card, text="SUBJECT", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.book_subject_combo = ttk.Combobox(add_card, textvariable=self.book_subject_var,
            values=list(self.book_subject_map), state="readonly", width=24)
        self.book_subject_combo.grid(row=2, column=0, sticky="w", padx=(0, 12))
        tk.Label(add_card, text="BOOK NO.", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=1, sticky="w", padx=(0, 8))
        ttk.Combobox(add_card, textvariable=self.book_no_var, values=["1", "2", "3", "4", "5"],
                     state="readonly", width=8).grid(row=2, column=1, sticky="w", padx=(0, 12))
        tk.Label(add_card, text="BOOK NAME", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(add_card, textvariable=self.book_name_var, width=24).grid(row=2, column=2, sticky="w", padx=(0, 12))
        tk.Label(add_card, text="TARGET MIN", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=3, sticky="w", padx=(0, 8))
        ttk.Entry(add_card, textvariable=self.book_target_var, width=10).grid(row=2, column=3, sticky="w")
        tk.Button(add_card, text="＋  Add book", command=self.add_book,
                  bg=BLUE, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=16, pady=9, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).grid(row=2, column=4, sticky="w", padx=(12, 0))

        log_card = self.card(self.content, 18, 14)
        log_card.pack(fill="x", pady=(0, 14))
        tk.Label(log_card, text="RECORD STUDY TIME", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self.book_log_choice = tk.StringVar()
        self.book_minutes_var = tk.StringVar(value="30")
        self.book_log_date_var = tk.StringVar(value=date.today().isoformat())
        tk.Label(log_card, text="SELECT BOOK", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w")
        self.book_log_combo = ttk.Combobox(log_card, textvariable=self.book_log_choice,
                                           state="readonly", width=42)
        self.book_log_combo.grid(row=2, column=0, sticky="w", padx=(0, 12))
        tk.Label(log_card, text="MINUTES STUDIED", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=1, sticky="w")
        ttk.Entry(log_card, textvariable=self.book_minutes_var, width=12).grid(row=2, column=1, sticky="w", padx=(0, 12))
        tk.Label(log_card, text="DATE (YYYY-MM-DD)", bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=1, column=2, sticky="w")
        ttk.Entry(log_card, textvariable=self.book_log_date_var, width=18).grid(row=2, column=2, sticky="w", padx=(0, 12))
        tk.Button(log_card, text="Save study minutes", command=self.save_book_minutes,
                  bg=TEAL, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=16, pady=9, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).grid(row=2, column=3, sticky="w")

        totals = self.card(self.content, 16, 12)
        totals.pack(fill="x", pady=(0, 12))
        self.book_count_var = tk.StringVar(value="0 books")
        self.book_minutes_total_var = tk.StringVar(value="0 minutes studied")
        tk.Label(totals, textvariable=self.book_count_var, bg=WHITE, fg=INK,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(totals, textvariable=self.book_minutes_total_var, bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 11, "bold")).pack(side="right")
        self.book_progress_text = tk.StringVar(value="Book target progress: 0%")
        tk.Label(totals, textvariable=self.book_progress_text, bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(12, 4))
        self.book_progress = ttk.Progressbar(totals, style="Horizontal.TProgressbar",
                                              maximum=100, mode="determinate")
        self.book_progress.pack(fill="x")

        list_card = self.card(self.content, 16, 14)
        list_card.pack(fill="both", expand=True)
        tk.Label(list_card, text="BOOK-WISE STUDY SUMMARY", bg=WHITE, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        self.books_tree = self.make_tree(list_card, [
            ("subject", "SUBJECT", 180), ("number", "BOOK NO.", 80),
            ("name", "BOOK NAME", 190), ("target", "TARGET MIN", 100),
            ("studied", "STUDIED MIN", 110), ("remaining", "LEFT MIN", 100)])
        self.books_tree._container.pack(fill="both", expand=True)
        tk.Button(list_card, text="Delete Selected", command=self.delete_selected_book,
                  bg="#F7E8E3", fg="#A44735", activebackground="#F0D8D0",
                  bd=0, padx=12, pady=7, cursor="hand2",
                  font=("Segoe UI", 8, "bold")).pack(anchor="e", pady=(9, 0))
        self.refresh_books_tracker()

    def add_book(self):
        subject = self.book_subject_var.get().strip()
        if not subject or subject not in self.book_subject_map:
            messagebox.showwarning("Subject needed", "First add/select a subject in the Subjects page.")
            return
        name = self.book_name_var.get().strip() or f"Book {self.book_no_var.get()}"
        try:
            number = int(self.book_no_var.get())
            target = int(self.book_target_var.get())
            if number not in range(1, 6) or target < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Check details", "Book number must be 1–5 and target minutes must be 0 or more.")
            return
        try:
            self.conn.execute("INSERT INTO books(subject_id, book_no, book_name, target_minutes) VALUES (?, ?, ?, ?)",
                              (self.book_subject_map[subject], number, name, target))
            self.conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showwarning("Already added", f"Book {number} is already added for {subject}.")
            return
        self.book_name_var.set("")
        self.book_no_var.set(str(min(number + 1, 5)))
        self.refresh_books_tracker()

    def save_book_minutes(self):
        choice = self.book_log_choice.get().strip()
        book_id = self.book_choice_map.get(choice)
        if not book_id:
            messagebox.showwarning("Select a book", "Please add and select a book first.")
            return
        try:
            minutes = int(self.book_minutes_var.get())
            study_day = date.fromisoformat(self.book_log_date_var.get().strip()).isoformat()
            if minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid entry", "Enter a valid date and study minutes greater than zero.")
            return
        self.conn.execute("INSERT INTO book_study_logs(book_id, study_date, minutes) VALUES (?, ?, ?)",
                          (book_id, study_day, minutes))
        self.conn.commit()
        self.refresh_books_tracker()
        messagebox.showinfo("Saved", f"{minutes} study minutes added to {choice}.")

    def refresh_books_tracker(self):
        if not hasattr(self, "books_tree") or not self.books_tree.winfo_exists():
            return
        rows = self.conn.execute("""SELECT b.id, s.name, b.book_no, b.book_name,
            b.target_minutes, COALESCE(SUM(l.minutes), 0) AS studied
            FROM books b JOIN subjects s ON s.id=b.subject_id
            LEFT JOIN book_study_logs l ON l.book_id=b.id
            GROUP BY b.id, s.name, b.book_no, b.book_name, b.target_minutes
            ORDER BY s.name ASC, b.book_no ASC, b.id ASC""").fetchall()
        for item in self.books_tree.get_children():
            self.books_tree.delete(item)
        for book_id, subject, number, name, target, studied in rows:
            remaining = max(0, target - studied) if target else 0
            self.books_tree.insert("", "end", iid=str(book_id),
                values=(subject, number, name, target, studied, remaining))
        self.book_count_var.set(f"{len(rows)} books")
        total = sum(row[5] for row in rows)
        self.book_minutes_total_var.set(f"{total} minutes studied in total")
        target_total = sum(row[4] for row in rows)
        studied_total = total
        pct = min(100, round((studied_total / target_total) * 100)) if target_total else 0
        if hasattr(self, "book_progress") and self.book_progress.winfo_exists():
            self.book_progress.configure(value=pct)
            self.book_progress_text.set(f"Book target progress: {pct}%  ({min(studied_total, target_total)} / {target_total} min)")
        if hasattr(self, "book_log_combo") and self.book_log_combo.winfo_exists():
            self.book_choice_map = {f"{r[1]} | Book {r[2]} - {r[3]}": r[0] for r in rows}
            choices = list(self.book_choice_map.keys())
            self.book_log_combo["values"] = choices
            if self.book_log_choice.get() not in choices:
                self.book_log_choice.set(choices[0] if choices else "")

    def build_log(self):
        self.heading("Log your study", "Record what you planned and what you actually completed.")
        form = self.card(self.content, 22, 20)
        form.pack(anchor="nw", fill="x")
        self.log_subject = tk.StringVar()
        self.log_date = tk.StringVar(value=date.today().isoformat())
        self.log_planned = tk.StringVar(value="60")
        self.log_completed = tk.StringVar(value="45")
        self.log_notes = tk.StringVar()
        self.subject_combo = self.add_labeled_field(form, "SUBJECT", ttk.Combobox(
            form, textvariable=self.log_subject, state="readonly", width=35))
        self.add_labeled_field(form, "STUDY DATE (YYYY-MM-DD)", ttk.Entry(form, textvariable=self.log_date, width=38), row=1)
        self.add_labeled_field(form, "PLANNED MINUTES", ttk.Entry(form, textvariable=self.log_planned, width=38), row=2)
        self.add_labeled_field(form, "COMPLETED MINUTES", ttk.Entry(form, textvariable=self.log_completed, width=38), row=3)
        self.add_labeled_field(form, "NOTES (OPTIONAL)", ttk.Entry(form, textvariable=self.log_notes, width=38), row=4)
        tk.Button(form, text="Save study session", command=self.save_session,
                  bg=BLUE, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=18, pady=10, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).grid(row=5, column=1, sticky="w", pady=(18, 0))
        tk.Label(form, text="Missed minutes are calculated automatically when you save.",
                 bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).grid(row=6, column=1, sticky="w", pady=(12, 0))

    def add_labeled_field(self, parent, label, widget, row=0):
        tk.Label(parent, text=label, bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=row, column=0, sticky="w", padx=(0, 25), pady=8)
        widget.grid(row=row, column=1, sticky="w", pady=8)
        return widget

    def build_recovery(self):
        self.heading("Smart recovery planner", "Recover missed time by subject without overloading your day.")
        summary = self.card(self.content, 22, 20)
        summary.pack(fill="x")
        tk.Label(summary, text="TOTAL MISSED TIME IN YOUR STUDY LOG", bg=WHITE,
                 fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.auto_missed_var = tk.StringVar(value="0 minutes")
        tk.Label(summary, textvariable=self.auto_missed_var, bg=WHITE, fg=ORANGE,
                 font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(5, 18))
        tk.Label(summary, text="DAYS REMAINING (AUTO-FILLED FROM EXAM DATE; EDITABLE)", bg=WHITE,
                 fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))
        exam_raw = self.get_setting("exam_date", "")
        default_days = "3"
        if exam_raw:
            try:
                default_days = str(max(1, (date.fromisoformat(exam_raw) - date.today()).days))
            except ValueError:
                pass
        self.days_var = tk.StringVar(value=default_days)
        ttk.Entry(summary, textvariable=self.days_var, width=18).pack(anchor="w")
        tk.Button(summary, text="Calculate my recovery plan", command=self.calculate_recovery,
                  bg=BLUE, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=18, pady=11, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(18, 0))
        self.burnout_label = tk.Label(summary, text="", bg=WHITE, fg="#B34B35",
                                      font=("Segoe UI", 10, "bold"), justify="left", wraplength=760)
        self.burnout_label.pack(anchor="w", pady=(12, 0))
        result = self.card(self.content, 22, 20)
        result.pack(fill="both", expand=True, pady=(16, 0))
        tk.Label(result, text="SUBJECT-WISE DAILY RECOVERY", bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.recovery_result = tk.StringVar(value="Calculate to see each subject's daily recovery target.")
        tk.Label(result, textvariable=self.recovery_result, bg=WHITE, fg=INK,
                 font=("Segoe UI", 11), wraplength=760, justify="left",
                 anchor="nw").pack(anchor="w", fill="both", expand=True, pady=(8, 0))
        self.calculate_recovery(silent=True)

    def build_exam_planner(self):
        self.heading("Exam planner", "Your exam date is optional. Add it whenever your university announces it.")
        card = self.card(self.content, 22, 20)
        card.pack(fill="x")
        tk.Label(card, text="EXAM DATE", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.exam_date_var = tk.StringVar(value=self.get_setting("exam_date", ""))
        ttk.Entry(card, textvariable=self.exam_date_var, width=28).pack(anchor="w", pady=(8, 5))
        tk.Label(card, text="Format: YYYY-MM-DD  |  Leave blank until the date is confirmed.",
                 bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Button(card, text="Save exam date", command=self.save_exam_date,
                  bg=BLUE, fg=WHITE, activebackground=NAVY_2, activeforeground=WHITE,
                  bd=0, padx=16, pady=10, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(16, 12))
        self.exam_countdown_var = tk.StringVar(value="No exam date added yet.")
        tk.Label(card, textvariable=self.exam_countdown_var, bg=WHITE, fg=INK,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(5, 0))
        self.update_exam_countdown()

    def get_setting(self, key, default=""):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def save_exam_date(self):
        raw = self.exam_date_var.get().strip()
        if raw:
            try:
                datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid date", "Please use YYYY-MM-DD, for example 2027-01-15.")
                return
        self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('exam_date', ?)", (raw,))
        self.conn.commit()
        self.update_exam_countdown()
        messagebox.showinfo("Saved", "Exam date saved." if raw else "Exam date cleared.")

    def update_exam_countdown(self):
        if not hasattr(self, "exam_countdown_var"):
            return
        raw = self.get_setting("exam_date", "")
        if not raw:
            self.exam_countdown_var.set("No exam date added yet. You can set it later.")
            return
        days = (date.fromisoformat(raw) - date.today()).days
        if days > 0:
            self.exam_countdown_var.set(f"{days} days until your exam.")
        elif days == 0:
            self.exam_countdown_var.set("Your exam date is today. Best of luck!")
        else:
            self.exam_countdown_var.set(f"That exam date was {-days} days ago.")

    def add_subject(self):
        name = self.subject_entry.get().strip()
        if not name:
            messagebox.showwarning("Subject needed", "Please type a subject name first.")
            return
        try:
            self.conn.execute("INSERT INTO subjects(name) VALUES (?)", (name,))
            self.conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showwarning("Already added", "This subject is already in your list.")
            return
        self.subject_entry.delete(0, "end")
        self.refresh_all()
        messagebox.showinfo("Added", f"{name} was added successfully.")

    def save_session(self):
        subject = self.log_subject.get().strip()
        if not subject:
            messagebox.showwarning("No subject", "Add a subject first in the Subjects page.")
            return
        try:
            study_day = date.fromisoformat(self.log_date.get().strip()).isoformat()
            planned = int(self.log_planned.get())
            completed = int(self.log_completed.get())
            if planned < 0 or completed < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Check your entries", "Use a valid date and non-negative whole minutes.")
            return
        row = self.conn.execute("SELECT id FROM subjects WHERE name=?", (subject,)).fetchone()
        if not row:
            messagebox.showerror("Subject not found", "Please choose a subject from the list.")
            return
        self.conn.execute("INSERT INTO sessions(subject_id, study_date, planned, completed, notes) VALUES (?, ?, ?, ?, ?)",
                          (row[0], study_day, planned, completed, self.log_notes.get().strip()))
        self.conn.commit()
        missed = max(0, planned - completed)
        self.log_notes.set("")
        self.refresh_all()
        messagebox.showinfo("Session saved", f"Your study session was saved. Missed time: {missed} minutes.")

    def calculate_recovery(self, silent=False):
        try:
            days = int(self.days_var.get())
            if days <= 0:
                raise ValueError
        except ValueError:
            if not silent:
                messagebox.showerror("Invalid days", "Days remaining must be a whole number greater than zero.")
            return
        rows = self.conn.execute("""SELECT sub.name,
            COALESCE(SUM(MAX(0, s.planned - s.completed)), 0) AS missed
            FROM subjects sub LEFT JOIN sessions s ON s.subject_id=sub.id
            GROUP BY sub.id, sub.name ORDER BY missed DESC, sub.name ASC""").fetchall()
        rows = [(name, int(missed or 0), ceil(int(missed or 0) / days) if missed else 0)
                for name, missed in rows if int(missed or 0) > 0]
        total_missed = sum(r[1] for r in rows)
        total_daily = sum(r[2] for r in rows)
        self.auto_missed_var.set(f"{total_missed} minutes")
        if rows:
            lines = [f"{name}: +{daily} min/day  (missed: {missed} min)"
                     for name, missed, daily in rows]
            lines.append("")
            lines.append(f"TOTAL: +{total_daily} extra minutes/day for {days} days")
            lines.append(f"Scheduled recovery: {total_daily * days} min | Original missed: {total_missed} min")
            self.recovery_result.set("\n".join(lines))
        else:
            self.recovery_result.set("No missed study time found. Great work — keep going!")
        if hasattr(self, "burnout_label") and self.burnout_label.winfo_exists():
            if total_daily > 180:
                self.burnout_label.configure(
                    text=f"⚠ OVERLOAD ALERT: {total_daily} extra min/day is above 180 minutes (3 hours). Prioritize high-weightage topics and avoid burnout.",
                    fg="#B34B35")
            else:
                self.burnout_label.configure(text="Daily recovery target is within the 3-hour alert threshold.",
                                              fg=TEAL)

    def get_missed_total(self):
        row = self.conn.execute("SELECT COALESCE(SUM(MAX(0, planned - completed)), 0) FROM sessions").fetchone()
        return int(row[0] or 0)

    def refresh_all(self):
        subjects = self.conn.execute("SELECT id, name FROM subjects ORDER BY name").fetchall()
        if hasattr(self, "subject_tree") and self.subject_tree.winfo_exists():
            for item in self.subject_tree.get_children():
                self.subject_tree.delete(item)
            for row in subjects:
                self.subject_tree.insert("", "end", iid=str(row[0]), values=row)
        if hasattr(self, "subject_combo") and self.subject_combo.winfo_exists():
            names = [r[1] for r in subjects]
            self.subject_combo["values"] = names
            if names and self.log_subject.get() not in names:
                self.log_subject.set(names[0])
        totals = self.conn.execute("SELECT COALESCE(SUM(planned),0), COALESCE(SUM(completed),0) FROM sessions").fetchone()
        missed = self.get_missed_total()
        if hasattr(self, "subject_count_var"):
            self.subject_count_var.set(str(len(subjects)))
            self.planned_total_var.set(f"{totals[0]} min")
            self.completed_total_var.set(f"{totals[1]} min")
            self.missed_total_var.set(f"{missed} min")
            if hasattr(self, "study_progress") and self.study_progress.winfo_exists():
                pct = min(100, round((totals[1] / totals[0]) * 100)) if totals[0] else 0
                self.study_progress.configure(value=pct)
                self.study_progress_text.set(f"{pct}%")
        if hasattr(self, "auto_missed_var"):
            self.auto_missed_var.set(f"{missed} minutes")
        if (hasattr(self, "days_var") and hasattr(self, "recovery_result")
                and hasattr(self, "burnout_label") and self.burnout_label.winfo_exists()):
            self.calculate_recovery(silent=True)
        if hasattr(self, "books_tree") and self.books_tree.winfo_exists():
            self.refresh_books_tracker()
        if hasattr(self, "recent_tree") and self.recent_tree.winfo_exists():
            for item in self.recent_tree.get_children():
                self.recent_tree.delete(item)
            recent = self.conn.execute("""SELECT s.id, s.study_date, sub.name, s.planned, s.completed,
                MAX(0, s.planned-s.completed) FROM sessions s
                JOIN subjects sub ON sub.id=s.subject_id
                ORDER BY s.study_date DESC, s.id DESC LIMIT 12""").fetchall()
            for row in recent:
                self.recent_tree.insert("", "end", iid=str(row[0]), values=row[1:])

    def delete_selected_session(self):
        selected = self.recent_tree.selection() if hasattr(self, "recent_tree") else ()
        if not selected:
            messagebox.showwarning("Nothing selected", "Select a study session from the table first.")
            return
        if not messagebox.askyesno("Confirm delete", "Delete the selected study session permanently?"):
            return
        self.conn.executemany("DELETE FROM sessions WHERE id=?", [(int(item),) for item in selected])
        self.conn.commit()
        self.refresh_all()

    def delete_selected_subject(self):
        selected = self.subject_tree.selection() if hasattr(self, "subject_tree") else ()
        if not selected:
            messagebox.showwarning("Nothing selected", "Select a subject from the table first.")
            return
        if not messagebox.askyesno("Confirm delete", "Delete selected subject(s) and their study sessions/books? This cannot be undone."):
            return
        ids = [int(item) for item in selected]
        self.conn.executemany("DELETE FROM book_study_logs WHERE book_id IN (SELECT id FROM books WHERE subject_id=?)", [(sid,) for sid in ids])
        self.conn.executemany("DELETE FROM books WHERE subject_id=?", [(sid,) for sid in ids])
        self.conn.executemany("DELETE FROM sessions WHERE subject_id=?", [(sid,) for sid in ids])
        self.conn.executemany("DELETE FROM subjects WHERE id=?", [(sid,) for sid in ids])
        self.conn.commit()
        self.refresh_all()

    def delete_selected_book(self):
        selected = self.books_tree.selection() if hasattr(self, "books_tree") else ()
        if not selected:
            messagebox.showwarning("Nothing selected", "Select a book from the table first.")
            return
        if not messagebox.askyesno("Confirm delete", "Delete the selected book and all its study-minute logs?"):
            return
        self.conn.executemany("DELETE FROM books WHERE id=?", [(int(item),) for item in selected])
        self.conn.commit()
        self.refresh_books_tracker()

    def load_demo_data(self):
        if self.get_setting("demo_data_loaded", "") == "1":
            messagebox.showinfo("Demo data already loaded", "Demo data has already been added once. No duplicates were created.")
            return
        if not messagebox.askyesno("Load Hackathon Demo", "Add 4 sample subjects, 2 textbooks, 6 study sessions, and an exam date 5 days from today? Existing records will be kept."):
            return
        demo_subjects = ["Programming Fundamentals", "Calculus", "Applied Physics", "ICT"]
        demo_ids = {}
        try:
            with self.conn:
                for name in demo_subjects:
                    self.conn.execute("INSERT OR IGNORE INTO subjects(name) VALUES (?)", (name,))
                    demo_ids[name] = self.conn.execute("SELECT id FROM subjects WHERE name=?", (name,)).fetchone()[0]
                demo_books = [
                    (demo_ids["Programming Fundamentals"], "C++ Programming Fundamentals", 240),
                    (demo_ids["Calculus"], "Calculus and Analytical Geometry", 300),
                ]
                for sid, title, target in demo_books:
                    already = self.conn.execute(
                        "SELECT id FROM books WHERE subject_id=? AND book_name=?", (sid, title)
                    ).fetchone()
                    if not already:
                        used = {r[0] for r in self.conn.execute(
                            "SELECT book_no FROM books WHERE subject_id=?", (sid,)
                        ).fetchall()}
                        available = next((n for n in range(1, 6) if n not in used), None)
                        if available is not None:
                            self.conn.execute(
                                "INSERT INTO books(subject_id, book_no, book_name, target_minutes) VALUES (?, ?, ?, ?)",
                                (sid, available, title, target)
                            )
                sample_sessions = [
                    ("Programming Fundamentals", 90, 60, "Practiced variables and input/output"),
                    ("Calculus", 75, 45, "Solved limits practice"),
                    ("Applied Physics", 60, 50, "Reviewed vectors"),
                    ("ICT", 50, 50, "Read computer fundamentals"),
                    ("Programming Fundamentals", 80, 40, "Practiced conditional statements"),
                    ("Calculus", 70, 35, "Worked on functions"),
                ]
                for index, (subject, planned, completed, notes) in enumerate(sample_sessions, start=1):
                    study_day = (date.today() - timedelta(days=index)).isoformat()
                    self.conn.execute("INSERT INTO sessions(subject_id, study_date, planned, completed, notes) VALUES (?, ?, ?, ?, ?)",
                                      (demo_ids[subject], study_day, planned, completed, notes))
                exam_day = (date.today() + timedelta(days=5)).isoformat()
                self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('exam_date', ?)", (exam_day,))
                self.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('demo_data_loaded', '1')")
        except sqlite3.Error as exc:
            messagebox.showerror("Demo data error", f"Could not load demo data: {exc}")
            return
        self.refresh_all()
        messagebox.showinfo("Demo data loaded", "Hackathon demo data added successfully. The demo button is protected against duplicate inserts.")

    def close(self):
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PlanBApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
