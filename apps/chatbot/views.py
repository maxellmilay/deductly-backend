from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Chat
from .serializers import ChatSerializer
from .utils.main import generate_answer
from apps.account.models import CustomUser
from datetime import datetime


class ChatView(APIView):
    def post(self, request):
        question = request.data.get("question")
        if not question:
            return Response(
                {"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            final_answer = generate_answer(question)

            # Save to database
            user = (
                CustomUser.objects.get(pk=request.user.id)
                if request.user.is_authenticated
                else None
            )

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


class ChatHistoryView(APIView):
    def get(self, request, user_id):
        try:
            chats = Chat.objects.filter(user_id=user_id).order_by("-timestamp")
            serializer = ChatSerializer(chats, many=True)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
