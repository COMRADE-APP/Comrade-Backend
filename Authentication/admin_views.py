"""
Admin Portal API Views
Comprehensive admin endpoints for platform management, analytics, and moderation.
All views require IsAdminUser permission.
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.parsers import JSONParser
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
CustomUser = get_user_model()


class AdminDashboardStatsView(APIView):
    """Platform-wide statistics for the admin dashboard."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from Opinions.models import Opinion
        from Articles.models import Article
        from Events.models import Event
        from Rooms.models import Room
        from Resources.models import Resource
        from Research.models import ResearchPaper
        from Announcements.models import Announcement
        from Authentication.models import (
            AccountDeletionRequest, RoleChangeRequest
        )
        from ActivityLog.models import UserActivity
        from Institution.models import Institution
        from Organisation.models import Organisation

        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total_users = CustomUser.objects.count()
        active_today = CustomUser.objects.filter(last_seen__date=today).count()
        new_this_week = CustomUser.objects.filter(date_joined__gte=week_ago).count()
        new_this_month = CustomUser.objects.filter(date_joined__gte=month_ago).count()

        # User role distribution
        role_distribution = list(
            CustomUser.objects.values('user_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Content counts
        content_counts = {
            'opinions': Opinion.objects.count(),
            'articles': Article.objects.count(),
            'events': Event.objects.count(),
            'rooms': Room.objects.count(),
            'resources': Resource.objects.count(),
            'research': ResearchPaper.objects.count(),
            'announcements': Announcement.objects.count(),
        }

        # Content created this week
        content_this_week = {
            'opinions': Opinion.objects.filter(created_at__gte=week_ago).count(),
            'events': Event.objects.filter(created_at__gte=week_ago).count(),
            'rooms': Room.objects.filter(created_at__gte=week_ago).count(),
        }

        # Pending reviews
        pending_deletions = AccountDeletionRequest.objects.filter(status='pending').count()
        pending_role_changes = RoleChangeRequest.objects.filter(status='pending').count()

        # Institution/Org verification pending
        try:
            pending_institutions = Institution.objects.filter(status='submitted').count()
        except Exception:
            pending_institutions = 0
        try:
            pending_organizations = Organisation.objects.filter(status='submitted').count()
        except Exception:
            pending_organizations = 0

        # Recent signups (last 10)
        recent_signups = list(
            CustomUser.objects.order_by('-date_joined')[:10].values(
                'id', 'email', 'first_name', 'last_name',
                'user_type', 'date_joined', 'is_active'
            )
        )

        # Recent activity (last 20)
        recent_activity = list(
            UserActivity.objects.select_related('user')
            .order_by('-timestamp')[:20]
            .values(
                'id', 'user__email', 'user__first_name',
                'activity_type', 'description', 'timestamp'
            )
        )

        # Account status breakdown
        account_statuses = {
            'active': CustomUser.objects.filter(account_status='active', is_active=True).count(),
            'deactivated': CustomUser.objects.filter(account_status='deactivated').count(),
            'pending_deletion': CustomUser.objects.filter(account_status='pending_deletion').count(),
        }

        return Response({
            'users': {
                'total': total_users,
                'active_today': active_today,
                'new_this_week': new_this_week,
                'new_this_month': new_this_month,
                'role_distribution': role_distribution,
                'account_statuses': account_statuses,
            },
            'content': content_counts,
            'content_this_week': content_this_week,
            'pending_reviews': {
                'deletions': pending_deletions,
                'role_changes': pending_role_changes,
                'institutions': pending_institutions,
                'organizations': pending_organizations,
                'total': pending_deletions + pending_role_changes + pending_institutions + pending_organizations,
            },
            'recent_signups': recent_signups,
            'recent_activity': recent_activity,
        })


class AdminUserManagementView(APIView):
    """List, search, and filter all platform users."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        queryset = CustomUser.objects.all().order_by('-date_joined')

        # Search
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        # Filter by role
        role = request.query_params.get('role', '')
        if role:
            queryset = queryset.filter(user_type=role)

        # Filter by status
        status_filter = request.query_params.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, account_status='active')
        elif status_filter == 'deactivated':
            queryset = queryset.filter(account_status='deactivated')
        elif status_filter == 'pending_deletion':
            queryset = queryset.filter(account_status='pending_deletion')
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 25))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size

        users = list(queryset[start:end].values(
            'id', 'email', 'first_name', 'last_name', 'user_type',
            'is_active', 'is_admin', 'is_staff', 'is_superuser',
            'account_status', 'date_joined', 'last_seen', 'is_online',
            'phone_number', 'totp_enabled', 'profile_completed'
        ))

        return Response({
            'results': users,
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
        })


class AdminToggleUserActiveView(APIView):
    """Toggle a user's active status (suspend/reactivate)."""
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [JSONParser]

    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {'error': 'Cannot modify a superuser account'},
                status=status.HTTP_403_FORBIDDEN
            )

        user.is_active = not user.is_active
        if not user.is_active:
            user.account_status = 'deactivated'
        else:
            user.account_status = 'active'
        user.save()

        return Response({
            'id': user.id,
            'email': user.email,
            'is_active': user.is_active,
            'account_status': user.account_status,
            'message': f"User {'activated' if user.is_active else 'suspended'} successfully"
        })


class AdminUpdateUserRoleView(APIView):
    """Force-update a user's role (admin override)."""
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [JSONParser]

    def post(self, request, user_id):
        from Authentication.models import USER_TYPE

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        new_role = request.data.get('role', '')
        valid_roles = [r[0] for r in USER_TYPE]
        if new_role not in valid_roles:
            return Response(
                {'error': f'Invalid role. Valid: {valid_roles}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_role = user.user_type
        user.user_type = new_role

        # Reset all role boolean flags
        user.is_admin = new_role == 'admin'
        user.is_student = new_role == 'student'
        user.is_lecturer = new_role == 'lecturer'
        user.is_moderator = new_role == 'moderator'
        user.is_student_admin = new_role == 'student_admin'
        user.is_inst_admin = new_role == 'institutional_admin'
        user.is_inst_staff = new_role == 'institutional_staff'
        user.is_org_admin = new_role == 'organisational_admin'
        user.is_org_staff = new_role == 'organisational_staff'
        user.is_author = new_role == 'author'
        user.is_editor = new_role == 'editor'
        user.is_normal_user = new_role == 'normal_user'
        user.is_staff = new_role in ('admin', 'staff')
        user.save()

        return Response({
            'id': user.id,
            'email': user.email,
            'old_role': old_role,
            'new_role': new_role,
            'message': f"Role changed from {old_role} to {new_role}"
        })


class AdminContentModerationView(APIView):
    """List and moderate platform content."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        content_type = request.query_params.get('type', 'opinions')
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        items = []
        total = 0

        try:
            if content_type == 'opinions':
                from Opinions.models import Opinion
                qs = Opinion.objects.select_related('author').order_by('-created_at')
                if search:
                    qs = qs.filter(Q(content__icontains=search) | Q(author__email__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                for o in qs[start:start + page_size]:
                    items.append({
                        'id': o.id, 'type': 'opinion',
                        'content': o.content[:200],
                        'author_email': o.author.email if o.author else 'N/A',
                        'author_name': f"{o.author.first_name} {o.author.last_name}" if o.author else 'N/A',
                        'created_at': o.created_at,
                        'likes_count': getattr(o, 'likes_count', 0),
                    })

            elif content_type == 'articles':
                from Articles.models import Article
                qs = Article.objects.select_related('author').order_by('-created_at')
                if search:
                    qs = qs.filter(Q(title__icontains=search) | Q(author__email__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                for a in qs[start:start + page_size]:
                    items.append({
                        'id': a.id, 'type': 'article',
                        'title': getattr(a, 'title', ''),
                        'content': str(getattr(a, 'body', getattr(a, 'content', '')))[:200],
                        'author_email': a.author.email if a.author else 'N/A',
                        'author_name': f"{a.author.first_name} {a.author.last_name}" if a.author else 'N/A',
                        'created_at': a.created_at,
                        'status': getattr(a, 'status', 'unknown'),
                    })

            elif content_type == 'events':
                from Events.models import Event
                qs = Event.objects.select_related('creator').order_by('-created_at')
                if search:
                    qs = qs.filter(Q(title__icontains=search) | Q(creator__email__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                for e in qs[start:start + page_size]:
                    items.append({
                        'id': e.id, 'type': 'event',
                        'title': e.title,
                        'description': str(getattr(e, 'description', ''))[:200],
                        'creator_email': e.creator.email if e.creator else 'N/A',
                        'creator_name': f"{e.creator.first_name} {e.creator.last_name}" if e.creator else 'N/A',
                        'created_at': e.created_at,
                        'start_date': getattr(e, 'start_date', None),
                    })

            elif content_type == 'rooms':
                from Rooms.models import Room
                qs = Room.objects.select_related('creator').order_by('-created_at')
                if search:
                    qs = qs.filter(Q(name__icontains=search) | Q(creator__email__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                for r in qs[start:start + page_size]:
                    items.append({
                        'id': r.id, 'type': 'room',
                        'name': r.name,
                        'description': str(getattr(r, 'description', ''))[:200],
                        'creator_email': r.creator.email if r.creator else 'N/A',
                        'creator_name': f"{r.creator.first_name} {r.creator.last_name}" if r.creator else 'N/A',
                        'created_at': r.created_at,
                        'members_count': getattr(r, 'members_count', 0),
                    })

            elif content_type == 'resources':
                from Resources.models import Resource
                qs = Resource.objects.select_related('creator').order_by('-created_at')
                if search:
                    qs = qs.filter(Q(title__icontains=search) | Q(creator__email__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                for res in qs[start:start + page_size]:
                    items.append({
                        'id': res.id, 'type': 'resource',
                        'title': res.title,
                        'description': str(getattr(res, 'description', ''))[:200],
                        'creator_email': res.creator.email if res.creator else 'N/A',
                        'creator_name': f"{res.creator.first_name} {res.creator.last_name}" if res.creator else 'N/A',
                        'created_at': res.created_at,
                    })

            elif content_type == 'research':
                from Research.models import ResearchPaper
                qs = ResearchPaper.objects.select_related('author').order_by('-created_at')
                if search:
                    qs = qs.filter(Q(title__icontains=search) | Q(author__email__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                for rp in qs[start:start + page_size]:
                    items.append({
                        'id': rp.id, 'type': 'research',
                        'title': rp.title,
                        'abstract': str(getattr(rp, 'abstract', ''))[:200],
                        'author_email': rp.author.email if rp.author else 'N/A',
                        'author_name': f"{rp.author.first_name} {rp.author.last_name}" if rp.author else 'N/A',
                        'created_at': rp.created_at,
                    })

        except Exception as e:
            logger.error(f"Error loading {content_type}: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'results': items,
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if total > 0 else 0,
        })


class AdminContentDeleteView(APIView):
    """Delete/remove specific content."""
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [JSONParser]

    def post(self, request):
        content_type = request.data.get('type', '')
        content_id = request.data.get('id', '')

        if not content_type or not content_id:
            return Response({'error': 'type and id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if content_type == 'opinion':
                from Opinions.models import Opinion
                obj = Opinion.objects.get(id=content_id)
            elif content_type == 'article':
                from Articles.models import Article
                obj = Article.objects.get(id=content_id)
            elif content_type == 'event':
                from Events.models import Event
                obj = Event.objects.get(id=content_id)
            elif content_type == 'room':
                from Rooms.models import Room
                obj = Room.objects.get(id=content_id)
            elif content_type == 'resource':
                from Resources.models import Resource
                obj = Resource.objects.get(id=content_id)
            elif content_type == 'research':
                from Research.models import ResearchPaper
                obj = ResearchPaper.objects.get(id=content_id)
            else:
                return Response({'error': 'Invalid content type'}, status=status.HTTP_400_BAD_REQUEST)

            obj.delete()
            return Response({'message': f'{content_type} #{content_id} deleted successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


class AdminAnalyticsView(APIView):
    """Time-series analytics for the platform."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from ActivityLog.models import UserActivity

        period = request.query_params.get('period', '30')
        try:
            days = int(period)
        except ValueError:
            days = 30

        start_date = timezone.now() - timedelta(days=days)

        # User signups over time
        signups = list(
            CustomUser.objects.filter(date_joined__gte=start_date)
            .annotate(date=TruncDate('date_joined'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # Login activity over time
        logins = list(
            UserActivity.objects.filter(
                activity_type='login',
                timestamp__gte=start_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # Content creation over time (opinions as proxy)
        try:
            from Opinions.models import Opinion
            content_created = list(
                Opinion.objects.filter(created_at__gte=start_date)
                .annotate(date=TruncDate('created_at'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )
        except Exception:
            content_created = []

        # Top creators (by opinion count)
        try:
            from Opinions.models import Opinion
            top_creators = list(
                Opinion.objects.values(
                    'author__id', 'author__email',
                    'author__first_name', 'author__last_name'
                )
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
        except Exception:
            top_creators = []

        # Most popular rooms
        try:
            from Rooms.models import Room
            popular_rooms = list(
                Room.objects.order_by('-members_count')[:10]
                .values('id', 'name', 'members_count', 'created_at')
            )
        except Exception:
            popular_rooms = []

        return Response({
            'period_days': days,
            'signups': signups,
            'logins': logins,
            'content_created': content_created,
            'top_creators': top_creators,
            'popular_rooms': popular_rooms,
        })


class AdminSystemInfoView(APIView):
    """System information and health check."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        import django
        import sys
        from Authentication.models import ComradeAdmin

        admin_users = list(
            ComradeAdmin.objects.select_related('user')
            .values(
                'id', 'user__email', 'user__first_name',
                'user__last_name', 'created_on'
            )
        )

        return Response({
            'django_version': django.get_version(),
            'python_version': sys.version,
            'total_users': CustomUser.objects.count(),
            'active_users': CustomUser.objects.filter(is_active=True).count(),
            'admin_users': admin_users,
            'admin_count': len(admin_users),
        })
