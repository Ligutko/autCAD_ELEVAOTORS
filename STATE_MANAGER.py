# -*- coding: utf-8 -*-
"""
STATE MANAGER - Система управління станом
Запобігає повторному масштабуванню та відстежує всі операції
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


class StateManager:
    """Manages processing state to prevent repeated operations"""

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.state_file = self.project_dir / "processing_state.json"
        self.originals_dir = self.project_dir / "ORIGINALS"
        self.working_dir = self.project_dir / "WORKING"
        self.results_dir = self.project_dir / "RESULTS"
        self.state = None

    def initialize(self):
        """Initialize directory structure and state file"""
        print("="*70)
        print("ІНІЦІАЛІЗАЦІЯ STATE MANAGER")
        print("="*70)

        # Create directories
        self.originals_dir.mkdir(exist_ok=True)
        self.working_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)

        print(f"\n✅ Директорії створено:")
        print(f"   ORIGINALS: {self.originals_dir}")
        print(f"   WORKING:   {self.working_dir}")
        print(f"   RESULTS:   {self.results_dir}")

        # Load or create state
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
            print(f"\n✅ State файл завантажено: {self.state_file}")
        else:
            self.state = {
                "created": datetime.now().isoformat(),
                "files": {},
                "operations": []
            }
            self._save_state()
            print(f"\n✅ Новий state файл створено: {self.state_file}")

    def _save_state(self):
        """Save state to file"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def preserve_original(self, source_file):
        """Copy source file to ORIGINALS if not already there"""
        source_path = Path(source_file)

        if not source_path.exists():
            raise FileNotFoundError(f"Файл не знайдено: {source_file}")

        # Check if original already exists
        original_name = f"ORIGINAL_{source_path.name}"
        original_path = self.originals_dir / original_name

        if original_path.exists():
            print(f"\n⚠ Оригінал вже існує: {original_name}")
            return original_path

        # Copy to originals
        shutil.copy2(source_path, original_path)
        print(f"\n✅ Оригінал збережено: {original_name}")

        # Record in state
        file_key = source_path.stem
        self.state["files"][file_key] = {
            "original_path": str(original_path),
            "original_created": datetime.now().isoformat(),
            "processed": False,
            "operations_applied": []
        }
        self._save_state()

        return original_path

    def create_working_copy(self, file_key):
        """Create working copy from original"""
        if file_key not in self.state["files"]:
            raise ValueError(f"Файл не знайдено в state: {file_key}")

        original_path = Path(self.state["files"][file_key]["original_path"])

        if not original_path.exists():
            raise FileNotFoundError(f"Оригінал не знайдено: {original_path}")

        # Create working copy
        working_name = f"WORKING_{original_path.name}"
        working_path = self.working_dir / working_name

        shutil.copy2(original_path, working_path)
        print(f"\n✅ Робоча копія створена: {working_name}")

        return working_path

    def is_processed(self, file_key):
        """Check if file has been processed"""
        if file_key not in self.state["files"]:
            return False

        return self.state["files"][file_key].get("processed", False)

    def can_apply_operation(self, file_key, operation_name):
        """Check if operation can be applied (hasn't been applied yet)"""
        if file_key not in self.state["files"]:
            return False

        operations = self.state["files"][file_key].get("operations_applied", [])

        # Check if this operation was already applied
        for op in operations:
            if op["name"] == operation_name:
                print(f"\n⚠ ПОПЕРЕДЖЕННЯ: Операція '{operation_name}' вже застосована!")
                print(f"   Дата: {op['timestamp']}")
                return False

        return True

    def record_operation(self, file_key, operation_name, details=None):
        """Record that operation was applied"""
        if file_key not in self.state["files"]:
            raise ValueError(f"Файл не знайдено в state: {file_key}")

        operation = {
            "name": operation_name,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }

        self.state["files"][file_key]["operations_applied"].append(operation)
        self.state["operations"].append({
            "file_key": file_key,
            **operation
        })

        self._save_state()

        print(f"\n✅ Операція записана: {operation_name}")

    def mark_processed(self, file_key):
        """Mark file as fully processed"""
        if file_key not in self.state["files"]:
            raise ValueError(f"Файл не знайдено в state: {file_key}")

        self.state["files"][file_key]["processed"] = True
        self.state["files"][file_key]["processed_timestamp"] = datetime.now().isoformat()

        self._save_state()

        print(f"\n✅ Файл позначено як оброблений: {file_key}")

    def save_result(self, working_file, file_key):
        """Save working file to results"""
        working_path = Path(working_file)

        if not working_path.exists():
            raise FileNotFoundError(f"Робочий файл не знайдено: {working_file}")

        # Create result filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_name = f"RESULT_{timestamp}_{working_path.name}"
        result_path = self.results_dir / result_name

        shutil.copy2(working_path, result_path)
        print(f"\n✅ Результат збережено: {result_name}")

        # Record in state
        self.state["files"][file_key]["result_path"] = str(result_path)
        self.state["files"][file_key]["result_timestamp"] = datetime.now().isoformat()
        self._save_state()

        return result_path

    def get_file_info(self, file_key):
        """Get file processing information"""
        if file_key not in self.state["files"]:
            return None

        return self.state["files"][file_key]

    def print_status(self):
        """Print current state status"""
        print("\n" + "="*70)
        print("ПОТОЧНИЙ СТАН")
        print("="*70)

        print(f"\nВсього файлів в системі: {len(self.state['files'])}")
        print(f"Всього операцій: {len(self.state['operations'])}")

        print("\n" + "-"*70)
        print("ФАЙЛИ:")
        print("-"*70)

        for file_key, info in self.state["files"].items():
            status = "✅ ОБРОБЛЕНО" if info.get("processed") else "⏳ В РОБОТІ"
            print(f"\n{status} {file_key}")
            print(f"  Оригінал: {Path(info['original_path']).name}")

            ops = info.get("operations_applied", [])
            if ops:
                print(f"  Операції ({len(ops)}):")
                for op in ops:
                    print(f"    - {op['name']} ({op['timestamp'][:19]})")
            else:
                print(f"  Операції: немає")

        print("\n" + "="*70)


def main():
    """Test state manager"""

    manager = StateManager("d:/autocad project")
    manager.initialize()

    manager.print_status()

    print("\n" + "="*70)
    print("STATE MANAGER ГОТОВИЙ ДО РОБОТИ!")
    print("="*70)


if __name__ == "__main__":
    main()
