from main.utils.generic_api import GenericView
from .serializers import ReportSerializer
from .models import Report


class ReportView(GenericView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "report"
