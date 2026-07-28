from apps.accounts.decorators import SESSION_STUDENT_ID_KEY

def student_session(request):
    return {
        "current_student_id": request.session.get(SESSION_STUDENT_ID_KEY),
    }
