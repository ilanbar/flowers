from collections import namedtuple
import json
import pandas as pd
import os

FlowerData = namedtuple('FlowerData', ['name', 'color', 'size'])

class FlowersTypes:

    def __init__(self):
        self.flowers = {}
        if os.path.exists('Flowers.xlsx'):
            try:
                df = pd.read_excel('Flowers.xlsx')
                # Expected columns: Name, Sizes
                for _, row in df.iterrows():
                    name = str(row['Name'])
                    sizes = str(row['Sizes']).split(',') if pd.notna(row['Sizes']) and row['Sizes'] else []
                    # Clean up whitespace
                    sizes = [s.strip() for s in sizes if s.strip()]
                    self.flowers[name] = {'colors': [], 'sizes': sizes}
            except Exception as e:
                print(f"Error loading Flowers.xlsx: {e}")
                self.flowers = {}
        elif os.path.exists('Flowers.json'):
            # Migration
            try:
                with open('Flowers.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.flowers = {name: {'colors': [], 'sizes': []} for name in data}
                    else:
                        self.flowers = data
                self._save() # Save as Excel
            except (FileNotFoundError, json.JSONDecodeError):
                self.flowers = {}
                self._save()
        else:
            self.flowers = {}
            self._save()

    def add(self, name):
        # check if flower already exists
        if name not in self.flowers:
            self.flowers[name] = {'colors': [], 'sizes': []}
            self._save()
        
    
    def remove(self, name):
        if name in self.flowers:
            del self.flowers[name]
            self._save()

    def contains(self, name):
        return name in self.flowers

    def update_config(self, name, sizes):
        if name in self.flowers:
            # We keep 'colors' key empty or ignore it, but let's keep structure consistent for now
            self.flowers[name] = {'colors': [], 'sizes': sizes}
            self._save()

    def get_config(self, name):
        return self.flowers.get(name, {'colors': [], 'sizes': []})

    def _save(self):
        data = []
        for name, config in self.flowers.items():
            # Colors column removed/ignored
            sizes_str = ",".join(config.get('sizes', []))
            data.append({'Name': name, 'Sizes': sizes_str})
        
        df = pd.DataFrame(data, columns=['Name', 'Sizes'])
        try:
            df.to_excel('Flowers.xlsx', index=False)
        except Exception as e:
            print(f"Error saving Flowers.xlsx: {e}")


class FlowerColors:

    def __init__(self):
        self.colors = []
        if os.path.exists('Colors.xlsx'):
            try:
                df = pd.read_excel('Colors.xlsx')
                if 'Color' in df.columns:
                    self.colors = df['Color'].dropna().astype(str).tolist()
            except Exception as e:
                print(f"Error loading Colors.xlsx: {e}")
        elif os.path.exists('Colors.json'):
            try:
                with open('Colors.json', 'r', encoding='utf-8') as f:
                    self.colors = json.load(f)
                self._save()
            except (FileNotFoundError, json.JSONDecodeError):
                self.colors = []
                self._save()
        else:
            self.colors = []
            self._save()

    def add(self, color):
        if color not in self.colors:
            self.colors.append(color)
            self._save()

    def remove(self, color):
        if color in self.colors:
            self.colors.remove(color)
            self._save()

    def _save(self):
        df = pd.DataFrame({'Color': self.colors})
        try:
            df.to_excel('Colors.xlsx', index=False)
        except Exception as e:
            print(f"Error saving Colors.xlsx: {e}")

class FlowerSizes:

    def __init__(self):
        self.sizes = ['קטן', 'בינוני', 'גדול', 'רגיל']
