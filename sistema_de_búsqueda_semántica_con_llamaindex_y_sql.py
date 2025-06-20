# -*- coding: utf-8 -*-
"""Sistema de búsqueda semántica con LlamaIndex y SQL.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1y989cPapG2JI84e4xGLp8jLSrdSKCkq1
"""

# Sistema de Búsqueda Semántica con LlamaIndex y SQL
# Proyecto completo para Google Colab

# =============================================================================
# INSTALACIÓN DE DEPENDENCIAS
# =============================================================================

# Instalar todas las dependencias necesarias
!pip install llama-index llama-index-embeddings-huggingface
!pip install sqlalchemy pandas numpy matplotlib seaborn
!pip install sentence-transformers transformers torch
!pip install pytest pytest-cov python-dotenv
!pip install gradio

# =============================================================================
# IMPORTACIONES Y CONFIGURACIÓN
# =============================================================================

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Any
import json
import logging
from pathlib import Path

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN DE API Y MODELOS
# =============================================================================

# Tu API key de Hugging Face
HF_API_KEY = "hf_OCOhRXKbIygHzfxbKvXbAaKJEfCmEXXXXX"
os.environ["HUGGINGFACE_API_KEY"] = HF_API_KEY

# Configuración de modelos
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Configurar LlamaIndex - Solo embedding model
Settings.embed_model = HuggingFaceEmbedding(
    model_name=EMBEDDING_MODEL,
    trust_remote_code=True
)

# =============================================================================
# MODELOS DE BASE DE DATOS
# =============================================================================

Base = declarative_base()

class DocumentMetadata(Base):
    """Modelo para almacenar metadatos de documentos"""
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(String(1000))
    file_type = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    word_count = Column(Integer)
    embedding_model = Column(String(100))

    def to_dict(self):
        return {
            'id': self.id,
            'doc_id': self.doc_id,
            'title': self.title,
            'content': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'created_at': self.created_at,
            'word_count': self.word_count
        }

class SearchQuery(Base):
    """Modelo para almacenar consultas de búsqueda"""
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    results_count = Column(Integer)
    avg_similarity = Column(Float)
    execution_time = Column(Float)

# =============================================================================
# CLASE PRINCIPAL DEL SISTEMA
# =============================================================================

