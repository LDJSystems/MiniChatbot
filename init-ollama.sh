#!/bin/sh
echo "Esperando a que el servicio de Ollama esté disponible..."
until curl -s http://ollama:11434/api/tags > /dev/null; do
  sleep 2
done

echo "Ollama está listo. Verificando/descargando modelo qwen2.5:1.5b-instruct..."
curl -X POST http://ollama:11434/api/pull -d '{"name": "qwen2.5:1.5b-instruct"}'
echo "Modelo configurado correctamente."