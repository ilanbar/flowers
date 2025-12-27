import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import shutil
import socket
import sys
from datetime import datetime
from collections import defaultdict
from flower import FlowersTypes, FlowerColors, FlowerSizes, FlowerData
from bouquet import Bouquet

class FlowerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flower Shop Manager")
        
        # Increase font size
        default_font = ('Helvetica', 12)
        self.root.option_add('*Font', default_font)
        style = ttk.Style()
        style.configure('.', font=default_font)
        
        self.flower_types = FlowersTypes()
        self.flower_colors = FlowerColors()
        self.flower_sizes = FlowerSizes()
        
        self.current_order = []
        self.tab_images = [] # Keep references to images

        self.create_menu()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.create_orders_tab()
        self.create_quantities_tab()
        self.create_bouquets_tab()
        self.create_flowers_tab()
        self.create_colors_tab()
        
    def create_tab_image(self, color):
        img = tk.PhotoImage(width=20, height=20)
        img.put(color, to=(0, 0, 20, 20))
        self.tab_images.append(img)
        return img

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Create Backup", command=self.create_backup)
        file_menu.add_command(label="Restore Backup", command=self.restore_backup_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_dir = os.path.join("backups", timestamp)
            os.makedirs(backup_dir, exist_ok=True)
            
            files_to_backup = ["Flowers.json", "Colors.json", "Bouquets.json"]
            for filename in files_to_backup:
                if os.path.exists(filename):
                    shutil.copy2(filename, backup_dir)
            
            messagebox.showinfo("Backup", f"Backup created successfully in:\n{backup_dir}")
        except Exception as e:
            messagebox.showerror("Backup Error", f"Failed to create backup: {e}")

    def restore_backup_dialog(self):
        if not os.path.exists("backups"):
            messagebox.showinfo("Restore", "No backups found.")
            return

        # Get list of backups (directories)
        backups = [d for d in os.listdir("backups") if os.path.isdir(os.path.join("backups", d))]
        backups.sort(reverse=True) # Newest first
        
        if not backups:
            messagebox.showinfo("Restore", "No backups found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Restore Backup")
        dialog.geometry("300x400")
        
        tk.Label(dialog, text="Select a backup to restore:").pack(pady=5)
        
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
            
            if messagebox.askyesno("Confirm Restore", f"Are you sure you want to restore from '{backup_name}'?\nCurrent data will be overwritten."):
                try:
                    files_to_restore = ["Flowers.json", "Colors.json", "Bouquets.json"]
                    for filename in files_to_restore:
                        src = os.path.join(backup_path, filename)
                        if os.path.exists(src):
                            shutil.copy2(src, filename)
                    
                    self.reload_data()
                    messagebox.showinfo("Restore", "Data restored successfully.")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Restore Error", f"Failed to restore: {e}")

        tk.Button(dialog, text="Restore", command=do_restore).pack(pady=10)

    def reload_data(self):
        self.flower_types = FlowersTypes()
        self.flower_colors = FlowerColors()
        # self.flower_sizes is static, no need to reload
        
        self.refresh_flowers_list()
        self.refresh_colors_list()
        self.refresh_bouquets_list()

    def create_flowers_tab(self):
        frame = ttk.Frame(self.notebook)
        img = self.create_tab_image('lightblue')
        self.notebook.add(frame, text="Flowers", image=img, compound='left')
        
        # List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.flowers_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.flowers_listbox.pack(side='left', expand=True, fill='both')
        scrollbar.config(command=self.flowers_listbox.yview)
        
        self.refresh_flowers_list()
        
        # Controls
        controls = ttk.Frame(frame)
        controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(controls, text="Name:").pack(side='left')
        self.flower_entry = ttk.Entry(controls)
        self.flower_entry.pack(side='left', expand=True, fill='x', padx=5)
        
        add_btn = ttk.Button(controls, text="Add", command=self.add_flower)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(controls, text="Delete", command=self.delete_flower)
        del_btn.pack(side='left', padx=5)

    def refresh_flowers_list(self):
        self.flowers_listbox.delete(0, tk.END)
        for f in sorted(self.flower_types.flowers):
            self.flowers_listbox.insert(tk.END, f)

    def add_flower(self):
        name = self.flower_entry.get().strip()
        if name:
            if self.flower_types.contains(name):
                messagebox.showwarning("Warning", f"Flower '{name}' already exists.")
                return
            self.flower_types.add(name)
            self.flower_entry.delete(0, tk.END)
            self.refresh_flowers_list()

    def delete_flower(self):
        selection = self.flowers_listbox.curselection()
        if selection:
            name = self.flowers_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Delete flower '{name}'?"):
                self.flower_types.remove(name)
                self.refresh_flowers_list()

    def create_colors_tab(self):
        frame = ttk.Frame(self.notebook)
        img = self.create_tab_image('lightgreen')
        self.notebook.add(frame, text="Colors", image=img, compound='left')
        
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
        
        ttk.Label(controls, text="Color:").pack(side='left')
        self.color_entry = ttk.Entry(controls)
        self.color_entry.pack(side='left', expand=True, fill='x', padx=5)
        
        add_btn = ttk.Button(controls, text="Add", command=self.add_color)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(controls, text="Delete", command=self.delete_color)
        del_btn.pack(side='left', padx=5)

    def refresh_colors_list(self):
        self.colors_listbox.delete(0, tk.END)
        for c in sorted(self.flower_colors.colors):
            self.colors_listbox.insert(tk.END, c)

    def add_color(self):
        color = self.color_entry.get().strip()
        if color:
            if color in self.flower_colors.colors:
                messagebox.showwarning("Warning", f"Color '{color}' already exists.")
                return
            self.flower_colors.add(color)
            self.color_entry.delete(0, tk.END)
            self.refresh_colors_list()

    def delete_color(self):
        selection = self.colors_listbox.curselection()
        if selection:
            color = self.colors_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Delete color '{color}'?"):
                self.flower_colors.remove(color)
                self.refresh_colors_list()

    def create_bouquets_tab(self):
        frame = ttk.Frame(self.notebook)
        img = self.create_tab_image('lightyellow')
        self.notebook.add(frame, text="Bouquets", image=img, compound='left')
        
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
        
        ttk.Label(input_frame, text="Name:").pack(side='left')
        self.bouquet_name_entry = ttk.Entry(input_frame)
        self.bouquet_name_entry.pack(side='left', expand=True, fill='x', padx=5)
        
        ttk.Label(input_frame, text="Based On:").pack(side='left')
        self.based_on_combo = ttk.Combobox(input_frame, state="readonly", width=20)
        self.based_on_combo.pack(side='left', padx=5)
        
        # Row 2: Buttons
        btn_frame = ttk.Frame(controls)
        btn_frame.pack(fill='x', pady=2)
        
        add_btn = ttk.Button(btn_frame, text="Add Bouquet", command=self.add_bouquet)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(btn_frame, text="Delete Bouquet", command=self.delete_bouquet)
        del_btn.pack(side='left', padx=5)
        
        edit_btn = ttk.Button(btn_frame, text="Edit Name", command=self.edit_bouquet_name)
        edit_btn.pack(side='left', padx=5)
        
        self.refresh_bouquets_list()

    def get_bouquet_names(self):
        try:
            with open("Bouquets.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return list(data.keys())
        except:
            return []

    def refresh_bouquets_list(self):
        self.bouquets_listbox.delete(0, tk.END)
        names = sorted(self.get_bouquet_names())
        for name in names:
            self.bouquets_listbox.insert(tk.END, name)
        
        self.based_on_combo['values'] = [""] + names
        self.based_on_combo.set("")

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
                messagebox.showinfo("Success", f"Bouquet '{b.name}' created.")
            except ValueError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")
        else:
            messagebox.showwarning("Warning", "Please enter a bouquet name.")

    def delete_bouquet(self):
        selection = self.bouquets_listbox.curselection()
        if selection:
            name = self.bouquets_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Delete bouquet '{name}'?"):
                try:
                    Bouquet.delete_bouquet(name)
                    self.refresh_bouquets_list()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

    def edit_bouquet_name(self):
        selection = self.bouquets_listbox.curselection()
        if selection:
            old_name = self.bouquets_listbox.get(selection[0])
            new_name = simpledialog.askstring("Edit Name", f"Enter new name for '{old_name}':")
            if new_name:
                new_name = new_name.strip()
                if new_name and new_name != old_name:
                    try:
                        Bouquet.rename_bouquet(old_name, new_name)
                        self.refresh_bouquets_list()
                        messagebox.showinfo("Success", f"Renamed '{old_name}' to '{new_name}'.")
                    except ValueError as e:
                        messagebox.showerror("Error", str(e))
                    except Exception as e:
                        messagebox.showerror("Error", f"An error occurred: {e}")

    def open_bouquet_editor(self, event):
        selection = self.bouquets_listbox.curselection()
        if not selection:
            return
        name = self.bouquets_listbox.get(selection[0])
        
        try:
            bouquet = Bouquet(name, load_existing=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load bouquet: {e}")
            return

        editor = tk.Toplevel(self.root)
        editor.title(f"Edit Bouquet: {name}")
        editor.geometry("600x500")
        
        # Left: List of flowers
        list_frame = ttk.LabelFrame(editor, text="Flowers in Bouquet")
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
        add_frame = ttk.LabelFrame(controls_frame, text="Add Flower")
        add_frame.pack(fill='x', pady=5)
        
        ttk.Label(add_frame, text="Type:").pack(anchor='w', padx=5)
        type_combo = ttk.Combobox(add_frame, values=sorted(self.flower_types.flowers), state="readonly")
        type_combo.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(add_frame, text="Color:").pack(anchor='w', padx=5)
        color_combo = ttk.Combobox(add_frame, values=sorted(self.flower_colors.colors), state="readonly")
        color_combo.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(add_frame, text="Size:").pack(anchor='w', padx=5)
        size_combo = ttk.Combobox(add_frame, values=self.flower_sizes.sizes, state="readonly")
        size_combo.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(add_frame, text="Count:").pack(anchor='w', padx=5)
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
                messagebox.showwarning("Warning", "Please select Type, Color, and Size.")
        
        ttk.Button(add_frame, text="Add", command=add_flower).pack(fill='x', padx=5, pady=5)
        
        def remove_flower_action():
            selection = flowers_list.curselection()
            if selection:
                idx = selection[0]
                flower = current_display_items[idx]
                bouquet.remove_flower(flower, count=1)
                refresh_list()
        
        ttk.Button(controls_frame, text="Remove Selected (1)", command=remove_flower_action).pack(fill='x', pady=5)
        
        # Edit Quantity Section
        edit_frame = ttk.LabelFrame(controls_frame, text="Edit Quantity")
        edit_frame.pack(fill='x', pady=5)
        
        edit_qty_spin = ttk.Spinbox(edit_frame, from_=1, to=100, width=5)
        edit_qty_spin.pack(side='left', padx=5, pady=5)
        
        def update_quantity():
            selection = flowers_list.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a flower to update.")
                return
            
            idx = selection[0]
            flower = current_display_items[idx]
            
            try:
                new_qty = int(edit_qty_spin.get())
            except ValueError:
                messagebox.showwarning("Warning", "Invalid quantity.")
                return
                
            if new_qty < 1:
                messagebox.showwarning("Warning", "Quantity must be at least 1.")
                return

            current_counts = bouquet.flower_count()
            current_qty = current_counts.get(flower, 0)
            
            if new_qty > current_qty:
                bouquet.select_flower(flower, count=new_qty - current_qty)
            elif new_qty < current_qty:
                bouquet.remove_flower(flower, count=current_qty - new_qty)
            
            refresh_list()
            
        ttk.Button(edit_frame, text="Update", command=update_quantity).pack(side='left', fill='x', expand=True, padx=5, pady=5)

        def on_flower_select(event):
            selection = flowers_list.curselection()
            if selection:
                idx = selection[0]
                flower = current_display_items[idx]
                counts = bouquet.flower_count()
                qty = counts.get(flower, 0)
                edit_qty_spin.set(qty)
        
        flowers_list.bind('<<ListboxSelect>>', on_flower_select)
        
        def save_bouquet():
            bouquet.save()
            messagebox.showinfo("Success", "Bouquet saved.")
            
        ttk.Button(controls_frame, text="Save Changes", command=save_bouquet).pack(fill='x', pady=20)

    def create_orders_tab(self):
        frame = ttk.Frame(self.notebook)
        img = self.create_tab_image('darkorange')
        self.notebook.add(frame, text="Order", image=img, compound='left')
        
        # Controls
        controls = ttk.Frame(frame)
        controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(controls, text="Bouquet:").pack(side='left')
        self.order_bouquet_combo = ttk.Combobox(controls, state="readonly", width=20)
        self.order_bouquet_combo.pack(side='left', padx=5)
        
        ttk.Label(controls, text="Quantity:").pack(side='left')
        self.order_qty_spin = ttk.Spinbox(controls, from_=1, to=100, width=5)
        self.order_qty_spin.set(1)
        self.order_qty_spin.pack(side='left', padx=5)
        
        add_btn = ttk.Button(controls, text="Add to Order", command=self.add_to_order)
        add_btn.pack(side='left', padx=5)
        
        del_btn = ttk.Button(controls, text="Remove Selected", command=self.remove_from_order)
        del_btn.pack(side='left', padx=5)
        
        update_btn = ttk.Button(controls, text="Update Qty", command=self.update_order_quantity)
        update_btn.pack(side='left', padx=5)
        
        save_btn = ttk.Button(controls, text="Save Order", command=self.save_order)
        save_btn.pack(side='left', padx=5)
        
        load_btn = ttk.Button(controls, text="Load Order", command=self.load_order)
        load_btn.pack(side='left', padx=5)
        
        # Order List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.order_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, exportselection=False)
        self.order_listbox.pack(side='left', expand=True, fill='both')
        self.order_listbox.bind('<<ListboxSelect>>', self.on_order_select)
        scrollbar.config(command=self.order_listbox.yview)
        
        # Refresh bouquets list when tab is selected
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def on_tab_change(self, event):
        # Check if the selected tab is "Order"
        try:
            selected_tab = self.notebook.select()
            tab_text = self.notebook.tab(selected_tab, "text")
            if tab_text == "Order":
                self.refresh_order_bouquets()
            elif tab_text == "Quantities":
                self.refresh_quantities()
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
            messagebox.showwarning("Warning", "Please select a bouquet and valid quantity.")

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
            messagebox.showwarning("Warning", "Please select an item to update.")
            return
            
        idx = selection[0]
        if idx < len(self.current_order):
            bouquet_name, _ = self.current_order[idx]
            
            try:
                new_qty = int(self.order_qty_spin.get())
            except ValueError:
                messagebox.showwarning("Warning", "Invalid quantity.")
                return
                
            if new_qty > 0:
                self.current_order[idx] = (bouquet_name, new_qty)
                self.order_listbox.delete(idx)
                self.order_listbox.insert(idx, f"{bouquet_name} (x{new_qty})")
                self.order_listbox.selection_set(idx)
            else:
                messagebox.showwarning("Warning", "Quantity must be greater than 0.")

    def save_order(self):
        if not self.current_order:
            messagebox.showwarning("Warning", "Order is empty.")
            return

        # Auto-generate filename from current date DD_MM_YYYY
        filename = datetime.now().strftime("%d_%m_%Y")
        
        orders_dir = "orders"
        os.makedirs(orders_dir, exist_ok=True)
        filepath = os.path.join(orders_dir, f"{filename}.json")
        
        if os.path.exists(filepath):
            if not messagebox.askyesno("Confirm Overwrite", f"Order '{filename}' already exists. Overwrite?"):
                return
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_order, f, ensure_ascii=False, indent=2)
            # messagebox.showinfo("Success", f"Order saved to '{filepath}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save order: {e}")

    def load_order(self):
        orders_dir = "orders"
        if not os.path.exists(orders_dir):
            os.makedirs(orders_dir)
            messagebox.showinfo("Info", "No orders found.")
            return

        # Get list of json files sorted by modification time (newest first)
        files = [f for f in os.listdir(orders_dir) if f.endswith('.json')]
        if not files:
            messagebox.showinfo("Info", "No orders found.")
            return
            
        files.sort(key=lambda x: os.path.getmtime(os.path.join(orders_dir, x)), reverse=True)
        recent_files = files[:10]

        # Create selection window
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Recent Order")
        dialog.geometry("300x400")
        
        tk.Label(dialog, text="Select an order to load:").pack(pady=5)
        
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
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Validate data format (list of [name, qty])
                if isinstance(data, list) and all(isinstance(item, list) and len(item) == 2 for item in data):
                    self.current_order = [tuple(item) for item in data]
                    self.order_listbox.delete(0, tk.END)
                    for name, qty in self.current_order:
                        self.order_listbox.insert(tk.END, f"{name} (x{qty})")
                    #messagebox.showinfo("Success", f"Order '{filename}' loaded.")
                else:
                    messagebox.showerror("Error", "Invalid order file format.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load order: {e}")

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Load", command=do_load).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def create_quantities_tab(self):
        frame = ttk.Frame(self.notebook)
        img = self.create_tab_image('lavender')
        self.notebook.add(frame, text="Quantities", image=img, compound='left')
        
        # List
        list_frame = ttk.Frame(frame)
        list_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.quantities_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.quantities_listbox.pack(side='left', expand=True, fill='both')
        scrollbar.config(command=self.quantities_listbox.yview)
        
        # Total Label
        self.total_flowers_label = ttk.Label(frame, text="Total Flowers: 0")
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
            
        self.total_flowers_label.config(text=f"Total Flowers: {grand_total}")

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
        messagebox.showerror("Error", "The application is already running.")
        sys.exit(1)

    root = tk.Tk()
    app = FlowerApp(root)
    root.mainloop()

