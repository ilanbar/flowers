from collections import namedtuple
import json

FlowerData = namedtuple('FlowerData', ['name', 'color', 'size'])

class FlowersTypes:

    def __init__(self):
        with open('Flowers.json', 'r', encoding='utf-8') as f:
            self.flowers = json.load(f)

    def add(self, name):
        # check if flower already exists
        if name not in self.flowers:
            self.flowers.append(name)
            self._save()
        
    
    def remove(self, name):
        if name in self.flowers:
            self.flowers.remove(name)
            self._save()

    def contains(self, name):
        return name in self.flowers

    def _save(self):
        with open('Flowers.json', 'w', encoding='utf-8') as f:
            json.dump(self.flowers, f, ensure_ascii=False, indent=2)


class FlowerColors:

    def __init__(self):
        with open('Colors.json', 'r', encoding='utf-8') as f:
            self.colors = json.load(f)

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
