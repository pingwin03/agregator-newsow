from rest_framework import permissions

class IsAdminOrOwnerReadOnly(permissions.BasePermission):
    """
    Niestandardowe uprawnienia:
    - Admin/Oficer może wszystko (CRUD).
    - Pracownik może tylko przeglądać (GET) swoje wnioski, brak opcji usuwania i edycji.
    """
    def has_object_permission(self, request, view, obj):
        # Sprawdzam, czy użytkownik jest administratorem lub oficerem - jeśli tak, pozwalam na wszystko
        if request.user.role in ['admin', 'officer']:
            return True
            
        # Jeśli to bezpieczna metoda (tylko odczyt, np. GET)
        if request.method in permissions.SAFE_METHODS:
            # Upewniam się, że wniosek należy do tego konkretnego pracownika
            return obj.article.source == request.user.username
            
        # Zabraniam wszystkich innych akcji (PUT, DELETE) dla zwykłego pracownika
        return False