from main.utils.generic_api import GenericView
from .serializers import ReportSerializer
from .models import Report
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q


class ReportView(GenericView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def filter_queryset(self, filters, excludes):
        filters["user"] = self.request.user
        filter_q = Q(**filters)
        exclude_q = Q(**excludes)
        return self.queryset.filter(filter_q).exclude(exclude_q)
