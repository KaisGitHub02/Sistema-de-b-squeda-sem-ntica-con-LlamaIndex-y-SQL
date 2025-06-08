# 🧠 Sistema de Búsqueda Semántica

Este proyecto implementa un sistema de búsqueda semántica utilizando modelos de lenguaje, embeddings y una base de datos relacional para analíticas y gestión de metadatos.

---

## 📐 Arquitectura

- **[LlamaIndex](https://github.com/jerryjliu/llama_index)** para indexación y búsqueda vectorial
- **[SQLAlchemy](https://www.sqlalchemy.org/)** para manejar metadatos y analíticas
- **[Hugging Face Transformers](https://huggingface.co/)** para generar embeddings semánticos
- **SQLite** para almacenamiento local (puede reemplazarse por otros motores)

---

## 🔧 Componentes Principales

- `SemanticSearchSystem`: Clase principal del sistema
- `DocumentMetadata`: Modelo de base de datos para almacenar metadatos
- `SearchQuery`: Modelo para registrar y analizar búsquedas

---

## 🔁 Flujo de Trabajo

1. **Agregar documentos:**  
   Utiliza `add_document()` para cargar contenido.

2. **Construir el índice:**  
   Llama a `build_index()` para generar el índice semántico.

3. **Realizar búsquedas:**  
   Usa `search()` para ejecutar consultas.

4. **Analizar resultados:**  
   Consulta `get_analytics()` para ver estadísticas y uso.

---

![image](https://github.com/user-attachments/assets/43e97730-f117-4bd8-8676-e07553697213)


## ✅ Buenas Prácticas

- Registro detallado con `logging`
- Manejo robusto de errores (`try/except`)
- Separación clara de responsabilidades
- Código documentado con docstrings
- Pruebas unitarias básicas incluidas
- Soporte opcional para interfaz de usuario (Gradio)

---

## 🚀 Posibles Extensiones

- Soporte para más tipos de archivo (.pdf, .docx, .html, etc.)
- Mejora de embeddings con modelos más potentes
- Agrupamiento (clustering) de documentos
- Integración de análisis de sentimientos
- Exportación de resultados (CSV, JSON, etc.)

---

## 🏗️ Configuración para Producción

- Reemplazar SQLite por PostgreSQL
- Agregar caché para resultados frecuentes
- Autenticación y permisos
- Optimización de rendimiento para grandes volúmenes
- Implementación de CI/CD y despliegue automatizado

---

## 🧪 Cómo Usar

1. Ejecuta todas las celdas del notebook en orden.
2. El sistema se inicializa automáticamente.
3. Usa `system.add_document()` para agregar contenido.
4. Ejecuta `system.search()` para hacer búsquedas.
5. Si lo deseas, lanza la interfaz web con **Gradio**.

---


