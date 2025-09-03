import requests
requests.post("http://localhost:11434/api/generate", json={
  "model": "gpt-oss:20b",
  "prompt": "test",
  "options": { "num_gpu": 999 },   # просим максимум слоев в GPU
  "keep_alive": 0                  # выгрузить после ответа (удобно для смены конфигурации)
})
