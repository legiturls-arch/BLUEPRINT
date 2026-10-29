BLUEPRINT 3D Robot Builder setup

1. Copy builder.html, builder.css and builder.js into D:\BLUEPRINT\frontend
2. Keep your existing index.html, style.css, script.js and app.py unchanged.
3. Start the server from D:\BLUEPRINT:
   .\.venv\Scripts\python.exe -m uvicorn app:app --reload
4. Open:
   http://127.0.0.1:8000/ui/builder.html

This assumes your app.py already mounts the frontend directory at /ui using FastAPI StaticFiles.
The browser needs internet access to load Three.js from jsDelivr.

Limits: this is a visual assembly prototype with simple geometry. It does not enforce joints or
collisions. Simulation submits aggregate mass, motor count/torque and wheel radius to your existing
simplified API; it does not yet validate motor-wheel connections, traction, drivetrain losses or
real-world performance.
