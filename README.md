# translate-api

A powerful, self-hosted translation API using Argos Translate.

## Features

- **High-Performance:** Built with Flask for fast and reliable translations.
- **Offline Mode:** Download models once and run the API completely offline.
- **Extensible:** Easily add new language models.
- **Secure:** Protect your endpoints with an API key.
- **Dockerized:** Simple setup and deployment with Docker and Docker Compose.

## Getting Started

### Prerequisites

- Docker
- Docker Compose
```docker-compose.yml
version: "3.9"
services:
  translate:
    image: ghcr.io/lane-fullstack/translate-api:latest
    container_name: translate-api
    ports:
      - "5050:5050"
    volumes:
      - ./translate-api/models:/app/models
      - ./translate-api/config.yaml:/app/config.yaml:ro
    restart: unless-stopped

```

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/translate-api.git
    cd translate-api
    ```

2.  **Configure API Key:**
    Edit `config.yaml` and set your secret API key:
    ```yaml
    api_key: "your_secret_key_here"
    ```

3.  **Run with Docker Compose:**
    The recommended way to run the service is using Docker Compose. This will mount the `models` and `config.yaml` files, ensuring persistence and custom configuration.

    ```bash
    docker-compose up -d --build
    ```
    The API will be available at `http://localhost:5050`.

## API Usage

All protected endpoints require an API key. You can provide it in two ways:

-   **Header (Recommended):** `X-API-KEY: your_secret_key_here`
-   **URL Parameter:** `?key=your_secret_key_here`

---

### 1. Translate Text

#### `POST /translate`

Translates a single text or a batch of texts.

**Single Text Translation:**

```bash
curl -X POST http://localhost:5050/translate \
     -H "Content-Type: application/json" \
     -H "X-API-KEY: your_secret_key_here" \
     -d '{
           "text": "Hello, world!",
           "source": "en",
           "target": "es"
         }'
```

**Batch Text Translation:**

```bash
curl -X POST http://localhost:5050/translate \
     -H "Content-Type: application/json" \
     -H "X-API-KEY: your_secret_key_here" \
     -d '{
           "texts": ["Hello", "How are you?"],
           "source": "en",
           "target": "zh"
         }'
```

---

### 2. Translate to Multiple Languages

#### `POST /translate/multi`

Translates a single text into multiple target languages.

```bash
curl -X POST http://localhost:5050/translate/multi \
     -H "Content-Type: application/json" \
     -H "X-API-KEY: your_secret_key_here" \
     -d '{
           "text": "This is a powerful translation API.",
           "source": "en",
           "targets": ["zh", "es", "fr"]
         }'
```

---

### 3. Detect Language

#### `POST /detect`

Detects the language of a given text.

```bash
curl -X POST http://localhost:5050/detect \
     -H "Content-Type: application/json" \
     -H "X-API-KEY: your_secret_key_here" \
     -d '{"text": "你好世界"}'
```

---

### 4. List Languages

#### `GET /languages`

Returns a list of installed and available (installable) languages.

```bash
curl -X GET "http://localhost:5050/languages?key=your_secret_key_here"
```

---

### 5. List Installed Models

#### `GET /models`

Returns a list of all installed translation model pairs.

```bash
curl -X GET "http://localhost:5050/models?key=your_secret_key_here"
```

---

### 6. Install a Model

#### `POST /models/install`

Downloads and installs a specific language model pair. This is a synchronous operation.

```bash
curl -X POST http://localhost:5050/models/install \
     -H "Content-Type: application/json" \
     -H "X-API-KEY: your_secret_key_here" \
     -d '{
           "from": "fr",
           "to": "en"
         }'
```

---

### 7. Install All Models

#### `GET /models/install-all`

Triggers a background job to download and install all available models that are not yet installed. It returns immediately with a list of models queued for installation.

```bash
curl -X GET "http://localhost:5050/models/install-all?key=your_secret_key_here"
```

---

### 8. Health Check

#### `GET /health`

A public endpoint to check if the service is running. Does not require an API key.

```bash
curl -X GET http://localhost:5050/health
```

---

### 9. Service Info

#### `GET /info`

Returns information about the service.

```bash
curl -X GET "http://localhost:5050/info?key=your_secret_key_here"
```

## Offline Models

You can manually download language models from the [Argos PM Index](https://www.argosopentech.com/argospm/index/) and place the `.argosmodel` files in the `./models` directory before starting the service.

---
*Thanks to the [Argos-Translate](https://github.com/argosopentech/argos-translate) project.*
