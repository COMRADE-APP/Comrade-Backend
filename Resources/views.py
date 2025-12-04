from django.shortcuts import render
from Resources.serializers import ResourceSerializer, ResourceVisibilitySerializer, VisibilityLogSerializer, LinkSerializer, VisibilitySerializer, MainVisibilityLogSerializer
from Resources.models import Resource, ResourceVisibility, VisibilityLog, Link, Visibility, MainVisibilityLog
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import status
from rest_framework.decorators import action
from Rooms.permissions import IsModerator
from Resources.permissions import IsAuthor, IsEditor, IsAuthorOrEditor
from rest_framework.response import Response
from Rooms.models import Room, DefaultRoom, DirectMessageRoom
from django.shortcuts import get_object_or_404
from Institution.models import Institution, InstBranch, Faculty, VCOffice, InstDepartment, AdminDep, Programme as InstProg, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport, Library, Hostel, Cafeteria, OtherInstitutionUnit
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit
from Authentication.models import Profile, ComradeAdmin
import os
from django.http import FileResponse
from Resources.renderers import PDFRenderer
from django.shortcuts import get_object_or_404
import os
import base64
import mimetypes
from datetime import datetime
import threading
import time
import copy
import uuid


VISIBILITY_MAP = {
    "organisations": (Organisation, "organisations"),
    "organisation_branches": (OrgBranch, "organisation_branches"),
    "departments": (Department, "departments"),
    "sections": (Section, "sections"),
    "committees": (Committee, "committees"),
    "units": (Unit, "units"),
    "programs": (Program, "programs"),
    "projects": (Project, "projects"),
    "centres": (Centre, "centres"),
    "teams": (Team, "teams"),
    "divisions": (Division, "divisions"),
    "boards": (Board, "boards"),
    "institutes": (Institute, "institutes"),
    "other_organisation_units": (OtherOrgUnit, "other_organisation_units"),
    "institutions": (Institution, "institutions"),
    "institution_branches": (InstBranch, "institution_branches"),
    "faculties": (Faculty, "faculties"),
    "vc_offices": (VCOffice, "vc_offices"),
    "inst_departments": (InstDepartment, "inst_departments"),
    "admin_deps": (AdminDep, "admin_deps"),
    "programmes": (InstProg, "programmes"),
    "hrs": (HR, "hrs"),
    "admissions": (Admissions, "admissions"),
    "health_services": (HealthServices, "health_services"),
    "securities": (Security, "securities"),
    "student_affairs": (StudentAffairs, "student_affairs"),
    "support_services": (SupportServices, "support_services"),
    "finances": (Finance, "finances"),
    "marketings": (Marketing, "marketings"),
    "legals": (Legal, "legals"),
    "icts": (ICT, "icts"),
    "career_offices": (CareerOffice, "career_offices"),
    "counsellings": (Counselling, "counsellings"),
    "registrar_offices": (RegistrarOffice, "registrar_offices"),
    "transports": (Transport, "transports"),
    "libraries": (Library, "libraries"),
    "hostels": (Hostel, "hostels"),
    "cafeterias": (Cafeteria, "cafeterias"),
    "other_institution_units": (OtherInstitutionUnit, "other_institution_units"),
    "rooms": (Room, "rooms"),
    "default_rooms": (DefaultRoom, "default_rooms"),
    "direct_message_rooms": (DirectMessageRoom, "direct_message_rooms"),
    "only_me": (Profile, "users_with_access"),
    "public": (None, None),  # Special case handled separately
}

