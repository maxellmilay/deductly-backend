from django.urls import path
from .views import ChatView, ChatHistoryView

urlpatterns = [
    path(
        "chat/<int:pk>/",
        ChatView.as_view({"get": "list", "post": "create"}),
        name="chat",
    ),
    path(
        "chat/history/",
        ChatHistoryView.as_view({"get": "list", "post": "create"}),
        name="chat-history",
    ),
]
