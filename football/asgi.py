# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from your_app.consumers import MatchConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'football.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/matches/", MatchConsumer.as_asgi()),
        ])
    ),
})
