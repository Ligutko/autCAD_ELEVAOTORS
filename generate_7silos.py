# -*- coding: utf-8 -*-
"""
LAUNCHER: Generate 7-silo schema
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from schema_generator import SchemaGenerator

schema_path = "d:/autocad project/structured_schema_7silos.json"

try:
    generator = SchemaGenerator(schema_path)
    generator.generate(clear=True)
except Exception as e:
    print(f"\nPOMYLKA: {e}")
    import traceback
    traceback.print_exc()
