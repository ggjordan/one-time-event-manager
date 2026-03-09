from app import create_app

app = create_app()
application = app  # for WSGI servers (e.g. PythonAnywhere)

if __name__ == "__main__":
    # Use 5001 to avoid macOS AirPlay Receiver on 5000, which can return 403
    app.run(debug=True, port=5001)

