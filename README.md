# REST API for Question Answering with ITMO University Assistant

This project provides a REST API service for answering questions related to ITMO University. The service uses a machine learning model to process questions and provide concise answers in JSON format.

---

## Features
- Accepts questions in Russian.
- Provides responses in JSON format.
- Supports answering multiple-choice questions.
- Hosted on a publicly accessible server.

---

## How to Use the API

### Endpoint
`POST /api/request`

### Request Format
The API expects a JSON payload with the following fields:
- `query` (string): The question you want to ask.
- `id` (integer): A unique identifier for the request.

### Example Request
You can use the following `curl` command to send a request to the API:

```bash
curl --location --request POST 'http://89.105.223.133:8080/api/request' \
--header 'Content-Type: application/json' \
--data-raw '{
  "query": "В каком городе находится главный кампус Университета ИТМО?\n1. Москва\n2. Санкт-Петербург\n3. Екатеринбург\n4. Нижний Новгород",
  "id": 1
}'
