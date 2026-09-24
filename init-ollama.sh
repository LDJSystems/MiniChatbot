#!/bin/sh
echo "Esperando a que el servicio de Ollama esté disponible..."
until curl -s http://ollama:11434/api/tags > /dev/null; do
  sleep 2
done

echo "Ollama está listo. Verificando/descargando modelo llama3.2:3b..."
curl -X POST http://ollama:11434/api/pull -d '{"name": "llama3.2:3b"}'
echo "Modelo configurado correctamente."