VISIBILITY_OPTIONS_MAP = {
    "organisations": (Organisation, "organisations"),
    "organisation_branches": (OrgBranch, "organisation_branches"),
    "departments": (Department, "departments"),
    "sections": (Section, "sections"),
    "committees": (Committee, "committees"),
    "units": (Unit, "units"),
    "programs": (Program, "programs"),
    "projects": (Project, "projects"),
    "centres": (Centre, "centres"),
    "teams": (Team, "teams"),
    "divisions": (Division, "divisions"),
    "boards": (Board, "boards"),
    "institutes": (Institute, "institutes"),
    "other_organisation_units": (OtherOrgUnit, "other_organisation_units"),
    "institutions": (Institution, "institutions"),
    "institution_branches": (InstBranch, "institution_branches"),
    "faculties": (Faculty, "faculties"),
    "vc_offices": (VCOffice, "vc_offices"),
    "inst_departments": (InstDepartment, "inst_departments"),
    "admin_deps": (AdminDep, "admin_deps"),
    "programmes": (InstProg, "programmes"),
    "hrs": (HR, "hrs"),
    "admissions": (Admissions, "admissions"),
    "health_services": (HealthServices, "health_services"),
    "securities": (Security, "securities"),
    "student_affairs": (StudentAffairs, "student_affairs"),
    "support_services": (SupportServices, "support_services"),
    "finances": (Finance, "finances"),
    "marketings": (Marketing, "marketings"),
    "legals": (Legal, "legals"),
    "icts": (ICT, "icts"),
    "career_offices": (CareerOffice, "career_offices"),
    "counsellings": (Counselling, "counsellings"),
    "registrar_offices": (RegistrarOffice, "registrar_offices"),
    "transports": (Transport, "transports"),
    "libraries": (Library, "libraries"),
    "hostels": (Hostel, "hostels"),
    "cafeterias": (Cafeteria, "cafeterias"),
    "other_institution_units": (OtherInstitutionUnit, "other_institution_units"),
    "rooms": (Room, "rooms"),
    "default_rooms": (DefaultRoom, "default_rooms"),
    "direct_message_rooms": (DirectMessageRoom, "direct_message_rooms"),
    "only_me": (Profile, "users_with_access"),
    "public": (None, None),  # Special case handled separately
    "comrade": (ComradeAdmin, "users_with_access"),
    "admins": (Profile, "users_with_access"),
    "admins_moderators": (Profile, "users_with_access"),
    "resources": (Resource, "users_with_access"),
}



