from app import create_app

print("iniciando app")
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)