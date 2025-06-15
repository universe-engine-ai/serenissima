import uvicorn
import os
import sys # Importer sys pour la manipulation de sys.path
import datetime
import threading

# Ajouter le répertoire racine du projet à sys.path
# os.path.dirname(__file__) est C:\Users\reyno\serenissima\backend
# os.path.join(..., '..') est C:\Users\reyno\serenissima
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the thinking loop
from backend.ais.thinkingLoop import main as thinking_loop_main

def start_thinking_loop():
    """Start the thinking loop in a separate thread."""
    print("Starting thinking loop in a separate thread...")
    thinking_thread = threading.Thread(target=thinking_loop_main)
    thinking_thread.daemon = True  # Set as daemon so it exits when the main thread exits
    thinking_thread.start()
    print(f"Thinking loop started in thread {thinking_thread.ident}")

if __name__ == "__main__":
    # Get port from environment variable with fallback to 10000
    port = int(os.environ.get("PORT", 10000))
    
    # Log the port we're using
    print(f"Starting server on port {port}")
    
    # Start the thinking loop
    start_thinking_loop()
    
    # Utiliser la chaîne d'application correcte et le port de la variable d'environnement
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
