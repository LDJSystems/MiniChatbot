from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from rest_framework import generics

from .models import Lead
from .serializers import LeadSerializer


@method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    ),
    name="post",
)
class LeadCreateView(generics.CreateAPIView):

    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
