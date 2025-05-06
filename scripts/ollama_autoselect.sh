#!/bin/bash
# Automatyczny wybór i test najmniejszego modelu Ollama do 3B

set -e

# Lista lekkich modeli do przetestowania (max 3B)
MODELS=("phi3" "tinyllama" "llama2:3b" "codegemma:2b" "stablelm2:1_6b")

# Funkcja testująca model
function test_model() {
    local model="$1"
    echo "Testuję model: $model..."
    ollama pull "$model" || return 1
    START=$(date +%s)
    OUT=$(ollama run "$model" "Hello" 2>&1)
    END=$(date +%s)
    DURATION=$((END-START))
    if echo "$OUT" | grep -qi "hello"; then
        echo "Model $model działa! (czas odpowiedzi: ${DURATION}s)"
        echo "$model" > scripts/ollama_selected_model.txt
        return 0
    else
        echo "Model $model NIE działa lub odpowiedź niepoprawna."
        return 1
    fi
}

for model in "${MODELS[@]}"; do
    if test_model "$model"; then
        echo "Wybrano model: $model"
        exit 0
    fi
    echo "Próbuję kolejny model..."
done

echo "Nie udało się uruchomić żadnego modelu do 3B. Sprawdź zasoby lub zainstaluj Ollama."
exit 1
