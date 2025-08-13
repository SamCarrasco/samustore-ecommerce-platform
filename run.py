from app import create_app
from config import DevConfig

app = create_app(config_object= DevConfig)

if __name__ == '__main__':
    app.run(port=5000,debug=True)