# Create your views here.
class ResourceViewSet(ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    # permission_classes = [IsAuthenticatedOrReadOnly]
    # renderer_classes = [PDFRenderer]

    @action(detail=True, methods=['get'], renderer_classes=[PDFRenderer])
    def view_resource(self, request, pk=None):
        resource = self.get_object()
        resource = get_object_or_404(Resource, id=resource.id)

        if not resource:
            return Response({'error': 'No object was parsed to the backend'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        file_path = resource.res_file
        print(file_path.path)
        print(file_path) # or use storage.open for remote storage
        if not os.path.exists(str(file_path.path)):
            raise Response({'error': 'The file does not exist'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(file_path.path, 'rb') as f:
                file_bytes = f.read()
        except Exception as e:
            return Response({'error': f'Failed to read file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        filename = os.path.basename(file_path.path)
        content_type, _ = mimetypes.guess_type(file_path.path)
        if not content_type:
            content_type = 'application/octet-stream'

        content_base64 = base64.b64encode(file_bytes).decode('utf-8')
        file_info = {
            'filename': filename,
            'content_type': content_type,
            'size': len(file_bytes),
            'content_base64': content_base64,
        }

        return Response(file_info, status=status.HTTP_200_OK)

class ResourceVisibilityViewSet(ModelViewSet):
    queryset = ResourceVisibility.objects.all()
    serializer_class = ResourceVisibilitySerializer
    permission_classes = [IsAuthorOrEditor]

    # Creating a visibility and logging it (for the first time).
    @action(detail=True, methods=['post'])
    def create_visibility(self, request):
        resource_id = request.data.get("resource_id")
        visibility_groups = request.data.get("visibility", {})

        if not resource_id:
            return Response({"error": "resource_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        resource = get_object_or_404(Resource, id=resource_id)

        visibility = ResourceVisibility.objects.create(resource=resource)
        old_visibility = None  # No previous visibility for creation
        changed_by = request.user

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        try:
            VisibilityLog.objects.create(
                resource=resource,
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=changed_by
            )
            return Response({
                "message": "Visibility created successfully and logged.", "visibility": visibility_groups
            }, status=201)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility creation: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    #
    @action(detail=True, methods=['patch', 'put'])
    def remove_visibility(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        if not visibility:
            return Response({"error": "ResourceVisibility not found."}, status=404)

        old_visibility = copy.copy(visibility)

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Remove from the many-to-many field
            getattr(visibility, field_name).remove(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        changed_by = request.user

        try:
            if old_visibility != new_visibility:
                VisibilityLog.objects.create(
                    resource=visibility.resource,
                    old_visibility=old_visibility,
                    new_visibility=new_visibility,
                    changed_by=changed_by
                )
                return Response({
                        "message": "Visibility items removed successfully. The action has been logged.",
                        "removed": visibility_groups
                    }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility change: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        

    
    @action(detail=True, methods=['patch', 'put'])
    def add_visibility(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)
    
    # Make a resource public
    @action(detail=True, methods=['post', 'put', 'patch'])
    def make_public(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        old_visibility = visibility
        created_by = request.user
        
        visibility.resource.visibility = 'public'
        visibility.resource.save()
        visibility.save()
        new_visibility = copy.copy(visibility)

        try:
            VisibilityLog.objects.create(
                resource=visibility.resource,
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=created_by
            )
            return Response({
                "message": "Resource made public successfully and logged."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log making resource public: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['post', 'put', 'patch'])
    def set_duration_availability(self, request):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})
        expiry_time = request.data.get('expiry_time')
        

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        old_visibility = copy.copy(visibility)
        created_by = request.user


        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)

        VisibilityLog.objects.create(
                resource=visibility.resource,
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=created_by
            )

        # check if expiry time is reached
        def _expiry_checker(visibility_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if now >= target_time:
                        try:
                            visibility = ResourceVisibility.objects.get(pk=visibility_id)
                            # remove the visibility
                            getattr(visibility, field_name).remove(*objects)
                            VisibilityLog.objects.create(
                                resource=visibility.resource,
                                old_visibility=new_visibility,
                                new_visibility=old_visibility,
                                changed_by=created_by
                            )
                            visibility.save()
                        except ResourceVisibility.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = threading.Thread(target=_expiry_checker, args=(visibility_id, expiry_time), daemon=True)
        checker_thread.start()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post', 'put', 'patch'])
    def schedule_visibility(self, request):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})
        expiry_time = request.data.get('expiry_time')
        resource_id = request.data.get('resource_id')
        

        if not expiry_time:
            return Response({"error": "Expiry time is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not resource_id:
            return Response({"error": "Resource is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not visibility_id and resource_id:
            resource = get_object_or_404(Resource, id=resource_id)

            visibility = ResourceVisibility.objects.create(resource=resource, expiry_time=expiry_time)
        else:
            visibility = get_object_or_404(ResourceVisibility, id=visibility_id)

        old_visibility = copy.copy(visibility)
        created_by = request.user


        # check if expiry time is reached
        def _schedule_checker(visibility_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if now >= target_time:
                        try:
                             for group_name, ids in visibility_groups.items():

                                if group_name not in VISIBILITY_MAP:
                                    return Response({
                                        "error": f"Invalid visibility type: {group_name}"
                                    }, status=status.HTTP_400_BAD_REQUEST)

                                model, field_name = VISIBILITY_MAP[group_name]

                                # Fetch all objects matching the IDs
                                objects = model.objects.filter(id__in=ids)

                                if objects.count() != len(ids):
                                    return Response({
                                        "error": f"Some IDs in {group_name} do not exist."
                                    }, status=status.HTTP_400_BAD_REQUEST)

                                # Add to the many-to-many field
                                getattr(visibility, field_name).add(*objects)

                                visibility.save()
                                new_visibility = copy.copy(visibility)

                                VisibilityLog.objects.create(
                                        resource=visibility.resource,
                                        old_visibility=old_visibility,
                                        new_visibility=new_visibility,
                                        changed_by=created_by
                                    )
                                visibility.save()
                        except ResourceVisibility.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = threading.Thread(target=_schedule_checker, args=(visibility_id, expiry_time), daemon=True)
        checker_thread.start()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)
        
    


    
class VisibilityLogViewSet(ModelViewSet):
    queryset = VisibilityLog.objects.all()
    serializer_class = VisibilityLogSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class VisibilityViewSet(ModelViewSet):
    queryset = Visibility.objects.all()
    serializer_class = VisibilitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


    # Creating a visibility and logging it (for the first time).
    @action(detail=True, methods=['post'])
    def create_visibility(self, request):
        main_entity = request.data.get('main_entity')
        visibility_groups = request.data.get("visibility", {})

        if not main_entity:
            return Response({"error": "Select the entity you want to create the visibility for."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = Visibility.objects.create(main_entity=main_entity)
        old_visibility = None  # No previous visibility for creation
        changed_by = request.user

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        try:
            MainVisibilityLog.objects.create(
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=changed_by
            )
            return Response({
                "message": "Visibility created successfully and logged.", "visibility": visibility_groups
            }, status=201)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility creation: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    @action(detail=True, methods=['patch', 'put'])
    def remove_visibility(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(Visibility, visibility_code=pk)
        # visibility = get_object_or_404(Visibility, visibility_code=visibility_id)

        if not visibility:
            return Response({"error": "Visibility not found."}, status=404)

        old_visibility = copy.copy(visibility)

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Remove from the many-to-many field
            getattr(visibility, field_name).remove(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        changed_by = request.user

        try:
            if old_visibility != new_visibility:
                VisibilityLog.objects.create(
                    old_visibility=old_visibility,
                    new_visibility=new_visibility,
                    changed_by=changed_by
                )
                return Response({
                        "message": "Visibility items removed successfully. The action has been logged.",
                        "removed": visibility_groups
                    }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility change: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        

    
    @action(detail=True, methods=['patch', 'put'])
    def add_visibility(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(Visibility, visibility_code=visibility_id)
        old_visibility = copy.copy(visibility)
        # visibility = get_object_or_404(Visibility, visibility_code=pk)

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        changed_by = request.user

        try:
            if old_visibility != new_visibility:
                MainVisibilityLog.objects.create(
                    old_visibility=old_visibility,
                    new_visibility=new_visibility,
                    changed_by=changed_by
                )
                return Response({
                        "message": "Visibility items added successfully. The action has been logged.",
                        "added": visibility_groups
                    }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility change: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    # Make a resource public
    @action(detail=True, methods=['post', 'put', 'patch'])
    def make_public(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        visibility = get_object_or_404(Visibility, visibility_code=visibility_id)
        # visibility = get_object_or_404(Visibility, visibility_code=pk)

        old_visibility = visibility
        created_by = request.user
        
        profiles = Profile.objects.all()
        visibility.users_with_access.add(profiles)
        visibility.save()
        new_visibility = copy.copy(visibility)

        try:
            MainVisibilityLog.objects.create(
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=created_by
            )
            return Response({
                "message": "Resource made public successfully and logged."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log making resource public: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['post', 'put', 'patch'])
    def set_duration_availability(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})
        expiry_time = request.data.get('expiry_time')
        

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(Visibility, visibility_code=visibility_id)
        # visibility = get_object_or_404(Visibility, visibility_code=id)

        old_visibility = copy.copy(visibility)
        created_by = request.user


        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)

        MainVisibilityLog.objects.create(
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=created_by
            )

        # check if expiry time is reached
        def _expiry_checker(visibility_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if now >= target_time:
                        try:
                            visibility = Visibility.objects.get(pk=visibility_id)
                            # remove the visibility
                            getattr(visibility, field_name).remove(*objects)
                            MainVisibilityLog.objects.create(
                                old_visibility=new_visibility,
                                new_visibility=old_visibility,
                                changed_by=created_by
                            )
                            visibility.save()
                        except Visibility.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = threading.Thread(target=_expiry_checker, args=(visibility_id, expiry_time), daemon=True)
        checker_thread.start()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post', 'put', 'patch'])
    def schedule_visibility(self, request):
        visibility_code = request.data.get("visibility_code")
        visibility_groups = request.data.get("visibility", {})
        expiry_time = request.data.get('expiry_time')
        main_entity = request.data.get('main_entity')
        

        if not expiry_time:
            return Response({"error": "Expiry time is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not main_entity:
            return Response({"error": "Resource is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not visibility_code and main_entity:
            model_id = visibility_groups[main_entity]
            model, field_name = VISIBILITY_OPTIONS_MAP[main_entity]
            model = get_object_or_404(model, pk=model_id)

            visibility = Visibility.objects.create(main_entity=main_entity, expiry_time=expiry_time)
        else:
            visibility = get_object_or_404(Visibility, visibility_code=visibility_code)
            # visibility = get_object_or_404(Visibility, pk=visibility_code)

        old_visibility = copy.copy(visibility)
        created_by = request.user


        # check if expiry time is reached
        def _schedule_checker(visibility_code, target_time):
            try:
                while True:
                    now = datetime.now()
                    if now >= target_time:
                        try:
                             for group_name, ids in visibility_groups.items():

                                if group_name not in VISIBILITY_MAP:
                                    return Response({
                                        "error": f"Invalid visibility type: {group_name}"
                                    }, status=status.HTTP_400_BAD_REQUEST)

                                model, field_name = VISIBILITY_MAP[group_name]

                                # Fetch all objects matching the IDs
                                objects = model.objects.filter(id__in=ids)

                                if objects.count() != len(ids):
                                    return Response({
                                        "error": f"Some IDs in {group_name} do not exist."
                                    }, status=status.HTTP_400_BAD_REQUEST)

                                # Add to the many-to-many field
                                getattr(visibility, field_name).add(*objects)

                                visibility.save()
                                new_visibility = copy.copy(visibility)

                                MainVisibilityLog.objects.create(
                                        old_visibility=old_visibility,
                                        new_visibility=new_visibility,
                                        changed_by=created_by
                                    )
                                visibility.save()
                        except ResourceVisibility.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = threading.Thread(target=_schedule_checker, args=(visibility_code, expiry_time), daemon=True)
        checker_thread.start()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post', 'put', 'patch'])
    def deactivate_instance(self, request, pk=None):
        visibility_code = request.data.get('visibility_code')
        main_entity = request.data.get('main_entity')

        if not visibility_code and pk:
            try:
                visibility = get_object_or_404(Visibility, visibility_code=pk)
            except Visibility.DoesNotExist:
                return Response({'error': 'visibility with that id does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                visibility = get_object_or_404(Visibility, visibility_code=visibility_code)
            except Visibility.DoesNotExist:
                return Response({'error': 'Visibility with that code does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Fetch the model instance to be deactivate
            model, field_name = VISIBILITY_OPTIONS_MAP[main_entity]
            entity = getattr(visibility, 'main_entity')
            entity = entity.first()
            model = get_object_or_404(model, id=entity.id)

            # Save the old visibility for logging purposes
            old_visibility = copy.copy(visibility)


            visibility = Visibility.objects.create(main_entity=main_entity, operation_state='deactivate')
            profile = get_object_or_404(Profile, user=request.user)
            # admins = ComradeAdmin.objects.all()
            getattr(visibility, main_entity).add(profile)
            visibility.save()

            new_visibility = copy.copy(visibility)

            MainVisibilityLog.objects.create(
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=profile,
            )

            return Response({'message': f'The {main_entity} instance has been deactivated successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'The following error occured: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        


class LinkViewSet(ModelViewSet):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class MainVisibilityLogViewSet(ModelViewSet):
    queryset = MainVisibilityLog.objects.all()
    serializer_class = MainVisibilityLogSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

