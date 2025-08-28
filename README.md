# TempTracker

Track the temperature of coolers in multiple locations.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the Flask development server:
   ```bash
   python app.py
   ```
3. Visit `http://localhost:5000` in your browser.

The default admin password is `admin`. You can override it with the `ADMIN_PASSWORD` environment variable.

### .env support

This app loads environment variables from a `.env` file in the project root if present (via `python-dotenv`). Copy `.env.example` to `.env` and adjust values:

```
ADMIN_PASSWORD=change-me
FLASK_PORT=5000
SECRET_KEY=dev
```

Then run the app normally (`python app.py`).

## Docker

Build the image:

```
docker build -t temptracker .
```

Run the container (port 5000):

```
docker run --rm \
  -e ADMIN_PASSWORD=change-me \
  -e FLASK_PORT=5000 \
  -p 5000:5000 \
  temptracker
```

Customize the port by setting `FLASK_PORT` and mapping accordingly, for example `-e FLASK_PORT=8080 -p 8080:8080`.

Persistence (optional):

```
# Persist uploads and database to the host
mkdir -p ./data/uploads
touch ./data/app.db

docker run --rm \
  -e ADMIN_PASSWORD=change-me \
  -e FLASK_PORT=5000 \
  -p 5000:5000 \
  -v ${PWD}/data/app.db:/app/app.db \
  -v ${PWD}/data/uploads:/app/static/uploads \
  temptracker

## Docker Compose

Create a `.env` file (or use the provided `.env.example`) to set variables like `ADMIN_PASSWORD` and `FLASK_PORT`, then run:

```
docker compose up --build
```

This will:
- Build the image from the Dockerfile
- Map `${FLASK_PORT}` (default 5000) to the same port on the host
- Persist `app.db` and uploads under `./data/`

Example `.env`:

```
ADMIN_PASSWORD=change-me
FLASK_PORT=5000
SECRET_KEY=dev
```

To stop:

```
docker compose down
```
```


## Styling

The app uses [Bootstrap](https://getbootstrap.com/) via CDN for layout and components.
A cohesive color palette is defined with CSS variables in `static/style.css`:

```css
:root {
  --color-primary: #0d6efd;
  --color-secondary: #6c757d;
  --color-accent: #198754;
  --color-bg: #f8f9fa;
  --color-text: #212529;
}
```

Use these variables in custom styles to keep colors consistent across the application.