class SemanticSearchSystem:
    """Sistema principal de búsqueda semántica"""

    def __init__(self, db_path: str = "semantic_search.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Inicializar componentes de LlamaIndex
        self.vector_store = SimpleVectorStore()
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = None
        self.documents = []

        logger.info(f"Sistema inicializado con base de datos: {db_path}")

    def get_db_session(self) -> Session:
        """Obtener sesión de base de datos"""
        return self.SessionLocal()

    def add_document(self, title: str, content: str, file_path: str = None,
                    file_type: str = None) -> str:
        """Agregar un documento al sistema"""
        try:
            # Generar ID único para el documento
            doc_id = f"doc_{len(self.documents) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Crear documento de LlamaIndex
            document = Document(
                text=content,
                doc_id=doc_id,
                metadata={
                    "title": title,
                    "file_path": file_path,
                    "file_type": file_type,
                    "created_at": datetime.now().isoformat()
                }
            )

            self.documents.append(document)

            # Guardar metadatos en SQL
            with self.get_db_session() as session:
                doc_metadata = DocumentMetadata(
                    doc_id=doc_id,
                    title=title,
                    content=content,
                    file_path=file_path,
                    file_type=file_type,
                    word_count=len(content.split()),
                    embedding_model=EMBEDDING_MODEL
                )
                session.add(doc_metadata)
                session.commit()

            logger.info(f"Documento agregado: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Error al agregar documento: {e}")
            raise

    def build_index(self):
        """Construir el índice de vectores"""
        try:
            if not self.documents:
                logger.warning("No hay documentos para indexar")
                return

            # Parsear documentos en nodos
            parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
            nodes = parser.get_nodes_from_documents(self.documents)

            # Crear índice
            self.index = VectorStoreIndex(
                nodes,
                storage_context=self.storage_context
            )

            logger.info(f"Índice construido con {len(nodes)} nodos")

        except Exception as e:
            logger.error(f"Error al construir índice: {e}")
            raise

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Realizar búsqueda semántica"""
        try:
            start_time = datetime.now()

            if not self.index:
                logger.error("Índice no construido. Ejecute build_index() primero")
                return []

            # Realizar búsqueda usando retriever
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)

            # Procesar resultados
            results = []
            similarities = []

            for node in nodes:
                # Obtener metadatos del documento
                doc_id = node.metadata.get('doc_id', 'unknown')

                with self.get_db_session() as session:
                    doc_metadata = session.query(DocumentMetadata).filter(
                        DocumentMetadata.doc_id == doc_id
                    ).first()

                # Calcular score de similitud (si está disponible)
                similarity_score = getattr(node, 'score', 0.0)

                result = {
                    'doc_id': doc_id,
                    'title': node.metadata.get('title', 'Sin título'),
                    'content': node.text,
                    'similarity_score': similarity_score,
                    'metadata': dict(node.metadata)
                }

                if doc_metadata:
                    result.update({
                        'file_path': doc_metadata.file_path,
                        'file_type': doc_metadata.file_type,
                        'created_at': doc_metadata.created_at,
                        'word_count': doc_metadata.word_count
                    })

                results.append(result)
                similarities.append(similarity_score)

            # Calcular métricas
            execution_time = (datetime.now() - start_time).total_seconds()
            avg_similarity = np.mean(similarities) if similarities else 0.0

            # Guardar consulta en base de datos
            with self.get_db_session() as session:
                search_query = SearchQuery(
                    query_text=query,
                    results_count=len(results),
                    avg_similarity=avg_similarity,
                    execution_time=execution_time
                )
                session.add(search_query)
                session.commit()

            logger.info(f"Búsqueda completada en {execution_time:.2f}s con {len(results)} resultados")
            return results

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []

    def get_document_stats(self) -> Dict:
        """Obtener estadísticas de documentos"""
        with self.get_db_session() as session:
            total_docs = session.query(func.count(DocumentMetadata.id)).scalar()
            total_words = session.query(func.sum(DocumentMetadata.word_count)).scalar() or 0

            file_types = session.query(
                DocumentMetadata.file_type,
                func.count(DocumentMetadata.id)
            ).group_by(DocumentMetadata.file_type).all()

            return {
                'total_documents': total_docs,
                'total_words': total_words,
                'file_types': dict(file_types),
                'embedding_model': EMBEDDING_MODEL
            }

    def get_search_analytics(self) -> Dict:
        """Obtener analíticas de búsquedas"""
        with self.get_db_session() as session:
            total_searches = session.query(func.count(SearchQuery.id)).scalar()
            avg_execution_time = session.query(func.avg(SearchQuery.execution_time)).scalar() or 0
            avg_results = session.query(func.avg(SearchQuery.results_count)).scalar() or 0

            recent_queries = session.query(SearchQuery).order_by(
                SearchQuery.timestamp.desc()
            ).limit(10).all()

            return {
                'total_searches': total_searches,
                'avg_execution_time': round(avg_execution_time, 3),
                'avg_results_per_search': round(avg_results, 1),
                'recent_queries': [q.query_text for q in recent_queries]
            }

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def load_sample_documents(system: SemanticSearchSystem):
    """Cargar documentos de ejemplo"""
    sample_docs = [
        {
            "title": "Introducción a la Inteligencia Artificial",
            "content": """La Inteligencia Artificial (IA) es una rama de la informática que busca crear
            sistemas capaces de realizar tareas que normalmente requieren inteligencia humana.
            Esto incluye el aprendizaje, el razonamiento, la percepción, y la comprensión del lenguaje natural.
            Los algoritmos de machine learning son fundamentales para el desarrollo de sistemas de IA modernos.""",
            "file_type": "text"
        },
        {
            "title": "Procesamiento de Lenguaje Natural",
            "content": """El Procesamiento de Lenguaje Natural (PLN) es un subcampo de la IA que se centra
            en la interacción entre computadoras y lenguaje humano. Incluye tareas como análisis de sentimientos,
            traducción automática, generación de texto y búsqueda semántica. Los modelos de transformers
            han revolucionado el campo del PLN en los últimos años.""",
            "file_type": "text"
        },
        {
            "title": "Machine Learning y Deep Learning",
            "content": """El Machine Learning es un método de análisis de datos que automatiza la construcción
            de modelos analíticos. El Deep Learning, un subconjunto del machine learning, utiliza redes neuronales
            con múltiples capas para modelar y entender datos complejos. Estas técnicas son especialmente útiles
            para reconocimiento de patrones, visión por computadora y procesamiento de lenguaje natural.""",
            "file_type": "text"
        },
        {
            "title": "Sistemas de Recomendación",
            "content": """Los sistemas de recomendación son algoritmos que sugieren elementos relevantes a los usuarios,
            como productos, películas, o contenido. Utilizan técnicas como filtrado colaborativo,
            filtrado basado en contenido, y métodos híbridos. Estos sistemas son fundamentales en plataformas
            como Netflix, Amazon, y Spotify para personalizar la experiencia del usuario.""",
            "file_type": "text"
        },
        {
            "title": "Bases de Datos y Big Data",
            "content": """Las bases de datos relacionales han sido el estándar para almacenar información estructurada
            durante décadas. Sin embargo, con el crecimiento del Big Data, han surgido nuevas tecnologías como
            bases de datos NoSQL, sistemas distribuidos, y herramientas de procesamiento en tiempo real.
            Estas tecnologías permiten manejar volúmenes masivos de datos con alta velocidad y variedad.""",
            "file_type": "text"
        }
    ]

    for doc in sample_docs:
        system.add_document(
            title=doc["title"],
            content=doc["content"],
            file_type=doc["file_type"]
        )

    print("Documentos de ejemplo cargados exitosamente")

def run_sample_searches(system: SemanticSearchSystem):
    """Ejecutar búsquedas de ejemplo"""
    sample_queries = [
        "¿Qué es inteligencia artificial?",
        "machine learning y redes neuronales",
        "sistemas de recomendación Netflix",
        "bases de datos NoSQL",
        "procesamiento lenguaje natural transformers"
    ]

    print("\n" + "="*50)
    print("EJECUTANDO BÚSQUEDAS DE EJEMPLO")
    print("="*50)

    for query in sample_queries:
        print(f"\n🔍 Consulta: '{query}'")
        print("-" * 40)

        results = system.search(query, top_k=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   Contenido: {result['content'][:100]}...")
                print(f"   Similitud: {result['similarity_score']:.3f}")
                print()
        else:
            print("No se encontraron resultados.")

def display_analytics(system: SemanticSearchSystem):
    """Mostrar analíticas del sistema"""
    print("\n" + "="*50)
    print("ANALÍTICAS DEL SISTEMA")
    print("="*50)

    # Estadísticas de documentos
    doc_stats = system.get_document_stats()
    print(f"📚 Total de documentos: {doc_stats['total_documents']}")
    print(f"📝 Total de palabras: {doc_stats['total_words']:,}")
    print(f"🔧 Modelo de embeddings: {doc_stats['embedding_model']}")

    if doc_stats['file_types']:
        print(f"📂 Tipos de archivo:")
        for file_type, count in doc_stats['file_types'].items():
            print(f"   - {file_type or 'Desconocido'}: {count}")

    # Analíticas de búsquedas
    search_stats = system.get_search_analytics()
    print(f"\n🔍 Total de búsquedas: {search_stats['total_searches']}")
    print(f"⏱️  Tiempo promedio: {search_stats['avg_execution_time']:.3f}s")
    print(f"📊 Resultados promedio: {search_stats['avg_results_per_search']}")

    if search_stats['recent_queries']:
        print(f"\n🕒 Consultas recientes:")
        for query in search_stats['recent_queries'][:5]:
            print(f"   - {query}")

# =============================================================================
# PRUEBAS UNITARIAS
# =============================================================================

def test_system_functionality():
    """Pruebas unitarias básicas del sistema"""
    print("\n" + "="*50)
    print("EJECUTANDO PRUEBAS UNITARIAS")
    print("="*50)

    # Inicializar sistema de prueba
    test_system = SemanticSearchSystem("test_semantic_search.db")

    try:
        # Prueba 1: Agregar documento
        print("✅ Prueba 1: Agregando documento...")
        doc_id = test_system.add_document(
            title="Documento de Prueba",
            content="Este es un documento de prueba para verificar el funcionamiento del sistema.",
            file_type="test"
        )
        assert doc_id is not None
        print(f"   Documento agregado con ID: {doc_id}")

        # Prueba 2: Construir índice
        print("✅ Prueba 2: Construyendo índice...")
        test_system.build_index()
        assert test_system.index is not None
        print("   Índice construido exitosamente")

        # Prueba 3: Realizar búsqueda
        print("✅ Prueba 3: Realizando búsqueda...")
        results = test_system.search("documento prueba", top_k=1)
        assert len(results) > 0
        print(f"   Se encontraron {len(results)} resultados")

        # Prueba 4: Estadísticas
        print("✅ Prueba 4: Obteniendo estadísticas...")
        stats = test_system.get_document_stats()
        assert stats['total_documents'] > 0
        print(f"   Total de documentos: {stats['total_documents']}")

        print("\n🎉 Todas las pruebas pasaron exitosamente!")

    except Exception as e:
        print(f"❌ Error en las pruebas: {e}")
        raise

    finally:
        # Limpiar base de datos de prueba
        import os
        if os.path.exists("test_semantic_search.db"):
            os.remove("test_semantic_search.db")

# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

def main():
    """Función principal del sistema"""
    print("🚀 SISTEMA DE BÚSQUEDA SEMÁNTICA CON LLAMAINDEX Y SQL")
    print("=" * 60)

    # Inicializar sistema
    system = SemanticSearchSystem()

    # Cargar documentos de ejemplo
    print("\n📚 Cargando documentos de ejemplo...")
    load_sample_documents(system)

    # Construir índice
    print("\n🔧 Construyendo índice de vectores...")
    system.build_index()

    # Ejecutar búsquedas de ejemplo
    run_sample_searches(system)

    # Mostrar analíticas
    display_analytics(system)

    # Ejecutar pruebas
    test_system_functionality()

    print("\n✨ Sistema de búsqueda semántica funcionando correctamente!")
    print("💡 Puedes usar el sistema creando una instancia de SemanticSearchSystem")
    print("   y utilizando los métodos add_document(), build_index(), y search()")

# =============================================================================
# INTERFAZ INTERACTIVA (OPCIONAL)
# =============================================================================

def create_interactive_interface():
    """Crear interfaz interactiva con Gradio"""
    try:
        import gradio as gr

        # Inicializar sistema global
        global_system = SemanticSearchSystem()
        load_sample_documents(global_system)
        global_system.build_index()

        def search_interface(query, top_k):
            """Interfaz de búsqueda para Gradio"""
            if not query.strip():
                return "Por favor, ingrese una consulta de búsqueda."

            results = global_system.search(query, top_k=int(top_k))

            if not results:
                return "No se encontraron resultados para su consulta."

            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(f"""
**{i}. {result['title']}**
Similitud: {result['similarity_score']:.3f}
Contenido: {result['content'][:300]}...
---
                """)

            return "\n".join(formatted_results)

        # Crear interfaz
        interface = gr.Interface(
            fn=search_interface,
            inputs=[
                gr.Textbox(label="Consulta de búsqueda", placeholder="Ingrese su consulta aquí..."),
                gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Número de resultados")
            ],
            outputs=gr.Markdown(label="Resultados de búsqueda"),
            title="🔍 Sistema de Búsqueda Semántica",
            description="Busque en la base de conocimientos usando búsqueda semántica con LlamaIndex",
            examples=[
                ["¿Qué es inteligencia artificial?", 3],
                ["machine learning redes neuronales", 5],
                ["sistemas recomendación", 3]
            ]
        )

        return interface

    except ImportError:
        print("Gradio no está instalado. Instale con: !pip install gradio")
        return None

# =============================================================================
# EJECUCIÓN DEL SISTEMA
# =============================================================================

if __name__ == "__main__":
    # Ejecutar sistema principal
    main()

    # Crear interfaz interactiva (opcional)
    print("\n🌐 Creando interfaz web interactiva...")
    interface = create_interactive_interface()

    if interface:
        print("✅ Interfaz creada. Ejecute interface.launch() para iniciar la aplicación web.")
    else:
        print("❌ No se pudo crear la interfaz web.")

interface.launch()