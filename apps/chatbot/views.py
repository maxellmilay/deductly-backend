from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Chat
from .serializers import ChatSerializer
from .utils.main import generate_answer


class ChatView(APIView):
    def post(self, request):
        question = request.data.get("question")
        if not question:
            return Response(
                {"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Your existing LangChain logic
            final_answer = generate_answer(question)

            # Save to database
            chat = Chat.objects.create(question=question, answer=final_answer)

            serializer = ChatSerializer(chat)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        chats = Chat.objects.all()
        serializer = ChatSerializer(chats, many=True)
        return Response(serializer.data)
