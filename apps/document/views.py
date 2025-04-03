from main.utils.generic_api import GenericView
from .serializers import DocumentSerializer
from .models import Document


class DocumentView(GenericView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "document"
