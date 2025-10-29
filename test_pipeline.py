#!/usr/bin/env python3
"""
Script de prueba para el pipeline de limpieza de datos.

Este script demuestra cómo usar los nuevos endpoints del pipeline.
"""

import requests
import sys
from pathlib import Path


BASE_URL = "http://localhost:8000"


def test_health():
    """Verificar que el servidor esté corriendo."""
    print("🔍 Verificando servidor...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        print("✅ Servidor corriendo correctamente\n")
        return True
    except Exception as e:
        print(f"❌ Error: Servidor no disponible - {e}")
        print("   Asegúrate de ejecutar: uvicorn app.main:app --reload\n")
        return False


def test_pipeline_status():
    """Verificar el estado del pipeline."""
    print("📊 Verificando estado del pipeline...")
    try:
        response = requests.get(f"{BASE_URL}/pipeline/status")
        response.raise_for_status()
        data = response.json()
        
        print(f"   Archivos procesados: {data['archivos_procesados']}/{data['total_complejidades']}")
        print(f"   Storage type: {data['storage_type']}")
        
        for complejidad, info in data['complejidades'].items():
            if info.get('procesado'):
                filas = info.get('filas', 'N/A')
                print(f"   ✅ {complejidad}: {filas} filas")
            else:
                print(f"   ⏳ {complejidad}: No procesada")
        
        print()
        return data
    except Exception as e:
        print(f"❌ Error al verificar estado: {e}\n")
        return None


def test_process_excel(excel_path: str):
    """Procesar un archivo Excel."""
    print(f"📤 Procesando Excel: {excel_path}")
    
    if not Path(excel_path).exists():
        print(f"❌ Error: Archivo no encontrado: {excel_path}\n")
        return None
    
    try:
        with open(excel_path, 'rb') as f:
            files = {'file': (Path(excel_path).name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(f"{BASE_URL}/pipeline/process-excel", files=files, timeout=300)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ {data['message']}")
            print(f"   Timestamp: {data['timestamp']}")
            print("\n   Complejidades procesadas:")
            for complejidad, status in data['complejidades_procesadas'].items():
                print(f"   - {complejidad}: {status}")
            
            if data['archivos_generados']:
                print("\n   Archivos generados:")
                for complejidad, path in data['archivos_generados'].items():
                    stats = data['estadisticas'][complejidad]
                    print(f"   - {path}")
                    print(f"     {stats['filas']} filas x {stats['columnas']} columnas")
            
            print()
            return data
            
    except requests.exceptions.Timeout:
        print("❌ Error: Timeout (el archivo puede ser muy grande)\n")
        return None
    except Exception as e:
        print(f"❌ Error al procesar Excel: {e}\n")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Detalle: {error_detail.get('detail', 'N/A')}\n")
            except:
                pass
        return None


def test_download_csv(complejidad: str, output_path: str = None):
    """Descargar CSV de una complejidad."""
    print(f"📥 Descargando CSV: {complejidad}")
    
    try:
        response = requests.get(f"{BASE_URL}/pipeline/download/{complejidad}")
        response.raise_for_status()
        
        if output_path is None:
            output_path = f"{complejidad}.csv"
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Guardado en: {output_path}\n")
        return True
        
    except Exception as e:
        print(f"❌ Error al descargar: {e}\n")
        return False


def test_download_all(output_path: str = "complejidades_procesadas.zip"):
    """Descargar todos los CSVs."""
    print("📦 Descargando todos los CSVs...")
    
    try:
        response = requests.get(f"{BASE_URL}/pipeline/download-all")
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ ZIP guardado en: {output_path}\n")
        return True
        
    except Exception as e:
        print(f"❌ Error al descargar ZIP: {e}\n")
        return False


def main():
    """Ejecutar todas las pruebas."""
    print("=" * 60)
    print("Pipeline de Limpieza de Datos - Pruebas")
    print("=" * 60)
    print()
    
    # 1. Verificar servidor
    if not test_health():
        sys.exit(1)
    
    # 2. Verificar estado inicial
    test_pipeline_status()
    
    # 3. Si hay argumentos, procesar Excel
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
        result = test_process_excel(excel_path)
        
        if result:
            # 4. Verificar estado después del procesamiento
            print("\n" + "=" * 60)
            test_pipeline_status()
            
            # 5. Descargar un CSV de ejemplo
            if result['archivos_generados']:
                primera_complejidad = list(result['archivos_generados'].keys())[0]
                test_download_csv(primera_complejidad)
            
            # 6. Descargar todos los CSVs
            test_download_all()
    else:
        print("💡 Para procesar un Excel, ejecuta:")
        print(f"   python {sys.argv[0]} ruta/al/archivo.xlsx\n")
    
    print("=" * 60)
    print("✅ Pruebas completadas")
    print("=" * 60)


if __name__ == "__main__":
    main()

