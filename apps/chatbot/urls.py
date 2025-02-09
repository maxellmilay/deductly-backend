from django.urls import path
from .views import ChatView, ChatHistoryView

urlpatterns = [
    path("chat/", ChatView.as_view({"get": "list", "post": "create"}), name="chat"),
    path(
        "chat/history/<int:user_id>/",
        ChatHistoryView.as_view({"get": "list", "post": "create"}),
        name="chat-history",
    ),
]
