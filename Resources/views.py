from django.shortcuts import render
from Resources.serializers import ResourceSerializer, ResourceVisibilitySerializer, VisibilityLogSerializer
from Resources.models import Resource, ResourceVisibility, VisibilityLog
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


# Create your views here.
class ResourceViewSet(ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ResourceVisibilityViewSet(ModelViewSet):
    queryset = ResourceVisibility.objects.all()
    serializer_class = ResourceVisibilitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    # ----- *Room Related Visibility Removal Actions* ----- #
    @action(detail=True, methods=['post'])
    def remove_room_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        rooms = serializer.validated_data['rooms']
        rooms = get_object_or_404(Room, id__in=[room.id for room in rooms])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.rooms.remove(*rooms)
        visibility.save()
        return Response({'message': 'Rooms removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_default_room_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        default_rooms = serializer.validated_data['default_rooms']
        default_rooms = get_object_or_404(DefaultRoom, id__in=[droom.id for droom in default_rooms])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.default_rooms.remove(*default_rooms)
        visibility.save()
        return Response({'message': 'Default Rooms removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_direct_message_room_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        dm_rooms = serializer.validated_data['direct_message_rooms']
        dm_rooms = get_object_or_404(DirectMessageRoom, id__in=[dmroom.id for dmroom in dm_rooms])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.direct_message_rooms.remove(*dm_rooms)
        visibility.save()
        return Response({'message': 'Direct Message Rooms removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    # ----- *Institution Related Visibility Removal Actions* ----- #
    @action(detail=True, methods=['post'])
    def remove_insitution_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        institutions = serializer.validated_data['institutions']
        institutions = get_object_or_404(Institution, id__in=[inst.id for inst in institutions])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institutions.remove(*institutions)
        visibility.save()
        return Response({'message': 'Institutions removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_institution_branch_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        inst_branches = serializer.validated_data['institution_branches']
        inst_branches = get_object_or_404(InstBranch, id__in=[ibranch.id for ibranch in inst_branches])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institution_branches.remove(*inst_branches)
        visibility.save()
        return Response({'message': 'Institution Branches removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_faculty_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        faculties = serializer.validated_data['faculties']
        faculties = get_object_or_404(Faculty, id__in=[fac.id for fac in faculties])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.faculties.remove(*faculties)
        visibility.save()
        return Response({'message': 'Faculties removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_vc_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        vc_offices = serializer.validated_data['vc_offices']
        vc_offices = get_object_or_404(VCOffice, id__in=[vc.id for vc in vc_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.vc_offices.remove(*vc_offices)
        visibility.save()
        return Response({'message': 'VC Offices removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_inst_department_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        inst_departments = serializer.validated_data['inst_departments']
        inst_departments = get_object_or_404(InstDepartment, id__in=[idep.id for idep in inst_departments])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.inst_departments.remove(*inst_departments)
        visibility.save()
        return Response({'message': 'Institution Departments removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_admin_dep_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        admin_deps = serializer.validated_data['admin_deps']
        admin_deps = get_object_or_404(AdminDep, id__in=[adep.id for adep in admin_deps])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.admin_deps.remove(*admin_deps)
        visibility.save()
        return Response({'message': 'Admin Departments removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_inst_program_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        inst_programs = serializer.validated_data['programs']
        inst_programs = get_object_or_404(InstProg, id__in=[iprog.id for iprog in inst_programs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.programs.remove(*inst_programs)
        visibility.save()
        return Response({'message': 'Institution Programs removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_hr_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        hrs = serializer.validated_data['hrs']
        hrs = get_object_or_404(HR, id__in=[hr.id for hr in hrs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.hrs.remove(*hrs)
        visibility.save()
        return Response({'message': 'HRs removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_admissions_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        admissions = serializer.validated_data['admissions']
        admissions = get_object_or_404(Admissions, id__in=[adm.id for adm in admissions])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.admissions.remove(*admissions)
        visibility.save()
        return Response({'message': 'Admissions removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_health_service_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        health_services = serializer.validated_data['health_services']
        health_services = get_object_or_404(HealthServices, id__in=[hs.id for hs in health_services])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.health_services.remove(*health_services)
        visibility.save()
        return Response({'message': 'Health Services removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_security_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        securities = serializer.validated_data['securities']
        securities = get_object_or_404(Security, id__in=[sec.id for sec in securities])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.securities.remove(*securities)
        visibility.save()
        return Response({'message': 'Securities removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_student_affairs_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        student_affairs = serializer.validated_data['student_affairs']
        student_affairs = get_object_or_404(StudentAffairs, id__in=[sa.id for sa in student_affairs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.student_affairs.remove(*student_affairs)
        visibility.save()
        return Response({'message': 'Student Affairs removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_support_service_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        support_services = serializer.validated_data['support_services']
        support_services = get_object_or_404(SupportServices, id__in=[ss.id for ss in support_services])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.support_services.remove(*support_services)
        visibility.save()
        return Response({'message': 'Support Services removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_finance_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        finances = serializer.validated_data['finances']
        finances = get_object_or_404(Finance, id__in=[fin.id for fin in finances])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.finances.remove(*finances)
        visibility.save()
        return Response({'message': 'Finances removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_marketing_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        marketings = serializer.validated_data['marketings']
        marketings = get_object_or_404(Marketing, id__in=[mark.id for mark in marketings])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.marketings.remove(*marketings)
        visibility.save()
        return Response({'message': 'Marketings removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_legal_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        legals = serializer.validated_data['legals']
        legals = get_object_or_404(Legal, id__in=[leg.id for leg in legals])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.legals.remove(*legals)
        visibility.save()
        return Response({'message': 'Legals removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_ict_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        icts = serializer.validated_data['icts']
        icts = get_object_or_404(ICT, id__in=[ict.id for ict in icts])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.icts.remove(*icts)
        visibility.save()
        return Response({'message': 'ICTs removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_career_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        career_offices = serializer.validated_data['career_offices']
        career_offices = get_object_or_404(CareerOffice, id__in=[co.id for co in career_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.career_offices.remove(*career_offices)
        visibility.save()
        return Response({'message': 'Career Offices removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_counselling_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        counsellings = serializer.validated_data['counsellings']
        counsellings = get_object_or_404(Counselling, id__in=[coun.id for coun in counsellings])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.counsellings.remove(*counsellings)
        visibility.save()
        return Response({'message': 'Counsellings removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_registrar_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        registrar_offices = serializer.validated_data['registrar_offices']
        registrar_offices = get_object_or_404(RegistrarOffice, id__in=[ro.id for ro in registrar_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.registrar_offices.remove(*registrar_offices)
        visibility.save()
        return Response({'message': 'Registrar Offices removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_transport_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        transports = serializer.validated_data['transports']
        transports = get_object_or_404(Transport, id__in=[tr.id for tr in transports])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.transports.remove(*transports)
        visibility.save()
        return Response({'message': 'Transports removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_library_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        libraries = serializer.validated_data['libraries']
        libraries = get_object_or_404(Library, id__in=[lib.id for lib in libraries])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.libraries.remove(*libraries)
        visibility.save()
        return Response({'message': 'Libraries removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_hostel_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        hostels = serializer.validated_data['hostels']
        hostels = get_object_or_404(Hostel, id__in=[hostel.id for hostel in hostels])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.hostels.remove(*hostels)
        visibility.save()
        return Response({'message': 'Hostels removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_cafeteria_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        cafeterias = serializer.validated_data['cafeterias']
        cafeterias = get_object_or_404(Cafeteria, id__in=[caf.id for caf in cafeterias])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.cafeterias.remove(*cafeterias)
        visibility.save()
        return Response({'message': 'Cafeterias removed from visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_other_institution_unit_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        other_units = serializer.validated_data['other_institution_units']
        other_units = get_object_or_404(OtherInstitutionUnit, id__in=[ou.unit_code for ou in other_units])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.other_institution_units.remove(*other_units)
        visibility.save()
        return Response({'message': 'Other Institution Units removed from visibility successfully.'}, status=status.HTTP_200_OK)


    # ----- *Organisation Related Visibility Removal Actions* ----- #
    @action(detail=True, methods=['post'])
    def remove_organisation_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        organisations = serializer.validated_data['organisations']
        organisations = get_object_or_404(Organisation, id__in=[org.id for org in organisations])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.organisations.remove(*organisations)
        visibility.save()
        return Response({'message': 'Organisations removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_organisation_branch_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        org_branches = serializer.validated_data['organistion_branches']
        org_branches = get_object_or_404(OrgBranch, id__in=[orgbranch.id for orgbranch in org_branches])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.organistion_branches.remove(*org_branches)
        visibility.save()
        return Response({'message': 'Organisation Branches removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_department_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        departments = serializer.validated_data['departments']
        departments = get_object_or_404(Department, id__in=[dep.id for dep in departments])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.departments.remove(*departments)
        visibility.save()
        return Response({'message': 'Departments removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_section_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        sections = serializer.validated_data['sections']
        sections = get_object_or_404(Section, id__in=[section.id for section in sections])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.sections.remove(*sections)
        visibility.save()
        return Response({'message': 'Sections removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_committee_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        committees = serializer.validated_data['committees']
        committees = get_object_or_404(Committee, id__in=[committee.id for committee in committees])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.committees.remove(*committees)
        visibility.save()
        return Response({'message': 'Committees removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_unit_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        units = serializer.validated_data['units']
        units = get_object_or_404(Unit, id__in=[unit.id for unit in units])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.units.remove(*units)
        visibility.save()
        return Response({'message': 'Units removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_program_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        programs = serializer.validated_data['programs']
        programs = get_object_or_404(Program, id__in=[prog.id for prog in programs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.programs.remove(*programs)
        visibility.save()
        return Response({'message': 'Programs removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_project_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        projects = serializer.validated_data['projects']
        projects = get_object_or_404(Project, id__in=[proj.id for proj in projects])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.projects.remove(*projects)
        visibility.save()
        return Response({'message': 'Projects removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_centre_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        centres = serializer.validated_data['centres']
        centres = get_object_or_404(Centre, id__in=[centre.id for centre in centres])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.centres.remove(*centres)
        visibility.save()
        return Response({'message': 'Centres removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_team_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        teams = serializer.validated_data['teams']
        teams = get_object_or_404(Team, id__in=[team.id for team in teams])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.teams.remove(*teams)
        visibility.save()
        return Response({'message': 'Teams removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_division_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        divisions = serializer.validated_data['divisions']
        divisions = get_object_or_404(Division, id__in=[div.id for div in divisions])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.divisions.remove(*divisions)
        visibility.save()
        return Response({'message': 'Divisions removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_board_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        boards = serializer.validated_data['boards']
        boards = get_object_or_404(Board, id__in=[board.id for board in boards])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.boards.remove(*boards)
        visibility.save()
        return Response({'message': 'Boards removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_institute_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        institutes = serializer.validated_data['institutes']
        institutes = get_object_or_404(Institute, id__in=[inst.id for inst in institutes])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institutes.remove(*institutes)
        visibility.save()
        return Response({'message': 'Institutes removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def remove_other_organisation_unit_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        other_organisations = serializer.validated_data['other_organisations']
        other_organisations = get_object_or_404(OtherOrgUnit, id__in=[oorg.unit_code for oorg in other_organisations])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.other_organisation_units.remove(*other_organisations)
        visibility.save()
        return Response({'message': 'Other Organisations removed from visibility successfully.'}, status=status.HTTP_200_OK)
    
    
    # ------ * Adding visibilities * --------
    # ----- *User Related Visibility Addition Actions* ----- #
    @action(detail=True, methods=['post'])
    def add_room_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        rooms = serializer.validated_data['rooms']
        rooms = get_object_or_404(Room, id__in=[room.id for room in rooms])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.rooms.add(*rooms)
        visibility.save()
        return Response({'message': 'Rooms added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_default_room_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        default_rooms = serializer.validated_data['default_rooms']
        default_rooms = get_object_or_404(DefaultRoom, id__in=[droom.id for droom in default_rooms])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.default_rooms.add(*default_rooms)
        visibility.save()
        return Response({'message': 'Default Rooms added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_direct_message_room_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        dm_rooms = serializer.validated_data['direct_message_rooms']
        dm_rooms = get_object_or_404(DirectMessageRoom, id__in=[dmroom.id for dmroom in dm_rooms])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.direct_message_rooms.add(*dm_rooms)
        visibility.save()
        return Response({'message': 'Direct Message Rooms added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    # ----- *Institution Related Visibility Addition Actions* ----- #
    @action(detail=True, methods=['post']) 
    def add_insitution_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        institutions = serializer.validated_data['institutions']
        institutions = get_object_or_404(Institution, id__in=[inst.id for inst in institutions])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institutions.add(*institutions)
        visibility.save()
        return Response({'message': 'Institutions added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_institution_branch_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        inst_branches = serializer.validated_data['institution_branches']
        inst_branches = get_object_or_404(InstBranch, id__in=[instbranch.id for instbranch in inst_branches])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institution_branches.add(*inst_branches)
        visibility.save()
        return Response({'message': 'Institution Branches added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_inst_department_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        inst_departments = serializer.validated_data['institution_departments']
        inst_departments = get_object_or_404(InstDepartment, id__in=[instdep.id for instdep in inst_departments])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institution_departments.add(*inst_departments)
        visibility.save()
        return Response({'message': 'Institution Departments added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_faculty_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        faculties = serializer.validated_data['faculties']
        faculties = get_object_or_404(Faculty, id__in=[fac.id for fac in faculties])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.faculties.add(*faculties)
        visibility.save()
        return Response({'message': 'Faculties added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_admin_department_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        admin_departments = serializer.validated_data['admin_departments']
        admin_departments = get_object_or_404(AdminDepartment, id__in=[admindep.id for admindep in admin_departments])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.admin_departments.add(*admin_departments)
        visibility.save()
        return Response({'message': 'Admin Departments added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_admissions_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        admissions_offices = serializer.validated_data['admissions_offices']
        admissions_offices = get_object_or_404(AdmissionsOffice, id__in=[ao.id for ao in admissions_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.admissions_offices.add(*admissions_offices)
        visibility.save()
        return Response({'message': 'Admissions Offices added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_vc_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        vc_offices = serializer.validated_data['vc_offices']
        vc_offices = get_object_or_404(VCOffice, id__in=[vco.id for vco in vc_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.vc_offices.add(*vc_offices)
        visibility.save()
        return Response({'message': 'VC Offices added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_hr_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        hrs = serializer.validated_data['hrs']
        hrs = get_object_or_404(HR, id__in=[hr.id for hr in hrs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.hrs.add(*hrs)
        visibility.save()
        return Response({'message': 'HRs added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_inst_program_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        inst_programs = serializer.validated_data['institution_programs']
        inst_programs = get_object_or_404(InstProgram, id__in=[instprog.id for instprog in inst_programs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institution_programs.add(*inst_programs)
        visibility.save()
        return Response({'message': 'Institution Programs added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_health_service_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        health_services = serializer.validated_data['health_services']
        health_services = get_object_or_404(HealthService, id__in=[hs.id for hs in health_services])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.health_services.add(*health_services)
        visibility.save()
        return Response({'message': 'Health Services added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_security_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        securities = serializer.validated_data['securities']
        securities = get_object_or_404(Security, id__in=[sec.id for sec in securities])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.securities.add(*securities)
        visibility.save()
        return Response({'message': 'Securities added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_student_affairs_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        student_affairs = serializer.validated_data['student_affairs']
        student_affairs = get_object_or_404(StudentAffairs, id__in=[sa.id for sa in student_affairs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.student_affairs.add(*student_affairs)
        visibility.save()
        return Response({'message': 'Student Affairs added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_support_service_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        support_services = serializer.validated_data['support_services']
        support_services = get_object_or_404(SupportService, id__in=[ss.id for ss in support_services])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.support_services.add(*support_services)
        visibility.save()
        return Response({'message': 'Support Services added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_finance_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        finances = serializer.validated_data['finances']
        finances = get_object_or_404(Finance, id__in=[fin.id for fin in finances])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.finances.add(*finances)
        visibility.save()
        return Response({'message': 'Finances added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_marketing_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        marketings = serializer.validated_data['marketings']
        marketings = get_object_or_404(Marketing, id__in=[mkt.id for mkt in marketings])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.marketings.add(*marketings)
        visibility.save()
        return Response({'message': 'Marketings added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_legal_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        legals = serializer.validated_data['legals']
        legals = get_object_or_404(Legal, id__in=[leg.id for leg in legals])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.legals.add(*legals)
        visibility.save()
        return Response({'message': 'Legals added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_ict_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        icts = serializer.validated_data['icts']
        icts = get_object_or_404(ICT, id__in=[ict.id for ict in icts])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.icts.add(*icts)
        visibility.save()
        return Response({'message': 'ICTs added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_career_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        career_offices = serializer.validated_data['career_offices']
        career_offices = get_object_or_404(CareerOffice, id__in=[co.id for co in career_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.career_offices.add(*career_offices)
        visibility.save()
        return Response({'message': 'Career Offices added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_counseling_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        counselings = serializer.validated_data['counselings']
        counselings = get_object_or_404(Counseling, id__in=[csl.id for csl in counselings])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.counselings.add(*counselings)
        visibility.save()
        return Response({'message': 'Counselings added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_registrar_office_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        registrar_offices = serializer.validated_data['registrar_offices']
        registrar_offices = get_object_or_404(RegistrarOffice, id__in=[ro.id for ro in registrar_offices])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.registrar_offices.add(*registrar_offices)
        visibility.save()
        return Response({'message': 'Registrar Offices added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_transport_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        transportations = serializer.validated_data['transportations']
        transportations = get_object_or_404(Transportation, id__in=[tr.id for tr in transportations])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.transportations.add(*transportations)
        visibility.save()
        return Response({'message': 'Transportations added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_library_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        libraries = serializer.validated_data['libraries']
        libraries = get_object_or_404(Library, id__in=[lib.id for lib in libraries])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.libraries.add(*libraries)
        visibility.save()
        return Response({'message': 'Libraries added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_hostel_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        hostels = serializer.validated_data['hostels']
        hostels = get_object_or_404(Hostel, id__in=[hostel.id for hostel in hostels])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.hostels.add(*hostels)
        visibility.save()
        return Response({'message': 'Hostels added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_cafeteria_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        cafeterias = serializer.validated_data['cafeterias']
        cafeterias = get_object_or_404(Cafeteria, id__in=[caf.id for caf in cafeterias])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.cafeterias.add(*cafeterias)
        visibility.save()
        return Response({'message': 'Cafeterias added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_other_institution_unit_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        other_units = serializer.validated_data['other_institution_units']
        other_units = get_object_or_404(OtherInstitutionUnit, id__in=[oiu.unit_code for oiu in other_units])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.other_institution_units.add(*other_units)
        visibility.save()
        return Response({'message': 'Other Institution Units added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    

    # ----- *Organisation Related Visibility Addition Actions* ----- #
    @action(detail=True, methods=['post'])
    def add_organisation_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        organisations = serializer.validated_data['organisations']
        organisations = get_object_or_404(Organisation, id__in=[org.id for org in organisations])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.organisations.add(*organisations)
        visibility.save()
        return Response({'message': 'Organisations added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_organisation_branch_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        org_branches = serializer.validated_data['organisation_branches']
        org_branches = get_object_or_404(OrgBranch, id__in=[orgbranch.id for orgbranch in org_branches])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.organisation_branches.add(*org_branches)
        visibility.save()
        return Response({'message': 'Organisation Branches added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_org_department_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        org_departments = serializer.validated_data['organisation_departments']
        org_departments = get_object_or_404(Department, id__in=[orgdep.id for orgdep in org_departments])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.organisation_departments.add(*org_departments)
        visibility.save()
        return Response({'message': 'Organisation Departments added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_division_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        divisions = serializer.validated_data['divisions']
        divisions = get_object_or_404(Division, id__in=[div.id for div in divisions])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.divisions.add(*divisions)
        visibility.save()
        return Response({'message': 'Divisions added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_sector_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        sectors = serializer.validated_data['sectors']
        sectors = get_object_or_404(Section, id__in=[sec.id for sec in sectors])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.sectors.add(*sectors)
        visibility.save()
        return Response({'message': 'Sectors added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_team_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        teams = serializer.validated_data['teams']
        teams = get_object_or_404(Team, id__in=[team.id for team in teams])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.teams.add(*teams)
        visibility.save()
        return Response({'message': 'Teams added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_project_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        projects = serializer.validated_data['projects']
        projects = get_object_or_404(Project, id__in=[proj.id for proj in projects])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.projects.add(*projects)
        visibility.save()
        return Response({'message': 'Projects added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_unit_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        units = serializer.validated_data['units']
        units = get_object_or_404(Unit, id__in=[unit.id for unit in units])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.units.add(*units)
        visibility.save()
        return Response({'message': 'Units added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_centre_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        centres = serializer.validated_data['centres']
        centres = get_object_or_404(Centre, id__in=[centre.id for centre in centres])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.centres.add(*centres)
        visibility.save()
        return Response({'message': 'Centres added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_committee_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        committees = serializer.validated_data['committees']
        committees = get_object_or_404(Committee, id__in=[comm.id for comm in committees])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.committees.add(*committees)
        visibility.save()
        return Response({'message': 'Committees added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_board_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        boards = serializer.validated_data['boards']
        boards = get_object_or_404(Board, id__in=[board.id for board in boards])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.boards.add(*boards)
        visibility.save()
        return Response({'message': 'Boards added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_institute_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        institutes = serializer.validated_data['institutes']
        institutes = get_object_or_404(Institute, id__in=[inst.id for inst in institutes])
        visibility_id = request.data.get('id', None)

        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.institutes.add(*institutes)
        visibility.save()
        return Response({'message': 'Institutes added to visibility successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_org_program_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        org_programs = serializer.validated_data['organisation_programs']
        org_programs = get_object_or_404(Program, id__in=[orgprog.id for orgprog in org_programs])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.organisation_programs.add(*org_programs)
        visibility.save()
        return Response({'message': 'Organisation Programs added to visibility successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_other_organisation_unit_visibility(self, request):
        serializer = ResourceVisibilitySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invaid data input.\n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        other_units = serializer.validated_data['other_organisation_units']
        other_units = get_object_or_404(OtherOrgUnit, id__in=[oou.unit_code for oou in other_units])
        visibility_id = request.data.get('id', None)
        if not visibility_id:
            return Response({'error': 'ResourceVisibility id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        visibility = get_object_or_404(ResourceVisibility, id=visibility_id)
        visibility.other_organisation_units.add(*other_units)
        visibility.save()
        return Response({'message': 'Other Organisation Units added to visibility successfully.'}, status=status.HTTP_200_OK)



    
class VisibilityLogViewSet(ModelViewSet):
    queryset = VisibilityLog.objects.all()
    serializer_class = VisibilityLogSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

