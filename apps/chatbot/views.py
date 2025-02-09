from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Chat
from .serializers import ChatSerializer
from .utils.main import generate_answer
from apps.account.models import CustomUser
from django.contrib.auth import get_user_model
from datetime import datetime
from main.utils.generic_api import GenericView

User = get_user_model()


class ChatView(GenericView):
    queryset = Chat.objects.filter(removed=False).order_by("-timestamp")
    serializer_class = ChatSerializer
    allowed_methods = ["get", "list", "create"]

    def put(self, request, pk=None):
        question = request.data.get("question")

        if not question:
            return Response(
                {"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            final_answer = generate_answer(question)

            # Handle guest users (pk = -1)
            if pk == 0:
                return Response(
                    {
                        "question": question,
                        "answer": final_answer,
                        "timestamp": datetime.now(),
                        "is_guest": True,
                    },
                    status=status.HTTP_200_OK,
                )

            # Save to database
            user = CustomUser.objects.get(pk=pk) if pk != -1 else None
            if user:
                chat = Chat.objects.create(
                    question=question, answer=final_answer, user=user
                )
            else:
                return Response(
                    {"answer": final_answer, "date": datetime.now()},
                    status=status.HTTP_200_OK,
                )

            serializer = ChatSerializer(chat)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatHistoryView(GenericView):
    queryset = Chat.objects.filter(removed=False).order_by("-timestamp")
    serializer_class = ChatSerializer
    size_per_request = 5
    allowed_methods = ["get", "list", "create"]
