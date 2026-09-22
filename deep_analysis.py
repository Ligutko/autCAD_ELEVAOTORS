# -*- coding: utf-8 -*-
"""
ГЛИБОКИЙ АНАЛІЗ КРЕСЛЕННЯ
Знаходить ВСІ об'єкти та їх зв'язки з силосами
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


class DeepAnalyzer:
    def __init__(self):
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []
        self.all_objects = []

    def connect(self):
        """Connect to AutoCAD"""
        print("[1] Pidkliuchennia...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Obiektiv: {self.ms.Count}")

    def load_silos(self):
        """Load silos data"""
        print("\n[2] Zavantazhennia sylosiv...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)
        self.silos = silos_data['silos']
        print(f"    Sylosiv: {len(self.silos)}")

    def analyze_all_objects(self):
        """Analyze ALL objects in drawing"""
        print("\n[3] Analiz VSIOGO kreslennnia...")

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)
                obj_type = obj.ObjectName

                obj_info = {
                    'index': i,
                    'type': obj_type,
                    'layer': obj.Layer if hasattr(obj, 'Layer') else 'N/A'
                }

                # Otrimaty geometriiu
                if hasattr(obj, 'GetBoundingBox'):
                    try:
                        bbox = obj.GetBoundingBox()
                        min_p, max_p = bbox[0], bbox[1]

                        obj_info['bounds'] = {
                            'min_x': round(min_p[0], 2),
                            'max_x': round(max_p[0], 2),
                            'min_y': round(min_p[1], 2),
                            'max_y': round(max_p[1], 2)
                        }

                        obj_info['center'] = {
                            'x': round((min_p[0] + max_p[0]) / 2, 2),
                            'y': round((min_p[1] + max_p[1]) / 2, 2)
                        }

                        obj_info['size'] = {
                            'width': round(max_p[0] - min_p[0], 2),
                            'height': round(max_p[1] - min_p[1], 2)
                        }

                        # Oriyentatsiia
                        w = obj_info['size']['width']
                        h = obj_info['size']['height']

                        if w > h * 2:
                            obj_info['orientation'] = 'horizontal'
                        elif h > w * 2:
                            obj_info['orientation'] = 'vertical'
                        else:
                            obj_info['orientation'] = 'square'

                    except:
                        pass

                # Dlia liniy - otrimaty start/end
                if obj_type == 'AcDbLine':
                    try:
                        start = obj.StartPoint
                        end = obj.EndPoint
                        obj_info['line'] = {
                            'start': {'x': round(start[0], 2), 'y': round(start[1], 2)},
                            'end': {'x': round(end[0], 2), 'y': round(end[1], 2)}
                        }
                    except:
                        pass

                self.all_objects.append(obj_info)

            except:
                pass

        print(f"    Proanalyzovano: {len(self.all_objects)} obiektiv")

    def assign_to_silos(self):
        """Assign each object to nearest silo"""
        print("\n[4] Pryzviachennia obiektiv do sylosiv...")

        silo_assignments = {silo['number']: [] for silo in self.silos}
        unassigned = []

        for obj in self.all_objects:
            if 'center' not in obj:
                unassigned.append(obj)
                continue

            obj_cx = obj['center']['x']
            obj_cy = obj['center']['y']

            # Znayty nayblyzhchyi sylos
            min_dist = float('inf')
            nearest_silo = None

            for silo in self.silos:
                silo_cx = silo['center']['x']
                silo_cy = silo['center']['y']

                dist = ((obj_cx - silo_cx)**2 + (obj_cy - silo_cy)**2)**0.5

                if dist < min_dist:
                    min_dist = dist
                    nearest_silo = silo['number']

            # Pryzvyachyty
            if min_dist < 150:  # Maksymalnya vidstan (zbilsheno do 150!)
                obj['assigned_to_silo'] = nearest_silo
                obj['distance_to_silo'] = round(min_dist, 2)
                silo_assignments[nearest_silo].append(obj)
            else:
                obj['assigned_to_silo'] = None
                obj['distance_to_silo'] = None
                unassigned.append(obj)

        # Statystyka
        print(f"\n    PRYZVIACHENNIA PO SYLOSAKH:")
        for silo_num, objects in sorted(silo_assignments.items()):
            layers_count = {}
            for o in objects:
                layer = o['layer']
                if layer not in layers_count:
                    layers_count[layer] = 0
                layers_count[layer] += 1

            print(f"\n      Sylos #{silo_num}: {len(objects)} obiektiv")
            for layer, count in sorted(layers_count.items(), key=lambda x: x[1], reverse=True):
                print(f"        - {layer}: {count}")

        print(f"\n    Nepryzviachenykh: {len(unassigned)}")

        return silo_assignments, unassigned

    def find_connections(self, silo_assignments):
        """Find connections between silos"""
        print("\n[5] Poshuk zviazkiv mizh sylosamy...")

        connections = []

        # Znayty CHERVONI obiekty (konveyory)
        for silo_num, objects in silo_assignments.items():
            red_objects = [o for o in objects if 'CFF-00-00' in o['layer']]

            for red_obj in red_objects:
                # Perevirka chy obiekt tiahnietsia do inshoho sylosa
                if 'bounds' in red_obj:
                    bounds = red_obj['bounds']

                    # Perevirka chy perekryvaiet inshyi sylos
                    for other_silo in self.silos:
                        if other_silo['number'] == silo_num:
                            continue

                        other_bounds = other_silo['bounds']

                        # Chy ye perekryttia
                        x_overlap = not (bounds['max_x'] < other_bounds['min_x'] or bounds['min_x'] > other_bounds['max_x'])
                        y_overlap = not (bounds['max_y'] < other_bounds['min_y'] or bounds['min_y'] > other_bounds['max_y'])

                        if x_overlap or y_overlap:
                            connection = {
                                'from_silo': silo_num,
                                'to_silo': other_silo['number'],
                                'object_index': red_obj['index'],
                                'object_type': red_obj['type'],
                                'orientation': red_obj.get('orientation', 'unknown')
                            }
                            connections.append(connection)

        print(f"    Znaideno zviazkiv: {len(connections)}")

        return connections

    def save_results(self, silo_assignments, connections):
        """Save analysis results"""
        print("\n[6] Zberezhenna rezultativ...")

        output = {
            'total_objects': len(self.all_objects),
            'silos_count': len(self.silos),
            'assignments': {},
            'connections': connections
        }

        for silo_num, objects in silo_assignments.items():
            output['assignments'][f'silo_{silo_num}'] = {
                'count': len(objects),
                'objects': objects  # VSI obiekty!
            }

        output_path = 'd:/autocad project/deep_analysis_result.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"    Zberezheno: {output_path}")

    def execute(self):
        """Main execution"""
        print("="*70)
        print("HLYBOKYI ANALIZ KRESLENNNIA")
        print("="*70)

        self.connect()
        self.load_silos()
        self.analyze_all_objects()

        silo_assignments, unassigned = self.assign_to_silos()
        connections = self.find_connections(silo_assignments)

        self.save_results(silo_assignments, connections)

        print(f"\n{'='*70}")
        print("ANALIZ ZAVERSHENYI!")
        print(f"{'='*70}")


def main():
    try:
        analyzer = DeepAnalyzer()
        analyzer.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
