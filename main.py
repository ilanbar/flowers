import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import shutil
import socket
import sys
import pandas as pd
from datetime import datetime
from collections import defaultdict

# Ensure we are working in the script's/executable's directory
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    # However, for persistent data, we want the folder where the EXE is, 
    # not the temp _MEIPASS folder.
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)

def ensure_data_files():
    """
    If running as a frozen exe, check if data files exist in the local directory.
    If not, copy them from the temporary bundle directory (_MEIPASS).
    """
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        files_to_ensure = ["Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx"]
        
        for filename in files_to_ensure:
            dest_path = os.path.join(application_path, filename)
            if not os.path.exists(dest_path):
                src_path = os.path.join(bundle_dir, filename)
                if os.path.exists(src_path):
                    try:
                        shutil.copy2(src_path, dest_path)
                    except Exception as e:
                        print(f"Failed to extract {filename}: {e}")

ensure_data_files()

from flower import FlowersTypes, FlowerColors, FlowerSizes, FlowerData
from bouquet import Bouquet, load_all_bouquets
try:
    from drive_sync import DriveSync
    DRIVE_SYNC_AVAILABLE = True
except ImportError:
    DRIVE_SYNC_AVAILABLE = False

class FlowerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("מנהל חנות פרחים")
        
        # Handle Window Close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Drive Sync
        self.drive_sync = None
        if DRIVE_SYNC_AVAILABLE:
            self.drive_sync = DriveSync(application_path)

        # Increase font size
        default_font = ('Helvetica', 12)
        self.root.option_add('*Font', default_font)
        style = ttk.Style()
        style.configure('.', font=default_font)
        
        self.flower_types = FlowersTypes()
        self.flower_colors = FlowerColors()
        self.flower_sizes = FlowerSizes()
        
        self.displayed_flowers = [] # Keep track of flowers displayed in listbox
        
        self.current_order = []
        self.current_prices = {} # Store price per flower type
        self.default_prices = {} # Store default prices
        self.load_default_prices()
        
        self.tab_images = [] # Keep references to images

        self.create_menu()

        # Toolbar
        self.toolbar = ttk.Frame(root)
        self.toolbar.pack(fill='x', padx=10, pady=5)
        
        self.show_config_var = tk.BooleanVar(value=True)
        self.show_config_chk = ttk.Checkbutton(self.toolbar, text="הצג לשוניות הגדרה", variable=self.show_config_var, command=self.toggle_right_pane)
        self.show_config_chk.pack(side='right')

        # Split Layout
        self.main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned.pack(expand=True, fill='both', padx=10, pady=10)

        self.left_notebook = ttk.Notebook(self.main_paned)
        self.main_paned.add(self.left_notebook, weight=1)

        self.right_notebook = ttk.Notebook(self.main_paned)
        self.main_paned.add(self.right_notebook, weight=2)

        # Bind tab changes
        self.left_notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.right_notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        
        self.create_orders_tab()
        self.create_quantities_tab()
        self.create_order_pricing_tab()
        self.create_summary_tab()
        self.create_bouquets_tab()
        self.create_flowers_tab()
        self.create_colors_tab()
        self.create_global_pricing_tab()
        
        if self.drive_sync:
            self.perform_startup_sync()
            
    def toggle_right_pane(self):
        if self.show_config_var.get():
            self.main_paned.add(self.right_notebook, weight=2)
        else:
            self.main_paned.forget(self.right_notebook)
        
    def perform_startup_sync(self):
        if not os.path.exists(os.path.join(application_path, 'credentials.json')):
            return

        if messagebox.askyesno("סנכרון Google Drive", "האם ברצונך להוריד את הנתונים העדכניים מ-Google Drive?"):
            try:
                files_to_sync = ["Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx"]
                self.drive_sync.download_files(files_to_sync)
                self.reload_data()
                #messagebox.showinfo("Sync", "Download complete. Loading data...")
            except Exception as e:
                messagebox.showerror("שגיאת סנכרון", f"נכשל בהורדה מ-Drive: {e}")

    def sync_to_drive(self):
        if self.drive_sync and os.path.exists(os.path.join(application_path, 'credentials.json')):
            if messagebox.askyesno("סנכרון Google Drive", "האם ברצונך להעלות שינויים ל-Google Drive?"):
                try:
                    files_to_sync = ["Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx"]
                    files_to_sync.extend([f for f in os.listdir('.') if f.startswith('DefaultPricing_') and f.endswith('.xlsx')])
                    self.drive_sync.upload_files(files_to_sync)
                    messagebox.showinfo("Sync", "הסנכרון הושלם בהצלחה.")
                except Exception as e:
                    messagebox.showerror("שגיאת סנכרון", f"נכשל בהעלאה ל-Drive: {e}")
        else:
             messagebox.showinfo("סנכרון Google Drive", "סנכרון אינו זמין (חסר credentials.json או drive_sync.py)")

    def on_closing(self):
        if self.drive_sync and os.path.exists(os.path.join(application_path, 'credentials.json')):
            if messagebox.askyesno("סנכרון Google Drive", "האם ברצונך להעלות שינויים ל-Google Drive לפני היציאה?"):
                try:
                    files_to_sync = ["Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx"]
                    files_to_sync.extend([f for f in os.listdir('.') if f.startswith('DefaultPricing_') and f.endswith('.xlsx')])
                    self.drive_sync.upload_files(files_to_sync)
                    # messagebox.showinfo("Sync", "Upload complete.")
                except Exception as e:
                    messagebox.showerror("שגיאת סנכרון", f"נכשל בהעלאה ל-Drive: {e}")
        
        self.root.destroy()

    def load_default_prices(self):
        self.default_prices = {}
        if os.path.exists("DefaultPricing.xlsx"):
            try:
                df = pd.read_excel("DefaultPricing.xlsx")
                # Expected columns: Flower Name, Size, Price
                for _, row in df.iterrows():
                    key = f"{row['Flower Name']} - {row['Size']}"
                    self.default_prices[key] = float(row['Price'])
            except Exception as e:
                print(f"Error loading DefaultPricing.xlsx: {e}")
        elif os.path.exists("DefaultPricing.json"):
            # Legacy migration (ignoring color)
            try:
                with open("DefaultPricing.json", "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    for key, price in old_data.items():
                        # Old key: Name - Color - Size
                        parts = key.split(' - ')
                        if len(parts) == 3:
                            new_key = f"{parts[0]} - {parts[2]}"
                            self.default_prices[new_key] = float(price)
            except (FileNotFoundError, json.JSONDecodeError):
                self.default_prices = {}
        
        # Load additional pricing files
        for filename in os.listdir('.'):
            if filename.startswith("DefaultPricing_") and filename.endswith(".xlsx"):
                try:
                    df = pd.read_excel(filename)
                    for _, row in df.iterrows():
                        key = f"{row['Flower Name']} - {row['Size']}"
                        self.default_prices[key] = float(row['Price'])
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Ensure file is up to date with all combinations
        self.save_default_prices()

    def save_default_prices(self):
        data = []
        # Iterate through all defined flowers to ensure complete list
        for f_name in sorted(self.flower_types.flowers):
            config = self.flower_types.get_config(f_name)
            valid_sizes = config.get('sizes', [])
            
            # If no specific sizes defined, use all available sizes
            if not valid_sizes:
                valid_sizes = self.flower_sizes.sizes
                
            for f_size in valid_sizes:
                key = f"{f_name} - {f_size}"
                price = self.default_prices.get(key, 0.0)
                
                data.append({
                    "Flower Name": f_name,
                    "Size": f_size,
                    "Price": price
                })
        
        df = pd.DataFrame(data, columns=["Flower Name", "Size", "Price"])
        try:
            df.to_excel("DefaultPricing.xlsx", index=False)
        except Exception as e:
            messagebox.showerror("שגיאה", f"שגיאה בשמירת מחירי ברירת מחדל: {e}")

    def create_tab_image(self, color):
        img = tk.PhotoImage(width=20, height=20)
        img.put(color, to=(0, 0, 20, 20))
        self.tab_images.append(img)
        return img

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="קובץ", menu=file_menu)
        file_menu.add_command(label="Sync to Drive", command=self.sync_to_drive)
        file_menu.add_command(label="הורד גירסה", command=self.download_new_version)
        file_menu.add_separator()
        file_menu.add_command(label="יציאה", command=self.root.quit)

    def download_new_version(self):
        if not self.drive_sync:
             messagebox.showerror("שגיאה", "סנכרון אינו זמין.")
             return

        if messagebox.askyesno("הורד גירסה", "האם להוריד גירסה חדשה מ-Google Drive?"):
            try:
                success = self.drive_sync.download_file_as("FlowerShopManager.exe", "FlowerShopManager_new.exe")
                if success:
                    messagebox.showinfo("הצלחה", "הגירסה החדשה הורדה כ-FlowerShopManager_new.exe.\nיש לסגור את התוכנה ולהחליף את הקובץ.")
                else:
                    messagebox.showerror("שגיאה", "הקובץ FlowerShopManager.exe לא נמצא ב-Drive.")
            except Exception as e:
                messagebox.showerror("שגיאה", f"נכשל בהורדה: {e}")

    def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_dir = os.path.join("backups", timestamp)
            os.makedirs(backup_dir, exist_ok=True)
            
            files_to_backup = ["Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx"]
            for filename in files_to_backup:
                if os.path.exists(filename):
                    shutil.copy2(filename, backup_dir)
            
            #messagebox.showinfo("גיבוי", f"גיבוי נוצר בהצלחה ב:\n{backup_dir}")
        except Exception as e:
            messagebox.showerror("שגיאת גיבוי", f"נכשל ביצירת גיבוי: {e}")

    def restore_backup_dialog(self):
        if not os.path.exists("backups"):
            messagebox.showinfo("שחזור", "לא נמצאו גיבויים.")
            return

        # Get list of backups (directories)
        backups = [d for d in os.listdir("backups") if os.path.isdir(os.path.join("backups", d))]
        backups.sort(reverse=True) # Newest first
        
        if not backups:
            messagebox.showinfo("שחזור", "לא נמצאו גיבויים.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("שחזר גיבוי")
        dialog.geometry("300x400")
        
        tk.Label(dialog, text="בחר גיבוי לשחזור:").pack(pady=5)
        
        listbox = tk.Listbox(dialog)
        listbox.pack(expand=True, fill='both', padx=10, pady=5)
        
        for b in backups:
            listbox.insert(tk.END, b)
            
        def do_restore():
            selection = listbox.curselection()
            if not selection:
                return
            
            backup_name = listbox.get(selection[0])
            backup_path = os.path.join("backups", backup_name)
            
            if messagebox.askyesno("אשר שחזור", f"האם אתה בטוח שברצונך לשחזר מ-'{backup_name}'?\nהנתונים הנוכחיים יוחלפו."):
                try:
                    files_to_restore = ["Flowers.xlsx", "Colors.xlsx", "Bouquets.xlsx", "DefaultPricing.xlsx"]
                    for filename in files_to_restore:
                        src = os.path.join(backup_path, filename)
                        if os.path.exists(src):
                            shutil.copy2(src, filename)
                    
                    self.reload_data()
                    messagebox.showinfo("שחזור", "הנתונים שוחזרו בהצלחה.")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("שגיאת שחזור", f"נכשל בשחזור: {e}")

        tk.Button(dialog, text="שחזר", command=do_restore).pack(pady=10)

    def reload_data(self):
        self.flower_types = FlowersTypes()
        self.flower_colors = FlowerColors()
        self.load_default_prices()
        # self.flower_sizes is static, no need to reload
        
        self.refresh_flowers_list()
        self.refresh_colors_list()
        self.refresh_bouquets_list()
        self.refresh_global_pricing_tab()

    def create_flowers_tab(self):
        frame = ttk.Frame(self.right_notebook)
        img = self.create_tab_image('lightblue')
        self.right_notebook.add(frame, text="פרחים", image=img, compound='left')
        
        # List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.flowers_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.flowers_listbox.pack(side='left', expand=True, fill='both')
        self.flowers_listbox.bind('<Double-1>', self.open_flower_editor)
        scrollbar.config(command=self.flowers_listbox.yview)
        
        self.refresh_flowers_list()
        
        # Controls
        controls = ttk.Frame(frame)
        controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(controls, text="שם:").pack(side='left')
        self.flower_entry = ttk.Entry(controls)
        self.flower_entry.pack(side='left', expand=True, fill='x', padx=5)
        
        add_btn = ttk.Button(controls, text="הוסף", command=self.add_flower)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(controls, text="מחק", command=self.delete_flower)
        del_btn.pack(side='left', padx=5)

        load_btn = ttk.Button(controls, text="טען פרחים", command=self.load_flowers_from_file)
        load_btn.pack(side='left', padx=5)

    def load_flowers_from_file(self):
        file_path = filedialog.askopenfilename(
            title="בחר קובץ פרחים",
            filetypes=[("קבצי Excel/JSON", "*.xlsx *.json"), ("קבצי Excel", "*.xlsx"), ("קבצי JSON", "*.json")]
        )
        if not file_path:
            return

        try:
            new_flowers = {}
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path)
                # Expected columns: Name, Sizes (optional)
                if "Name" not in df.columns:
                     # Try "Flower Name" or just first column?
                     if "Flower Name" in df.columns:
                         df.rename(columns={"Flower Name": "Name"}, inplace=True)
                     else:
                         # Fallback: assume first column is Name
                         df.rename(columns={df.columns[0]: "Name"}, inplace=True)
                
                for _, row in df.iterrows():
                    name = str(row['Name']).strip()
                    if not name: continue
                    
                    sizes = []
                    if "Sizes" in df.columns and pd.notna(row['Sizes']):
                        sizes = [s.strip() for s in str(row['Sizes']).split(',') if s.strip()]
                    
                    new_flowers[name] = {'colors': [], 'sizes': sizes}

            elif file_path.lower().endswith('.json'):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # List of strings
                        for name in data:
                            new_flowers[name] = {'colors': [], 'sizes': []}
                    elif isinstance(data, dict):
                        # Dict of configs
                        for name, config in data.items():
                            sizes = config.get('sizes', [])
                            new_flowers[name] = {'colors': [], 'sizes': sizes}
            
            if new_flowers:
                # Merge
                added_count = 0
                updated_count = 0
                for name, config in new_flowers.items():
                    if name not in self.flower_types.flowers:
                        self.flower_types.flowers[name] = config
                        added_count += 1
                    else:
                        # Merge sizes
                        existing_sizes = set(self.flower_types.flowers[name].get('sizes', []))
                        new_sizes = set(config.get('sizes', []))
                        if new_sizes - existing_sizes: # If there are new sizes
                            combined = list(existing_sizes.union(new_sizes))
                            self.flower_types.flowers[name]['sizes'] = combined
                            updated_count += 1
                
                self.flower_types._save()
                self.refresh_flowers_list()
                messagebox.showinfo("הצלחה", f"הקובץ עובד.\nנוספו: {added_count} פרחים חדשים.\nעודכנו: {updated_count} פרחים קיימים.")
            else:
                messagebox.showwarning("אזהרה", "לא נמצאו פרחים בקובץ.")

        except Exception as e:
            messagebox.showerror("שגיאה", f"נכשל בטעינת פרחים: {e}")

    def open_flower_editor(self, event):
        selection = self.flowers_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if idx < len(self.displayed_flowers):
            name = self.displayed_flowers[idx]
        else:
            return
        
        editor = tk.Toplevel(self.root)
        editor.title(f"ערוך פרח: {name}")
        editor.geometry("400x400")
        
        config = self.flower_types.get_config(name)
        current_sizes = set(config.get('sizes', []))
        
        # Sizes
        size_frame = ttk.LabelFrame(editor, text="גדלים מותרים")
        size_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        size_listbox = tk.Listbox(size_frame, selectmode=tk.MULTIPLE, exportselection=False)
        size_listbox.pack(fill='both', expand=True)
        
        all_sizes = self.flower_sizes.sizes
        for i, s in enumerate(all_sizes):
            size_listbox.insert(tk.END, s)
            # If empty, select all (default)
            if not current_sizes or s in current_sizes:
                size_listbox.selection_set(i)
                
        def save_config():
            selected_sizes = [size_listbox.get(i) for i in size_listbox.curselection()]
            
            self.flower_types.update_config(name, selected_sizes)
            messagebox.showinfo("הצלחה", f"הגדרות עודכנו עבור {name}")
            self.refresh_flowers_list() # Refresh list to show new config
            editor.destroy()
            
        ttk.Button(editor, text="שמור", command=save_config).pack(pady=10)

    def refresh_flowers_list(self):
        if not hasattr(self, 'flowers_listbox'):
            return
        self.flowers_listbox.delete(0, tk.END)
        self.displayed_flowers = sorted(self.flower_types.flowers)
        for f in self.displayed_flowers:
            config = self.flower_types.get_config(f)
            sizes = config.get('sizes', [])
            
            size_str = ",".join(sizes) if sizes else "הכל"
            
            display_text = f"{f} (גדלים: {size_str})"
            self.flowers_listbox.insert(tk.END, display_text)

    def add_flower(self):
        name = self.flower_entry.get().strip()
        if name:
            if self.flower_types.contains(name):
                messagebox.showwarning("אזהרה", f"פרח '{name}' כבר קיים.")
                return
            self.flower_types.add(name)
            self.flower_entry.delete(0, tk.END)
            self.refresh_flowers_list()

    def delete_flower(self):
        selection = self.flowers_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.displayed_flowers):
                name = self.displayed_flowers[idx]
                if messagebox.askyesno("אישור", f"למחוק את הפרח '{name}'?"):
                    self.flower_types.remove(name)
                    self.refresh_flowers_list()

    def create_colors_tab(self):
        frame = ttk.Frame(self.right_notebook)
        img = self.create_tab_image('lightgreen')
        self.right_notebook.add(frame, text="צבעים", image=img, compound='left')
        
        # List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.colors_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.colors_listbox.pack(side='left', expand=True, fill='both')
        scrollbar.config(command=self.colors_listbox.yview)
        
        self.refresh_colors_list()
        
        # Controls
        controls = ttk.Frame(frame)
        controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(controls, text="צבע:").pack(side='left')
        self.color_entry = ttk.Entry(controls)
        self.color_entry.pack(side='left', expand=True, fill='x', padx=5)
        
        add_btn = ttk.Button(controls, text="הוסף", command=self.add_color)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(controls, text="מחק", command=self.delete_color)
        del_btn.pack(side='left', padx=5)

    def refresh_colors_list(self):
        if not hasattr(self, 'colors_listbox'):
            return
        self.colors_listbox.delete(0, tk.END)
        for c in sorted(self.flower_colors.colors):
            self.colors_listbox.insert(tk.END, c)

    def add_color(self):
        color = self.color_entry.get().strip()
        if color:
            if color in self.flower_colors.colors:
                messagebox.showwarning("אזהרה", f"צבע '{color}' כבר קיים.")
                return
            self.flower_colors.add(color)
            self.color_entry.delete(0, tk.END)
            self.refresh_colors_list()

    def delete_color(self):
        selection = self.colors_listbox.curselection()
        if selection:
            color = self.colors_listbox.get(selection[0])
            if messagebox.askyesno("אישור", f"למחוק את הצבע '{color}'?"):
                self.flower_colors.remove(color)
                self.refresh_colors_list()

    def create_bouquets_tab(self):
        frame = ttk.Frame(self.right_notebook)
        img = self.create_tab_image('lightyellow')
        self.right_notebook.add(frame, text="זרים", image=img, compound='left')
        
        # List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.bouquets_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.bouquets_listbox.pack(side='left', expand=True, fill='both')
        self.bouquets_listbox.bind('<Double-1>', self.open_bouquet_editor)
        scrollbar.config(command=self.bouquets_listbox.yview)
        
        # Controls
        controls = ttk.Frame(frame)
        controls.pack(fill='x', padx=5, pady=5)
        
        # Row 1: Inputs
        input_frame = ttk.Frame(controls)
        input_frame.pack(fill='x', pady=2)
        
        ttk.Label(input_frame, text="שם:").pack(side='left')
        self.bouquet_name_entry = ttk.Entry(input_frame)
        self.bouquet_name_entry.pack(side='left', expand=True, fill='x', padx=5)
        
        ttk.Label(input_frame, text="מבוסס על:").pack(side='left')
        self.based_on_combo = ttk.Combobox(input_frame, state="readonly", width=20)
        self.based_on_combo.pack(side='left', padx=5)
        
        # Row 2: Buttons
        btn_frame = ttk.Frame(controls)
        btn_frame.pack(fill='x', pady=2)
        
        add_btn = ttk.Button(btn_frame, text="הוסף זר", command=self.add_bouquet)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(btn_frame, text="מחק זר", command=self.delete_bouquet)
        del_btn.pack(side='left', padx=5)
        
        edit_btn = ttk.Button(btn_frame, text="ערוך שם", command=self.edit_bouquet_name)
        edit_btn.pack(side='left', padx=5)

        load_btn = ttk.Button(btn_frame, text="טען זרים", command=self.load_bouquets_from_file)
        load_btn.pack(side='left', padx=5)
        
        self.refresh_bouquets_list()

    def get_bouquet_names(self):
        try:
            all_bouquets = load_all_bouquets()
            return list(all_bouquets.keys())
        except:
            return []

    def refresh_bouquets_list(self):
        if not hasattr(self, 'bouquets_listbox'):
            return
        self.bouquets_listbox.delete(0, tk.END)
        names = sorted(self.get_bouquet_names())
        for name in names:
            self.bouquets_listbox.insert(tk.END, name)
        
        self.based_on_combo['values'] = [""] + names
        self.based_on_combo.set("")

        # Also refresh the order tab dropdown if it exists
        if hasattr(self, 'order_bouquet_combo'):
            self.refresh_order_bouquets()

    def add_bouquet(self):
        name = self.bouquet_name_entry.get().strip()
        based_on = self.based_on_combo.get()
        if not based_on:
            based_on = None
            
        if name:
            try:
                b = Bouquet(name, based_on)
                b.save() # Save the new bouquet
                self.bouquet_name_entry.delete(0, tk.END)
                self.refresh_bouquets_list()
                # messagebox.showinfo("Success", f"Bouquet '{b.name}' created.")
            except ValueError as e:
                messagebox.showerror("שגיאה", str(e))
            except Exception as e:
                messagebox.showerror("שגיאה", f"אירעה שגיאה: {e}")
        else:
            messagebox.showwarning("אזהרה", "נא להזין שם לזר.")

    def delete_bouquet(self):
        selection = self.bouquets_listbox.curselection()
        if selection:
            name = self.bouquets_listbox.get(selection[0])
            if messagebox.askyesno("אישור", f"למחוק את הזר '{name}'?"):
                try:
                    Bouquet.delete_bouquet(name)
                    self.refresh_bouquets_list()
                except Exception as e:
                    messagebox.showerror("שגיאה", str(e))

    def edit_bouquet_name(self):
        selection = self.bouquets_listbox.curselection()
        if selection:
            old_name = self.bouquets_listbox.get(selection[0])
            new_name = simpledialog.askstring("ערוך שם", f"הזן שם חדש עבור '{old_name}':")
            if new_name:
                new_name = new_name.strip()
                if new_name and new_name != old_name:
                    try:
                        Bouquet.rename_bouquet(old_name, new_name)
                        self.refresh_bouquets_list()
                        # messagebox.showinfo("Success", f"Renamed '{old_name}' to '{new_name}'.")
                    except ValueError as e:
                        messagebox.showerror("שגיאה", str(e))
                    except Exception as e:
                        messagebox.showerror("שגיאה", f"אירעה שגיאה: {e}")

    def load_bouquets_from_file(self):
        file_path = filedialog.askopenfilename(
            title="בחר קובץ זרים",
            filetypes=[("קבצי Excel/JSON", "*.xlsx *.json"), ("קבצי Excel", "*.xlsx"), ("קבצי JSON", "*.json")]
        )
        if not file_path:
            return

        try:
            new_bouquets = {}
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path)
                # Expected columns: Bouquet Name, Flower Name, Color, Size, Count
                required_cols = ["Bouquet Name", "Flower Name", "Color", "Size", "Count"]
                
                if not df.empty:
                    # Check if columns exist
                    missing = [col for col in required_cols if col not in df.columns]
                    if missing:
                         raise ValueError(f"Excel file missing columns: {', '.join(missing)}")

                    grouped = df.groupby("Bouquet Name")
                    for name, group in grouped:
                        flowers = []
                        for _, row in group.iterrows():
                            f_name = row["Flower Name"]
                            f_color = row["Color"]
                            f_size = row["Size"]
                            count = int(row["Count"])
                            flower = FlowerData(f_name, f_color, f_size)
                            flowers.extend([flower] * count)
                        new_bouquets[name] = flowers
            elif file_path.lower().endswith('.json'):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, flist in data.items():
                        # flist is list of [name, color, size]
                        new_bouquets[name] = [FlowerData(*f) for f in flist]
            
            if new_bouquets:
                # Merge with existing
                from bouquet import load_all_bouquets, save_all_bouquets
                current_bouquets = load_all_bouquets()
                current_bouquets.update(new_bouquets)
                save_all_bouquets(current_bouquets)
                
                self.refresh_bouquets_list()
                messagebox.showinfo("הצלחה", f"נטענו/מוזגו {len(new_bouquets)} זרים.")
            else:
                messagebox.showwarning("אזהרה", "לא נמצאו זרים בקובץ.")

        except Exception as e:
            messagebox.showerror("שגיאה", f"נכשל בטעינת זרים: {e}")

    def open_bouquet_editor(self, event):
        selection = self.bouquets_listbox.curselection()
        if not selection:
            return
        name = self.bouquets_listbox.get(selection[0])
        
        try:
            bouquet = Bouquet(name, load_existing=True)
        except Exception as e:
            messagebox.showerror("שגיאה", f"שגיאה בטעינת הזר: {e}")
            return

        editor = tk.Toplevel(self.root)
        editor.title(f"ערוך זר: {name}")
        # Auto-size to fit contents
        
        # Left: List of flowers
        list_frame = ttk.LabelFrame(editor, text="פרחים בזר")
        list_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        flowers_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=40, exportselection=False)
        flowers_list.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=flowers_list.yview)
        
        current_display_items = []

        def refresh_list():
            nonlocal current_display_items
            flowers_list.delete(0, tk.END)
            current_display_items = []
            counts = bouquet.flower_count()
            for flower, count in counts.items():
                flowers_list.insert(tk.END, f"{flower.name} - {flower.color} - {flower.size} (x{count})")
                current_display_items.append(flower)
                
        refresh_list()
        
        # Right: Controls
        controls_frame = ttk.Frame(editor)
        controls_frame.pack(side='right', fill='y', padx=10, pady=10)
        
        # Add Flower Section
        add_frame = ttk.LabelFrame(controls_frame, text="הוסף פרח")
        add_frame.pack(fill='x', pady=5)
        
        ttk.Label(add_frame, text="סוג:").pack(anchor='w', padx=5)
        type_combo = ttk.Combobox(add_frame, values=sorted(self.flower_types.flowers), state="readonly")
        type_combo.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(add_frame, text="צבע:").pack(anchor='w', padx=5)
        color_combo = ttk.Combobox(add_frame, values=sorted(self.flower_colors.colors), state="readonly")
        color_combo.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(add_frame, text="גודל:").pack(anchor='w', padx=5)
        size_combo = ttk.Combobox(add_frame, values=self.flower_sizes.sizes, state="readonly")
        size_combo.pack(fill='x', padx=5, pady=2)
        
        def update_add_combos(event=None):
            f_name = type_combo.get()
            if not f_name: return
            
            config = self.flower_types.get_config(f_name)
            valid_sizes = config.get('sizes', [])
            
            # Colors are now unrestricted per flower type
            valid_colors = sorted(self.flower_colors.colors)
            
            if not valid_sizes: valid_sizes = self.flower_sizes.sizes
            
            color_combo['values'] = valid_colors
            size_combo['values'] = valid_sizes
            
            color_combo.set('')
            size_combo.set('')
            
        type_combo.bind('<<ComboboxSelected>>', update_add_combos)
        
        ttk.Label(add_frame, text="כמות:").pack(anchor='w', padx=5)
        count_spin = ttk.Spinbox(add_frame, from_=1, to=100, width=5)
        count_spin.set(1)
        count_spin.pack(anchor='w', padx=5, pady=2)
        
        def add_flower():
            f_name = type_combo.get()
            f_color = color_combo.get()
            f_size = size_combo.get()
            try:
                count = int(count_spin.get())
            except ValueError:
                count = 1
            
            if f_name and f_color and f_size:
                flower = FlowerData(f_name, f_color, f_size)
                bouquet.select_flower(flower, count)
                refresh_list()
            else:
                messagebox.showwarning("אזהרה", "נא לבחור סוג, צבע וגודל.")
        
        ttk.Button(add_frame, text="הוסף", command=add_flower).pack(fill='x', padx=5, pady=5)
        
        def remove_flower_action():
            selection = flowers_list.curselection()
            if selection:
                idx = selection[0]
                flower = current_display_items[idx]
                bouquet.remove_flower(flower, count=1)
                refresh_list()
        
        ttk.Button(controls_frame, text="הסר נבחרים (1)", command=remove_flower_action).pack(fill='x', pady=5)
        
        # Edit Quantity Section
        edit_frame = ttk.LabelFrame(controls_frame, text="ערוך כמות")
        edit_frame.pack(fill='x', pady=5)
        
        edit_qty_spin = ttk.Spinbox(edit_frame, from_=1, to=100, width=5)
        edit_qty_spin.pack(side='left', padx=5, pady=5)
        
        def update_quantity():
            selection = flowers_list.curselection()
            if not selection:
                messagebox.showwarning("אזהרה", "אנא בחר פרח לעדכון.")
                return
            
            idx = selection[0]
            flower = current_display_items[idx]
            
            try:
                new_qty = int(edit_qty_spin.get())
            except ValueError:
                messagebox.showwarning("אזהרה", "כמות לא תקינה.")
                return
                
            if new_qty < 1:
                messagebox.showwarning("אזהרה", "הכמות חייבת להיות לפחות 1.")
                return

            current_counts = bouquet.flower_count()
            current_qty = current_counts.get(flower, 0)
            
            if new_qty > current_qty:
                bouquet.select_flower(flower, count=new_qty - current_qty)
            elif new_qty < current_qty:
                bouquet.remove_flower(flower, count=current_qty - new_qty)
            
            refresh_list()
            
        ttk.Button(edit_frame, text="עדכן", command=update_quantity).pack(side='left', fill='x', expand=True, padx=5, pady=5)

        # Edit Details Section
        edit_details_frame = ttk.LabelFrame(controls_frame, text="ערוך פרטים")
        edit_details_frame.pack(fill='x', pady=5)
        
        ttk.Label(edit_details_frame, text="צבע:").pack(anchor='w', padx=5)
        edit_color_combo = ttk.Combobox(edit_details_frame, values=sorted(self.flower_colors.colors), state="readonly")
        edit_color_combo.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(edit_details_frame, text="גודל:").pack(anchor='w', padx=5)
        edit_size_combo = ttk.Combobox(edit_details_frame, values=self.flower_sizes.sizes, state="readonly")
        edit_size_combo.pack(fill='x', padx=5, pady=2)
        
        def update_details():
            selection = flowers_list.curselection()
            if not selection:
                messagebox.showwarning("אזהרה", "אנא בחר פרח לעדכון.")
                return
            
            idx = selection[0]
            old_flower = current_display_items[idx]
            
            new_color = edit_color_combo.get()
            new_size = edit_size_combo.get()
            
            if not new_color or not new_size:
                 messagebox.showwarning("אזהרה", "אנא בחר צבע וגודל.")
                 return

            if new_color == old_flower.color and new_size == old_flower.size:
                return # No change

            # Create new flower data
            new_flower = FlowerData(old_flower.name, new_color, new_size)
            
            # Get count
            counts = bouquet.flower_count()
            count = counts.get(old_flower, 0)
            
            # Remove old
            bouquet.remove_flower(old_flower, count)
            
            # Add new
            bouquet.select_flower(new_flower, count)
            
            refresh_list()
            
        ttk.Button(edit_details_frame, text="עדכן פרטים", command=update_details).pack(fill='x', padx=5, pady=5)

        def on_flower_select(event):
            selection = flowers_list.curselection()
            if selection:
                idx = selection[0]
                flower = current_display_items[idx]
                counts = bouquet.flower_count()
                qty = counts.get(flower, 0)
                edit_qty_spin.set(qty)
                
                # Update values based on flower type
                config = self.flower_types.get_config(flower.name)
                valid_sizes = config.get('sizes', [])
                
                # Colors are unrestricted
                valid_colors = sorted(self.flower_colors.colors)
                
                if not valid_sizes: valid_sizes = self.flower_sizes.sizes
                
                edit_color_combo['values'] = valid_colors
                edit_size_combo['values'] = valid_sizes
                
                # Set combos
                edit_color_combo.set(flower.color)
                edit_size_combo.set(flower.size)
        
        flowers_list.bind('<<ListboxSelect>>', on_flower_select)
        
        def save_bouquet():
            bouquet.save()
            # messagebox.showinfo("הצלחה", "הזר נשמר.")
            
        ttk.Button(controls_frame, text="שמור שינויים", command=save_bouquet).pack(fill='x', pady=20)

    def create_orders_tab(self):
        frame = ttk.Frame(self.left_notebook)
        img = self.create_tab_image('darkorange')
        self.left_notebook.add(frame, text="הזמנה", image=img, compound='left')
        
        # Controls
        controls = ttk.Frame(frame)
        controls.pack(fill='x', padx=5, pady=5)
        
        # Configure grid columns to expand evenly
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        # Row 0: Bouquet Selection
        ttk.Label(controls, text="זר:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.order_bouquet_combo = ttk.Combobox(controls, state="readonly")
        self.order_bouquet_combo.grid(row=0, column=1, columnspan=3, sticky='ew', padx=5, pady=2)
        
        # Row 1: Quantity and Add
        ttk.Label(controls, text="כמות:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.order_qty_spin = ttk.Spinbox(controls, from_=1, to=100, width=5)
        self.order_qty_spin.set(1)
        self.order_qty_spin.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        add_btn = ttk.Button(controls, text="הוסף להזמנה", command=self.add_to_order)
        add_btn.grid(row=1, column=2, columnspan=2, sticky='ew', padx=5, pady=2)
        
        # Row 2: Edit Actions
        update_btn = ttk.Button(controls, text="עדכן כמות", command=self.update_order_quantity)
        update_btn.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=2)
        
        del_btn = ttk.Button(controls, text="הסר נבחרים", command=self.remove_from_order)
        del_btn.grid(row=2, column=2, columnspan=2, sticky='ew', padx=5, pady=2)
        
        # Row 3: File Actions
        save_btn = ttk.Button(controls, text="שמור הזמנה", command=self.save_order)
        save_btn.grid(row=3, column=0, columnspan=2, sticky='ew', padx=5, pady=2)
        
        load_btn = ttk.Button(controls, text="טען הזמנה", command=self.load_order)
        load_btn.grid(row=3, column=2, columnspan=2, sticky='ew', padx=5, pady=2)
        
        # Configure columns to share width
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)
        controls.columnconfigure(3, weight=1)
        
        # Order List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.order_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, exportselection=False)
        self.order_listbox.pack(side='left', expand=True, fill='both')
        self.order_listbox.bind('<<ListboxSelect>>', self.on_order_select)
        scrollbar.config(command=self.order_listbox.yview)
        
    def on_tab_change(self, event):
        # Check if the selected tab is "Order"
        try:
            notebook = event.widget
            selected_tab = notebook.select()
            tab_text = notebook.tab(selected_tab, "text")
            if tab_text == "הזמנה":
                self.refresh_order_bouquets()
            elif tab_text == "כמויות":
                self.refresh_quantities()
            elif tab_text == "תמחור הזמנה":
                self.refresh_order_pricing_tab()
            elif tab_text == "סיכום":
                self.refresh_summary_tab()
            elif tab_text == "מחירון":
                self.refresh_global_pricing_tab()
        except:
            pass

    def refresh_order_bouquets(self):
        names = sorted(self.get_bouquet_names())
        self.order_bouquet_combo['values'] = names
        if names:
            if self.order_bouquet_combo.get() not in names:
                self.order_bouquet_combo.current(0)
        else:
            self.order_bouquet_combo.set('')

    def add_to_order(self):
        bouquet_name = self.order_bouquet_combo.get()
        try:
            qty = int(self.order_qty_spin.get())
        except ValueError:
            qty = 1
            
        if bouquet_name and qty > 0:
            # Check if already exists
            found_index = -1
            for i, (name, current_qty) in enumerate(self.current_order):
                if name == bouquet_name:
                    found_index = i
                    break
            
            if found_index != -1:
                # Update existing
                new_total_qty = self.current_order[found_index][1] + qty
                self.current_order[found_index] = (bouquet_name, new_total_qty)
                
                # Update listbox
                self.order_listbox.delete(found_index)
                self.order_listbox.insert(found_index, f"{bouquet_name} (x{new_total_qty})")
            else:
                # Add new
                self.order_listbox.insert(tk.END, f"{bouquet_name} (x{qty})")
                self.current_order.append((bouquet_name, qty))
        else:
            messagebox.showwarning("אזהרה", "נא לבחור זר וכמות חוקית.")

    def remove_from_order(self):
        selection = self.order_listbox.curselection()
        if selection:
            idx = selection[0]
            self.order_listbox.delete(idx)
            del self.current_order[idx]

    def on_order_select(self, event):
        selection = self.order_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.current_order):
                bouquet_name, qty = self.current_order[idx]
                self.order_qty_spin.set(qty)
                self.order_bouquet_combo.set(bouquet_name)

    def update_order_quantity(self):
        selection = self.order_listbox.curselection()
        if not selection:
            messagebox.showwarning("אזהרה", "נא לבחור פריט לעדכון.")
            return
            
        idx = selection[0]
        if idx < len(self.current_order):
            bouquet_name, _ = self.current_order[idx]
            
            try:
                new_qty = int(self.order_qty_spin.get())
            except ValueError:
                messagebox.showwarning("אזהרה", "כמות לא חוקית.")
                return
                
            if new_qty > 0:
                self.current_order[idx] = (bouquet_name, new_qty)
                self.order_listbox.delete(idx)
                self.order_listbox.insert(idx, f"{bouquet_name} (x{new_qty})")
                self.order_listbox.selection_set(idx)
            else:
                messagebox.showwarning("אזהרה", "הכמות חייבת להיות גדולה מ-0.")

    def save_order(self):
        if not self.current_order:
            messagebox.showwarning("אזהרה", "ההזמנה ריקה.")
            return

        # Auto-generate filename from current date DD_MM_YYYY
        filename = datetime.now().strftime("%d_%m_%Y")
        
        orders_dir = "orders"
        os.makedirs(orders_dir, exist_ok=True)
        filepath = os.path.join(orders_dir, f"{filename}.xlsx")
        
        if os.path.exists(filepath):
            if not messagebox.askyesno("אישור דריסה", f"הזמנה '{filename}' כבר קיימת. האם לדרוס?"):
                return
        
        try:
            # Sheet 1: Order
            order_data = []
            for b_name, qty in self.current_order:
                order_data.append({"Bouquet Name": b_name, "Quantity": qty})
            df_order = pd.DataFrame(order_data)
            
            # Sheet 2: Prices
            price_data = []
            for key, price in self.current_prices.items():
                parts = key.split(' - ')
                if len(parts) == 3:
                    price_data.append({
                        "Flower Name": parts[0],
                        "Color": parts[1],
                        "Size": parts[2],
                        "Price": price
                    })
            df_prices = pd.DataFrame(price_data)
            
            with pd.ExcelWriter(filepath) as writer:
                df_order.to_excel(writer, sheet_name="Order", index=False)
                df_prices.to_excel(writer, sheet_name="Prices", index=False)
                
            # messagebox.showinfo("Success", f"Order saved to '{filepath}'.")
        except Exception as e:
            messagebox.showerror("שגיאה", f"שגיאה בשמירת ההזמנה: {e}")

    def load_order(self):
        orders_dir = "orders"
        if not os.path.exists(orders_dir):
            os.makedirs(orders_dir)
            messagebox.showinfo("מידע", "לא נמצאו הזמנות.")
            return

        # Get list of xlsx files (and json for backward compat)
        files = [f for f in os.listdir(orders_dir) if f.endswith('.xlsx') or f.endswith('.json')]
        if not files:
            messagebox.showinfo("מידע", "לא נמצאו הזמנות.")
            return
            
        files.sort(key=lambda x: os.path.getmtime(os.path.join(orders_dir, x)), reverse=True)
        recent_files = files[:10]

        # Create selection window
        dialog = tk.Toplevel(self.root)
        dialog.title("טען הזמנה אחרונה")
        dialog.geometry("300x400")
        
        tk.Label(dialog, text="בחר הזמנה לטעינה:").pack(pady=5)
        
        listbox = tk.Listbox(dialog, exportselection=False)
        listbox.pack(expand=True, fill='both', padx=10, pady=5)
        
        for f in recent_files:
            listbox.insert(tk.END, f)
            
        def do_load():
            selection = listbox.curselection()
            if not selection:
                return
            
            filename = listbox.get(selection[0])
            filepath = os.path.join(orders_dir, filename)
            dialog.destroy()
            
            try:
                if filename.endswith('.json'):
                    # Legacy load
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    loaded_order = []
                    loaded_prices = {}

                    if isinstance(data, list):
                        # Old format
                        loaded_order = data
                    elif isinstance(data, dict) and "order" in data:
                        # New format
                        loaded_order = data["order"]
                        loaded_prices = data.get("prices", {})
                        
                    # Validate data format (list of [name, qty])
                    if isinstance(loaded_order, list) and all(isinstance(item, list) and len(item) == 2 for item in loaded_order):
                        self.current_order = [tuple(item) for item in loaded_order]
                        self.current_prices = loaded_prices
                        self.order_listbox.delete(0, tk.END)
                        for name, qty in self.current_order:
                            self.order_listbox.insert(tk.END, f"{name} (x{qty})")
                    else:
                        messagebox.showerror("שגיאה", "Invalid order file format.")
                else:
                    # Excel load
                    df_order = pd.read_excel(filepath, sheet_name="Order")
                    self.current_order = []
                    for _, row in df_order.iterrows():
                        self.current_order.append((row["Bouquet Name"], int(row["Quantity"])))
                    
                    self.current_prices = {}
                    try:
                        df_prices = pd.read_excel(filepath, sheet_name="Prices")
                        for _, row in df_prices.iterrows():
                            key = f"{row['Flower Name']} - {row['Color']} - {row['Size']}"
                            self.current_prices[key] = float(row['Price'])
                    except:
                        pass # Prices sheet might not exist or be empty
                    
                    self.order_listbox.delete(0, tk.END)
                    for name, qty in self.current_order:
                        self.order_listbox.insert(tk.END, f"{name} (x{qty})")

            except Exception as e:
                messagebox.showerror("שגיאה", f"נכשל בטעינת ההזמנה: {e}")

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="טען", command=do_load).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="ביטול", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def create_quantities_tab(self):
        frame = ttk.Frame(self.left_notebook)
        img = self.create_tab_image('lavender')
        self.left_notebook.add(frame, text="כמויות", image=img, compound='left')
        
        # List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.quantities_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.quantities_listbox.pack(side='left', expand=True, fill='both')
        scrollbar.config(command=self.quantities_listbox.yview)
        
        # Total Label
        self.total_flowers_label = ttk.Label(frame, text="סה\"כ פרחים: 0")
        self.total_flowers_label.pack(pady=5)

    def refresh_quantities(self):
        self.quantities_listbox.delete(0, tk.END)
        total_flowers = defaultdict(int)
        grand_total = 0
        
        for bouquet_name, qty in self.current_order:
            try:
                b = Bouquet(bouquet_name, load_existing=True)
                counts = b.flower_count()
                for flower, count in counts.items():
                    total_count = count * qty
                    total_flowers[flower] += total_count
                    grand_total += total_count
            except Exception as e:
                print(f"Error loading bouquet {bouquet_name}: {e}")
                
        # Sort by flower name
        sorted_flowers = sorted(total_flowers.items(), key=lambda x: x[0].name)
        
        for flower, count in sorted_flowers:
            self.quantities_listbox.insert(tk.END, f"{flower.name} - {flower.color} - {flower.size}: {count}")
            
        self.total_flowers_label.config(text=f"סה\"כ פרחים: {grand_total}")

        self.total_flowers_label.config(text=f"סה\"כ פרחים: {grand_total}")

    def create_order_pricing_tab(self):
        frame = ttk.Frame(self.left_notebook)
        img = self.create_tab_image('gold')
        self.left_notebook.add(frame, text="תמחור הזמנה", image=img, compound='left')
        
        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(header_frame, text="פרח", width=40).pack(side='left', padx=5)
        ttk.Label(header_frame, text="כמות", width=10).pack(side='left', padx=5)
        ttk.Label(header_frame, text="מחיר ליחידה", width=15).pack(side='left', padx=5)
        
        # Scrollable Area
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.order_pricing_scrollable_frame = ttk.Frame(canvas)
        
        self.order_pricing_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=self.order_pricing_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Total Price Label
        self.total_price_label = ttk.Label(frame, text="סה\"כ מחיר: 0.00", font=('Helvetica', 14, 'bold'))
        self.total_price_label.pack(pady=10)

    def refresh_order_pricing_tab(self):
        # Clear existing rows
        for widget in self.order_pricing_scrollable_frame.winfo_children():
            widget.destroy()
            
        total_flowers = defaultdict(int)
        
        # Calculate totals
        for bouquet_name, qty in self.current_order:
            try:
                b = Bouquet(bouquet_name, load_existing=True)
                counts = b.flower_count()
                for flower, count in counts.items():
                    total_count = count * qty
                    total_flowers[flower] += total_count
            except Exception as e:
                print(f"Error loading bouquet {bouquet_name}: {e}")
        
        sorted_flowers = sorted(total_flowers.items(), key=lambda x: x[0].name)
        
        grand_total_price = 0.0
        
        for flower, count in sorted_flowers:
            flower_key = f"{flower.name} - {flower.color} - {flower.size}"
            
            row_frame = ttk.Frame(self.order_pricing_scrollable_frame)
            row_frame.pack(fill='x', pady=2)
            
            ttk.Label(row_frame, text=flower_key, width=40).pack(side='left', padx=5)
            ttk.Label(row_frame, text=str(count), width=10).pack(side='left', padx=5)
            
            price_var = tk.StringVar()
            
            # Determine price: Order Specific > Default (Name-Size) > 0
            current_price = 0.0
            if flower_key in self.current_prices:
                current_price = self.current_prices[flower_key]
            else:
                default_key = f"{flower.name} - {flower.size}"
                if default_key in self.default_prices:
                    current_price = self.default_prices[default_key]
            
            price_var.set(str(current_price))
            grand_total_price += float(current_price) * count
            
            entry = ttk.Entry(row_frame, textvariable=price_var, width=15)
            entry.pack(side='left', padx=5)
            
            # Bind trace to update total price and save to current_prices
            def on_price_change(var, key=flower_key, cnt=count):
                try:
                    val = var.get()
                    if val:
                        price = float(val)
                        self.current_prices[key] = price
                    else:
                        if key in self.current_prices:
                            del self.current_prices[key]
                    self.update_total_price(total_flowers)
                except ValueError:
                    pass # Ignore invalid input
            
            # Use trace_add instead of trace for newer tkinter, but trace is safer for older
            price_var.trace("w", lambda name, index, mode, v=price_var, k=flower_key, c=count: on_price_change(v, k, c))
            
        self.total_price_label.config(text=f"סה\"כ מחיר: {grand_total_price:.2f}")

    def update_total_price(self, total_flowers):
        grand_total = 0.0
        for flower, count in total_flowers.items():
            flower_key = f"{flower.name} - {flower.color} - {flower.size}"
            
            # Priority: Order Specific > Default (Name-Size) > 0
            price = 0.0
            if flower_key in self.current_prices:
                price = self.current_prices[flower_key]
            else:
                default_key = f"{flower.name} - {flower.size}"
                if default_key in self.default_prices:
                    price = self.default_prices[default_key]
                
            grand_total += price * count
        self.total_price_label.config(text=f"סה\"כ מחיר: {grand_total:.2f}")

    def create_summary_tab(self):
        frame = ttk.Frame(self.left_notebook)
        img = self.create_tab_image('cyan')
        self.left_notebook.add(frame, text="סיכום", image=img, compound='left')
        
        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(header_frame, text="זר", width=30).pack(side='left', padx=5)
        ttk.Label(header_frame, text="כמות", width=10).pack(side='left', padx=5)
        ttk.Label(header_frame, text="מחיר יח'", width=15).pack(side='left', padx=5)
        ttk.Label(header_frame, text="סה\"כ", width=15).pack(side='left', padx=5)
        
        # Scrollable Area
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.summary_scrollable_frame = ttk.Frame(canvas)
        
        self.summary_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=self.summary_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Footer (Grand Total + Buttons)
        footer_frame = ttk.Frame(frame)
        footer_frame.pack(fill='x', padx=5, pady=10)
        
        self.summary_total_label = ttk.Label(footer_frame, text="סה\"כ כולל: 0.00", font=('Helvetica', 12, 'bold'))
        self.summary_total_label.pack(side='left', padx=10)
        
        ttk.Button(footer_frame, text="הדפס דוח", command=self.print_summary_report).pack(side='right', padx=5)
        ttk.Button(footer_frame, text="שמור דוח", command=self.save_summary_report).pack(side='right', padx=5)

    def refresh_summary_tab(self):
        # Clear existing
        for widget in self.summary_scrollable_frame.winfo_children():
            widget.destroy()
            
        grand_total = 0.0
        
        for bouquet_name, qty in self.current_order:
            # Calculate unit price for this bouquet
            unit_price = 0.0
            try:
                b = Bouquet(bouquet_name, load_existing=True)
                counts = b.flower_count()
                for flower, count in counts.items():
                    # Get price for this flower
                    flower_key = f"{flower.name} - {flower.color} - {flower.size}"
                    f_price = 0.0
                    if flower_key in self.current_prices:
                        f_price = self.current_prices[flower_key]
                    else:
                        default_key = f"{flower.name} - {flower.size}"
                        if default_key in self.default_prices:
                            f_price = self.default_prices[default_key]
                    
                    unit_price += f_price * count
            except Exception as e:
                print(f"Error calculating price for {bouquet_name}: {e}")
            
            total_price = unit_price * qty
            grand_total += total_price
            
            # Display Row
            row_frame = ttk.Frame(self.summary_scrollable_frame)
            row_frame.pack(fill='x', pady=2)
            
            ttk.Label(row_frame, text=bouquet_name, width=30).pack(side='left', padx=5)
            ttk.Label(row_frame, text=str(qty), width=10).pack(side='left', padx=5)
            ttk.Label(row_frame, text=f"{unit_price:.2f}", width=15).pack(side='left', padx=5)
            ttk.Label(row_frame, text=f"{total_price:.2f}", width=15).pack(side='left', padx=5)
            
        self.summary_total_label.config(text=f"סה\"כ כולל: {grand_total:.2f}")

    def generate_summary_text(self):
        lines = []
        lines.append("דוח סיכום הזמנה")
        lines.append(f"תאריך: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("-" * 60)
        lines.append(f"{'זר':<30} | {'כמות':<5} | {'יח\'':<10} | {'סה\"כ':<10}")
        lines.append("-" * 60)
        
        grand_total = 0.0
        for bouquet_name, qty in self.current_order:
            unit_price = 0.0
            try:
                b = Bouquet(bouquet_name, load_existing=True)
                counts = b.flower_count()
                for flower, count in counts.items():
                    flower_key = f"{flower.name} - {flower.color} - {flower.size}"
                    f_price = 0.0
                    if flower_key in self.current_prices:
                        f_price = self.current_prices[flower_key]
                    else:
                        default_key = f"{flower.name} - {flower.size}"
                        if default_key in self.default_prices:
                            f_price = self.default_prices[default_key]
                    unit_price += f_price * count
            except:
                pass
            
            total_price = unit_price * qty
            grand_total += total_price
            
            lines.append(f"{bouquet_name:<30} | {qty:<5} | {unit_price:<10.2f} | {total_price:<10.2f}")
            
        lines.append("-" * 60)
        lines.append(f"{'סה\"כ כולל':<48} | {grand_total:<10.2f}")
        return "\n".join(lines)

    def print_summary_report(self):
        report_text = self.generate_summary_text()
        
        # Save to temp file and open
        filename = "temp_report.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_text)
            
        try:
            os.startfile(filename)
        except Exception as e:
            messagebox.showerror("שגיאה", f"נכשל בפתיחת הדוח: {e}")

    def save_summary_report(self):
        timestamp = datetime.now().strftime("%d_%m_%Y")
        filename = f"Summary_Report_{timestamp}.txt"
        
        report_text = self.generate_summary_text()
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report_text)
            messagebox.showinfo("הצלחה", f"הדוח נשמר ב-{filename}")
        except Exception as e:
            messagebox.showerror("שגיאה", f"נכשל בשמירת הדוח: {e}")

    def create_global_pricing_tab(self):
        frame = ttk.Frame(self.right_notebook)
        img = self.create_tab_image('silver')
        self.right_notebook.add(frame, text="מחירון", image=img, compound='left')
        
        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(header_frame, text="פרח", width=40).pack(side='left', padx=5)
        ttk.Label(header_frame, text="מחיר ברירת מחדל", width=15).pack(side='left', padx=5)
        
        # Button Frame (Moved to top or bottom with fixed visibility)
        # We'll put it at the bottom, but ensure it's packed AFTER the canvas with fill='x'
        # Actually, to ensure it's always visible, we should pack it BEFORE the canvas if we want it top,
        # or pack it with side='bottom' BEFORE packing the canvas.
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side='bottom', fill='x', pady=10)

        ttk.Button(btn_frame, text="טען מחירון", command=self.load_default_prices_from_file).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="שמור מחירון", command=self.save_default_prices).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="שמור עם תאריך", command=self.save_timestamped_prices).pack(side='left', padx=5)

        # Scrollable Area
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.global_pricing_scrollable_frame = ttk.Frame(canvas)
        
        self.global_pricing_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        # Ensure the inner frame expands to fill the canvas width
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(window_id, width=e.width))
        
        window_id = canvas.create_window((0, 0), window=self.global_pricing_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def save_timestamped_prices(self):
        timestamp = datetime.now().strftime("%d_%m_%Y")
        filename = f"DefaultPricing_{timestamp}.xlsx"
        
        data = []
        # Iterate through all defined flowers to ensure complete list
        for f_name in sorted(self.flower_types.flowers):
            config = self.flower_types.get_config(f_name)
            valid_sizes = config.get('sizes', [])
            
            # If no specific sizes defined, use all available sizes
            if not valid_sizes:
                valid_sizes = self.flower_sizes.sizes
                
            for f_size in valid_sizes:
                key = f"{f_name} - {f_size}"
                price = self.default_prices.get(key, 0.0)
                
                data.append({
                    "Flower Name": f_name,
                    "Size": f_size,
                    "Price": price
                })
        
        df = pd.DataFrame(data, columns=["Flower Name", "Size", "Price"])
        try:
            df.to_excel(filename, index=False)
            messagebox.showinfo("הצלחה", f"המחירים נשמרו בקובץ '{filename}'")
        except Exception as e:
            messagebox.showerror("שגיאה", f"שגיאה בשמירת המחירים: {e}")

    def load_default_prices_from_file(self):
        file_path = filedialog.askopenfilename(
            title="בחר קובץ מחירי ברירת מחדל",
            filetypes=[("קבצי Excel/JSON", "*.xlsx *.json"), ("קבצי Excel", "*.xlsx"), ("קבצי JSON", "*.json")]
        )
        if not file_path:
            return

        try:
            new_prices = {}
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path)
                # Expected columns: Flower Name, Size, Price
                
                required_cols = ["Flower Name", "Size", "Price"]
                # Check if columns exist
                if all(col in df.columns for col in required_cols):
                    for _, row in df.iterrows():
                        key = f"{row['Flower Name']} - {row['Size']}"
                        new_prices[key] = float(row['Price'])
                else:
                     # Try legacy format with Color?
                     if "Color" in df.columns and "Flower Name" in df.columns and "Size" in df.columns and "Price" in df.columns:
                         for _, row in df.iterrows():
                            key = f"{row['Flower Name']} - {row['Size']}"
                            new_prices[key] = float(row['Price'])
                     else:
                         raise ValueError(f"חסרות עמודות בקובץ Excel. נדרש: {', '.join(required_cols)}")

            elif file_path.lower().endswith('.json'):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, price in data.items():
                        # Key format: "Flower - Size" or "Flower - Color - Size"
                        parts = key.split(' - ')
                        if len(parts) == 2:
                            new_prices[key] = float(price)
                        elif len(parts) == 3:
                            # Legacy: Flower - Color - Size -> Flower - Size
                            new_key = f"{parts[0]} - {parts[2]}"
                            new_prices[new_key] = float(price)
            
            if new_prices:
                # Auto-update flower sizes if needed
                updated_flowers = set()
                for key in new_prices:
                    # key is "Name - Size"
                    parts = key.rsplit(' - ', 1)
                    if len(parts) == 2:
                        f_name, f_size = parts
                        if self.flower_types.contains(f_name):
                            config = self.flower_types.get_config(f_name)
                            current_sizes = config.get('sizes', [])
                            # If sizes are restricted (not empty) and this size is missing
                            if current_sizes and f_size not in current_sizes:
                                current_sizes.append(f_size)
                                self.flower_types.update_config(f_name, current_sizes)
                                updated_flowers.add(f_name)
                
                if updated_flowers:
                    # Refresh flowers tab if it exists
                    if hasattr(self, 'refresh_flowers_list'):
                        self.refresh_flowers_list()

                self.default_prices.update(new_prices)
                self.save_default_prices()
                self.refresh_global_pricing_tab()
                
                msg = f"נטענו/מוזגו {len(new_prices)} מחירים."
                if updated_flowers:
                    msg += f"\n\nכמו כן נוספו גדלים חסרים עבור {len(updated_flowers)} פרחים."
                
                messagebox.showinfo("הצלחה", msg)
            else:
                messagebox.showwarning("אזהרה", "לא נמצאו מחירים תקינים בקובץ.")

        except Exception as e:
            messagebox.showerror("שגיאה", f"שגיאה בטעינת המחירים: {e}")

    def refresh_global_pricing_tab(self):
        if not hasattr(self, 'global_pricing_scrollable_frame'):
            return
        # Clear existing rows
        for widget in self.global_pricing_scrollable_frame.winfo_children():
            widget.destroy()
            
        # Generate all combinations of existing flowers and sizes (ignoring colors)
        all_combinations = []
        for f_name in sorted(self.flower_types.flowers):
            config = self.flower_types.get_config(f_name)
            valid_sizes = config.get('sizes', [])
            
            if not valid_sizes: valid_sizes = self.flower_sizes.sizes
            
            for f_size in valid_sizes:
                all_combinations.append(f"{f_name} - {f_size}")
        
        for flower_key in all_combinations:
            row_frame = ttk.Frame(self.global_pricing_scrollable_frame)
            row_frame.pack(fill='x', pady=2)
            
            ttk.Label(row_frame, text=flower_key, width=40).pack(side='left', padx=5)
            
            price_var = tk.StringVar()
            if flower_key in self.default_prices:
                price_var.set(str(self.default_prices[flower_key]))
            
            entry = ttk.Entry(row_frame, textvariable=price_var, width=15)
            entry.pack(side='left', padx=5)
            
            def on_default_price_change(var, key=flower_key):
                try:
                    val = var.get()
                    if val:
                        self.default_prices[key] = float(val)
                    else:
                        if key in self.default_prices:
                            del self.default_prices[key]
                except ValueError:
                    pass
            
            price_var.trace("w", lambda name, index, mode, v=price_var, k=flower_key: on_default_price_change(v, k))

def check_single_instance():
    try:
        # Create a socket to bind to a specific port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to localhost on a specific port (e.g., 54321)
        s.bind(('127.0.0.1', 54321))
        return s
    except socket.error:
        return None

if __name__ == "__main__":
    lock_socket = check_single_instance()
    if not lock_socket:
        root = tk.Tk()
        root.withdraw() # Hide the main window
        messagebox.showerror("שגיאה", "האפליקציה כבר רצה.")
        sys.exit(1)

    root = tk.Tk()
    app = FlowerApp(root)
    root.mainloop()

