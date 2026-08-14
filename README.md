# AgroGuardian ESP32 Test Live

Backend temporário de dispositivo único. A única chave aceita é `278088d6-b723-45eb-8005-e7dc4b9e00ab`.

## Rotas

- `GET /health`
- `POST /api/live/request/{device_key}`
- `GET /api/live/status?device_key={device_key}`
- `POST /api/live/frame` com `device_key` e `file` JPEG
- `GET /api/live/stream/{device_key}`

Depois da publicação, o firmware deve usar a nova URL pública como `API_BASE_URL`.
