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
from django.core.paginator import Paginator

User = get_user_model()


class ChatView(GenericView):
    def post(self, request):
        print("Request data:", request.data)
        question = request.data.get("question")
        user_id = request.data.get("id")
        print(user_id, question, "user id")

        if not question:
            return Response(
                {"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            final_answer = generate_answer(question)

            # Save to database
            user = CustomUser.objects.get(pk=user_id) if user_id else None

            print(user, "user printing")

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
    queryset = Chat.objects.filter().order_by("-timestamp")
    serializer_class = ChatSerializer
    allowed_methods = ["get", "list", "create"]
    # def filter(self, top, bottom):
    #     try:
    #         chats = Chat.objects.filter(user_id=user_id).order_by("-timestamp")
    #         paginator = Paginator(chats, self.size_per_request)
    #         page_number = (top // self.size_per_request) + 1
    #         page = paginator.get_page(page_number)
    #         serializer = ChatSerializer(chats, many=True)
    #         return Response(serializer.data)
    #     except CustomUser.DoesNotExist:
    #         return Response(
    #             {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
    #         )
