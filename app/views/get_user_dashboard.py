"""
app/views/get_user_dashboard.py

CBV: GetUserDashboardView
URL: GET /api/v1/dashboard/
"""
from __future__ import annotations

from flask import jsonify, make_response, session, request
from flask.views import MethodView

from app.services.get_user_dashboard import get_user_dashboard
from app.views._auth                 import resolve_username


class GetUserDashboardView(MethodView):

    def get(self):
        username = resolve_username()
        if not username:
            return make_response(jsonify({"error": "Login required."}), 401)

        ip = request.remote_addr or "unknown"

        try:
            dashboard = get_user_dashboard(username=username, ip=ip)
        except LookupError as exc:
            return make_response(jsonify({"error": str(exc)}), 404)

        return make_response(jsonify(dashboard), 200)
