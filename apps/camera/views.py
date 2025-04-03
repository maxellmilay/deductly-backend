from main.utils.generic_api import GenericView
from .serializers import ImageSerializer
from .models import Image
from rest_framework.permissions import IsAuthenticated


class ImageView(GenericView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "image"
