"""
NYAAI - cases/views.py
Handles all case operations — create, list, detail, analyse
"""

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Case, CaseTimeline
from .serializers import CaseSerializer, CaseCreateSerializer
import json
import logging

logger = logging.getLogger(__name__)


class CaseListCreateView(APIView):
    """
    GET  /api/cases/       → list all user cases
    POST /api/cases/create/ → create new case
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cases = Case.objects.filter(user=request.user)
        serializer = CaseSerializer(cases, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CaseCreateSerializer(data=request.data)
        if serializer.is_valid():
            case = serializer.save(user=request.user)

            # Run AI analysis immediately
            try:
                analyse_case(case)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")

            return Response(
                CaseSerializer(case).data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class CaseDetailView(APIView):
    """
    GET   /api/cases/<id>/ → get case details
    PATCH /api/cases/<id>/ → update case status
    """
    permission_classes = [IsAuthenticated]

    def get_case(self, case_id, user):
        try:
            return Case.objects.get(id=case_id, user=user)
        except Case.DoesNotExist:
            return None

    def get(self, request, case_id):
        case = self.get_case(case_id, request.user)
        if not case:
            return Response(
                {'success': False, 'message': 'Case not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CaseSerializer(case)
        return Response({'success': True, 'case': serializer.data})

    def patch(self, request, case_id):
        case = self.get_case(case_id, request.user)
        if not case:
            return Response(
                {'success': False, 'message': 'Case not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CaseSerializer(case, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'case': serializer.data})
        return Response({'success': False, 'errors': serializer.errors})


class AnalyseCaseView(APIView):
    """
    POST /api/cases/<id>/analyse/ → run AI analysis on a case
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, case_id):
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Case not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = analyse_case(case)
            return Response({
                'success':       True,
                'message':       'Case analysed successfully.',
                'laws_violated': case.laws_violated,
                'forum_type':    case.forum_type,
                'ai_summary':    case.ai_summary,
            })
        except Exception as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def analyse_case(case):
    """
    AI Analysis using Groq (llama-3.3-70b) — Free, fast, no quota issues.
    14,400 requests/day free. No rate limit problems.
    """
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)

    prompt = f"""You are an expert Indian lawyer. A citizen has this complaint:

CATEGORY: {case.get_category_display()}
DESCRIPTION: {case.description}

Respond ONLY with valid JSON — no extra text, no markdown, just pure JSON:
{{
    "laws_violated": [
        {{
            "act": "Full Act name",
            "section": "Section number",
            "description": "How this section applies to this case"
        }}
    ],
    "forum_type": "Which forum/court to approach",
    "forum_guidance": "Step by step how to file a complaint",
    "documents_needed": ["Document 1", "Document 2", "Document 3"],
    "ai_summary": "2-3 sentence summary of legal situation and recommended action",
    "confidence": 0.95
}}

Only include real Indian laws. Be specific."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()

    # Clean markdown if present
    if '```' in raw:
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)

    # Save AI results to case
    case.laws_violated    = data.get('laws_violated', [])
    case.forum_type       = data.get('forum_type', '')
    case.forum_address    = data.get('forum_guidance', '')
    case.documents_needed = data.get('documents_needed', [])
    case.ai_summary       = data.get('ai_summary', '')
    case.confidence_score = data.get('confidence', 0.0)
    case.is_analysed      = True
    case.status           = 'active'
    case.save()

    # Create timeline steps
    CaseTimeline.objects.filter(case=case).delete()
    steps = [
        ("Gather documents",     "Collect all relevant documents listed", 1),
        ("Send legal notice",    "Download and send the generated notice", 2),
        ("Wait for response",    "Give the other party 15 days to respond", 3),
        ("File forum complaint", f"File complaint at {case.forum_type}", 4),
        ("Attend hearing",       "Attend the scheduled hearing date", 5),
    ]
    for step, desc, order in steps:
        CaseTimeline.objects.create(
            case=case, step=step,
            description=desc, order=order
        )

    logger.info(f"[NYAAI] Case {case.id} analysed successfully via Groq")
    return data