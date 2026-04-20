from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from cases.models import Case
from accounts.models import UserProfile
from .pdf_generator import generate_legal_notice


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_legal_notice(request, case_id):
    """
    Generate and return a legal notice PDF for the given case.
    Only the case owner can download it.
    """
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return Response(
            {'error': 'Case not found or access denied.'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response(
            {'error': 'User profile not found.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        buffer = generate_legal_notice(case, user_profile)
    except Exception as e:
        return Response(
            {'error': f'PDF generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    filename = f"legal_notice_case_{case.id}.pdf"

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename,
        content_type='application/pdf'
    )