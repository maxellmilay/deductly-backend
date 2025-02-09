from django.contrib import admin
from .models import Chat


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("truncated_question", "truncated_answer", "user", "timestamp")
    list_filter = ("timestamp", "user")
    search_fields = ("question", "answer", "user__email", "user__username")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)

    def truncated_question(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question

    truncated_question.short_description = "Question"

    def truncated_answer(self, obj):
        return obj.answer[:50] + "..." if len(obj.answer) > 50 else obj.answer

    truncated_answer.short_description = "Answer"

    fieldsets = (
        ("Chat Content", {"fields": ("question", "answer")}),
        ("User Information", {"fields": ("user", "timestamp")}),
    )
