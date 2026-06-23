from flask import Flask

from config import SECRET_KEY
from views.auth_views import auth_bp
from views.admin_views import admin_bp
from views.generate_views import generate_bp
from views.user_views import user_bp
from views.page_views import page_bp
from views.debug_views import debug_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(generate_bp)
app.register_blueprint(user_bp)
app.register_blueprint(page_bp)
app.register_blueprint(debug_bp)

if __name__ == "__main__":
    app.run(debug=False)
