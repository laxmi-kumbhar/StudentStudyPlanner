import os
from backend import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n==================================================")
    print("  [*] Student Study Planner Server Running!")
    print(f"  [>] Open URL: http://127.0.0.1:{port}")
    print("==================================================\n")
    app.run(host=os.environ.get('HOST', '0.0.0.0'), port=port, debug=True)
