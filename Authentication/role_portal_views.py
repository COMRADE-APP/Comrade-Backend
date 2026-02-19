"""
Role-Specific Portal API Views
Provides data and actions for staff, authors, moderators, lecturers, 
and institutional/organizational admins.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


class IsStaffOrAbove(permissions.BasePermission):
    """Allow staff, admin, superuser."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_admin or request.user.is_superuser
        )


class IsRoleOwner(permissions.BasePermission):
    """Allow user with specific roles. Checks user_type against allowed_roles on the view."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        allowed = getattr(view, 'allowed_roles', [])
        return (
            request.user.user_type in allowed
            or request.user.is_admin
            or request.user.is_staff
            or request.user.is_superuser
        )


# ─── Staff Portal ───────────────────────────────────────────────
class StaffPortalDashboardView(APIView):
    """Staff overview: user stats, recent tickets, support metrics."""
    permission_classes = [IsStaffOrAbove]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_this_week = User.objects.filter(date_joined__gte=week_ago).count()

        # Recent signups needing attention
        recent_signups = User.objects.filter(
            date_joined__gte=week_ago
        ).order_by('-date_joined').values(
            'id', 'first_name', 'last_name', 'email', 'user_type', 'is_active', 'date_joined'
        )[:10]

        # Users by status
        pending_profiles = User.objects.filter(profile_completed=False, is_active=True).count()

        # Pending requests
        pending_data = {}
        try:
            from Authentication.models import RoleChangeRequest, AccountDeletionRequest
            pending_data['role_changes'] = RoleChangeRequest.objects.filter(status='pending').count()
            pending_data['deletions'] = AccountDeletionRequest.objects.filter(status='pending').count()
        except Exception:
            pending_data['role_changes'] = 0
            pending_data['deletions'] = 0

        # Activity feed
        recent_activity = []
        try:
            from ActivityLog.models import UserActivity
            recent_activity = list(UserActivity.objects.order_by('-timestamp').values(
                'user__first_name', 'user__email', 'activity_type', 'description', 'timestamp'
            )[:15])
        except Exception:
            pass

        # Role breakdown
        role_dist = list(User.objects.values('user_type').annotate(count=Count('id')).order_by('-count'))

        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'new_this_week': new_this_week,
            'pending_profiles': pending_profiles,
            'pending_requests': pending_data,
            'recent_signups': list(recent_signups),
            'recent_activity': recent_activity,
            'role_distribution': role_dist,
        })


class StaffUserAssistView(APIView):
    """Staff: search and assist users."""
    permission_classes = [IsStaffOrAbove]

    def get(self, request):
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        qs = User.objects.all()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        total = qs.count()
        start = (page - 1) * page_size
        users = qs.order_by('-date_joined')[start:start + page_size].values(
            'id', 'first_name', 'last_name', 'email', 'user_type',
            'is_active', 'profile_completed', 'date_joined', 'last_seen',
        )

        return Response({
            'results': list(users),
            'count': total,
            'page': page,
            'total_pages': max(1, (total + page_size - 1) // page_size),
        })


# ─── Author / Editor Portal ────────────────────────────────────
class AuthorPortalDashboardView(APIView):
    """Author stats: published content, drafts, engagement."""
    allowed_roles = ['author', 'editor']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        user = request.user
        data = {
            'opinions': {'published': 0, 'total_likes': 0, 'total_comments': 0},
            'articles': {'published': 0, 'drafts': 0},
            'research': {'published': 0},
            'recent_content': [],
        }

        try:
            from Opinions.models import Opinion
            opinions = Opinion.objects.filter(author=user)
            data['opinions']['published'] = opinions.count()
            data['opinions']['total_likes'] = sum(o.likes_count for o in opinions if hasattr(o, 'likes_count'))
            data['opinions']['total_comments'] = sum(o.comments_count for o in opinions if hasattr(o, 'comments_count'))

            recent = opinions.order_by('-created_at').values(
                'id', 'content', 'created_at'
            )[:5]
            for r in recent:
                data['recent_content'].append({
                    'type': 'opinion',
                    'title': (r['content'] or '')[:80],
                    'created_at': r['created_at'],
                    'id': r['id'],
                })
        except Exception:
            pass

        try:
            from Articles.models import Article
            articles = Article.objects.filter(author=user)
            data['articles']['published'] = articles.filter(status='published').count()
            data['articles']['drafts'] = articles.filter(status='draft').count()

            recent = articles.order_by('-created_at').values(
                'id', 'title', 'status', 'created_at'
            )[:5]
            for r in recent:
                data['recent_content'].append({
                    'type': 'article',
                    'title': r['title'],
                    'status': r['status'],
                    'created_at': r['created_at'],
                    'id': r['id'],
                })
        except Exception:
            pass

        try:
            from Research.models import Research
            data['research']['published'] = Research.objects.filter(author=user).count()
        except Exception:
            pass

        data['recent_content'].sort(key=lambda x: x.get('created_at') or '', reverse=True)
        data['recent_content'] = data['recent_content'][:10]

        return Response(data)


# ─── Moderator Portal ──────────────────────────────────────────
class ModeratorPortalDashboardView(APIView):
    """Moderator: content stats, flagged items, community health."""
    allowed_roles = ['moderator']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        data = {
            'content_stats': {},
            'new_this_week': {},
            'recent_content': [],
            'community_stats': {},
        }

        # Count content
        try:
            from Opinions.models import Opinion
            data['content_stats']['opinions'] = Opinion.objects.count()
            data['new_this_week']['opinions'] = Opinion.objects.filter(created_at__gte=week_ago).count()
            recent = Opinion.objects.order_by('-created_at').values(
                'id', 'content', 'author__first_name', 'author__email', 'created_at'
            )[:10]
            for r in recent:
                data['recent_content'].append({
                    'type': 'opinion',
                    'title': (r['content'] or '')[:80],
                    'author': r['author__first_name'] or r['author__email'],
                    'created_at': r['created_at'],
                    'id': r['id'],
                })
        except Exception:
            pass

        try:
            from Articles.models import Article
            data['content_stats']['articles'] = Article.objects.count()
            data['new_this_week']['articles'] = Article.objects.filter(created_at__gte=week_ago).count()
        except Exception:
            pass

        try:
            from Events.models import Event
            data['content_stats']['events'] = Event.objects.count()
            data['new_this_week']['events'] = Event.objects.filter(created_at__gte=week_ago).count()
        except Exception:
            pass

        try:
            from Rooms.models import Room
            data['content_stats']['rooms'] = Room.objects.count()
        except Exception:
            pass

        # User community stats
        data['community_stats'] = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'new_users_week': User.objects.filter(date_joined__gte=week_ago).count(),
        }

        return Response(data)


class ModeratorContentReviewView(APIView):
    """Moderator: browse and review content."""
    allowed_roles = ['moderator']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        content_type = request.query_params.get('type', 'opinions')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '')

        results = []
        total = 0

        try:
            if content_type == 'opinions':
                from Opinions.models import Opinion
                qs = Opinion.objects.all()
                if search:
                    qs = qs.filter(content__icontains=search)
                total = qs.count()
                start = (page - 1) * page_size
                items = qs.order_by('-created_at')[start:start + page_size]
                for item in items:
                    results.append({
                        'id': item.id,
                        'type': 'opinion',
                        'title': (item.content or '')[:100],
                        'author_name': getattr(item.author, 'first_name', '') if item.author else 'Unknown',
                        'author_email': getattr(item.author, 'email', '') if item.author else '',
                        'created_at': item.created_at,
                    })

            elif content_type == 'articles':
                from Articles.models import Article
                qs = Article.objects.all()
                if search:
                    qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))
                total = qs.count()
                start = (page - 1) * page_size
                items = qs.order_by('-created_at')[start:start + page_size]
                for item in items:
                    results.append({
                        'id': item.id,
                        'type': 'article',
                        'title': item.title or 'Untitled',
                        'author_name': getattr(item.author, 'first_name', '') if item.author else 'Unknown',
                        'author_email': getattr(item.author, 'email', '') if item.author else '',
                        'created_at': item.created_at,
                        'status': getattr(item, 'status', 'published'),
                    })
        except Exception:
            pass

        return Response({
            'results': results,
            'count': total,
            'page': page,
            'total_pages': max(1, (total + page_size - 1) // page_size),
        })


# ─── Lecturer Portal ───────────────────────────────────────────
class LecturerPortalDashboardView(APIView):
    """Lecturer: teaching stats, resources, student engagement."""
    allowed_roles = ['lecturer']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        user = request.user
        data = {
            'my_rooms': [],
            'my_resources': 0,
            'my_research': 0,
            'my_events': 0,
            'my_tasks': 0,
            'my_announcements': 0,
        }

        try:
            from Rooms.models import Room
            rooms = Room.objects.filter(creator=user)
            data['my_rooms'] = list(rooms.values('id', 'name', 'description', 'members_count', 'created_at')[:10])
        except Exception:
            pass

        try:
            from Resources.models import Resource
            data['my_resources'] = Resource.objects.filter(creator=user).count()
        except Exception:
            pass

        try:
            from Research.models import Research
            data['my_research'] = Research.objects.filter(author=user).count()
        except Exception:
            pass

        try:
            from Events.models import Event
            data['my_events'] = Event.objects.filter(creator=user).count()
        except Exception:
            pass

        try:
            from Tasks.models import Task
            data['my_tasks'] = Task.objects.filter(created_by=user).count()
        except Exception:
            pass

        try:
            from Announcements.models import Announcement
            data['my_announcements'] = Announcement.objects.filter(creator=user).count()
        except Exception:
            pass

        return Response(data)


# ─── Institutional Admin Portal ─────────────────────────────────
class InstitutionPortalDashboardView(APIView):
    """Institutional admin: institution stats, members, events."""
    allowed_roles = ['institutional_admin', 'institutional_staff']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        user = request.user
        data = {
            'institutions': [],
            'total_members': 0,
            'total_events': 0,
            'total_resources': 0,
        }

        try:
            from Institution.models import Institution
            # Get institutions this user owns/admins
            insts = Institution.objects.filter(
                Q(created_by=user) | Q(admin=user)
            ).distinct()
            data['institutions'] = list(insts.values(
                'id', 'name', 'email', 'status', 'institution_type', 'created_at'
            )[:10])
        except Exception:
            pass

        return Response(data)


# ─── Organisation Admin Portal ──────────────────────────────────
class OrganisationPortalDashboardView(APIView):
    """Organisational admin: org stats, members, activities."""
    allowed_roles = ['organisational_admin', 'organisational_staff']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        user = request.user
        data = {
            'organisations': [],
            'total_members': 0,
        }

        try:
            from Organisation.models import Organisation
            orgs = Organisation.objects.filter(
                Q(created_by=user) | Q(admin=user)
            ).distinct()
            data['organisations'] = list(orgs.values(
                'id', 'name', 'email', 'status', 'organization_type', 'created_at'
            )[:10])
        except Exception:
            pass

        return Response(data)


# ─── Partner Portal ─────────────────────────────────────────────
class PartnerPortalDashboardView(APIView):
    """Partner: products, sales, commissions."""
    allowed_roles = ['partner']
    permission_classes = [IsRoleOwner]

    def get(self, request):
        user = request.user
        data = {
            'products': 0,
            'establishments': 0,
            'recent_products': [],
        }

        try:
            from Shop.models import Product
            products = Product.objects.filter(partner__user=user)
            data['products'] = products.count()
            data['recent_products'] = list(products.order_by('-created_at').values(
                'id', 'name', 'price', 'status', 'created_at'
            )[:10])
        except Exception:
            pass

        try:
            from Shop.models import Establishment
            data['establishments'] = Establishment.objects.filter(owner=user).count()
        except Exception:
            pass

        return Response(data)
