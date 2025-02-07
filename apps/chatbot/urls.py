from django.urls import path
from .views import ChatView, ChatHistoryView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
]
