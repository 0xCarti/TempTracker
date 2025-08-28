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
