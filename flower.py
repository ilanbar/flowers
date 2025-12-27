from collections import namedtuple
import json

FlowerData = namedtuple('FlowerData', ['name', 'color', 'size'])

class FlowersTypes:

    def __init__(self):
        try:
            with open('Flowers.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Migrate list to dict
                    self.flowers = {name: {'colors': [], 'sizes': []} for name in data}
                    self._save()
                else:
                    self.flowers = data
        except (FileNotFoundError, json.JSONDecodeError):
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

    def update_config(self, name, colors, sizes):
        if name in self.flowers:
            self.flowers[name] = {'colors': colors, 'sizes': sizes}
            self._save()

    def get_config(self, name):
        return self.flowers.get(name, {'colors': [], 'sizes': []})

    def _save(self):
        with open('Flowers.json', 'w', encoding='utf-8') as f:
            json.dump(self.flowers, f, ensure_ascii=False, indent=2)


class FlowerColors:

    def __init__(self):
        try:
            with open('Colors.json', 'r', encoding='utf-8') as f:
                self.colors = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
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
        with open('Colors.json', 'w', encoding='utf-8') as f:
            json.dump(self.colors, f, ensure_ascii=False, indent=2)

class FlowerSizes:

    def __init__(self):
        self.sizes = ['קטן', 'בינוני', 'גדול', 'רגיל']
