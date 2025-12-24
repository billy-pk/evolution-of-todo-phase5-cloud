from main import app

print("Registered routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        methods = route.methods if hasattr(route, 'methods') else 'N/A'
        print(f"  {route.path} - {methods}")
